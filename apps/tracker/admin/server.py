import logging
from typing import Any, ClassVar

from django import forms
from django.conf import settings
from django.contrib import admin, messages
from django.core.exceptions import ValidationError
from django.core.validators import validate_ipv4_address
from django.db.models import QuerySet, Case, When, Value, BooleanField
from django.http import HttpRequest, QueryDict, HttpResponseRedirect, HttpResponse
from django.shortcuts import render
from django.urls import path, reverse, URLPattern
from django.utils.translation import gettext_lazy as _

from apps.tracker.models import Server
from apps.tracker.tasks import merge_servers
from apps.utils.admin import admin_change_url, admin_change_urls
from apps.utils.misc import concat_it

logger = logging.getLogger(__name__)


class IsMergedListFilter(admin.SimpleListFilter):
    title = _("Merged")
    parameter_name = "is_merged"

    def lookups(self, request: HttpRequest, model_admin: admin.ModelAdmin) -> list[tuple[str, str]]:
        return [
            ("1", _("Yes")),
            ("0", _("No")),
        ]

    def queryset(self, request: HttpRequest, queryset: QuerySet) -> QuerySet:
        match self.value():
            case "1":
                return queryset.filter(merged_into__isnull=False)
            case "0":
                return queryset.filter(merged_into__isnull=True)
            case _:
                return queryset


class ServerMergeForm(forms.Form):
    merged_servers = forms.MultipleChoiceField(label=_("Merged servers"), required=True)
    main_server = forms.ChoiceField(label=_("Main server"), required=True)

    confirm = forms.BooleanField(label=_("Confirm"), required=True)

    def __init__(self, data: QueryDict | None, queryset: QuerySet) -> None:
        super().__init__(data=data)
        choices = [(s.pk, f"{s.name} ({s.address})") for s in queryset]
        self.fields["main_server"].choices = choices
        self.fields["merged_servers"].choices = choices

    def clean(self) -> dict[str, Any]:
        main_server_id = self.cleaned_data.get("main_server")
        merged_server_ids = self.cleaned_data.get("merged_servers")

        if not (main_server_id and merged_server_ids):
            raise ValidationError(_("Please select servers to merge"))

        if not (merged_server_ids_uniq := set(merged_server_ids) - {main_server_id}):
            raise ValidationError(_("Please select at least one server to merge"))

        try:
            main_server = Server.objects.select_related("merged_into").get(pk=main_server_id)
        except Server.DoesNotExist:
            raise ValidationError(_("Please specify correct target server"))

        if main_server.merged_into is not None:
            raise ValidationError(
                _("Target server is already merged into %(server)s")
                % {
                    "server": f"{main_server.merged_into.name} ({main_server.merged_into.address})",
                }
            )

        # fmt: off
        merged_servers = (
            Server.objects
            .filter(merged_into__isnull=True, pk__in=merged_server_ids_uniq)
            .order_by("pk")
        )
        # fmt: on
        if len(merged_servers) != len(merged_server_ids_uniq):
            raise ValidationError(_("Some of the selected servers are not available"))

        self.cleaned_data.update(
            {"main_server": main_server.pk, "merged_servers": [s.pk for s in merged_servers]}
        )
        return self.cleaned_data


@admin.register(Server)
class ServerAdmin(admin.ModelAdmin):
    list_display = ("__str__", "ip", "port", "enabled", "listed", "admin_is_merged", "version")
    list_filter = ("enabled", "listed", "pinned", IsMergedListFilter, "version")
    search_fields = ("=ip", "hostname")
    fieldsets = (
        (
            None,
            {
                "fields": (
                    "ip",
                    "port",
                    "status_port",
                    "hostname",
                    "country",
                    "enabled",
                    "listed",
                    "pinned",
                ),
            },
        ),
        (
            _("Meta"),
            {
                "fields": (
                    "version",
                    "failures",
                    "admin_merged_into",
                    "admin_merged_with",
                    "merged_into_at",
                    "merged_stats_at",
                ),
            },
        ),
    )
    readonly_fields = (
        "version",
        "failures",
        "admin_merged_into",
        "admin_merged_with",
        "merged_into_at",
        "merged_stats_at",
    )
    list_per_page = 50
    actions: ClassVar[list[str]] = ["merge_servers"]
    ordering: ClassVar[list[str]] = ["pk"]

    @admin.display(description=_("Merged"), boolean=True, ordering="is_merged")
    def admin_is_merged(self, obj: Server) -> bool:
        return obj.is_merged

    @admin.display(description=_("Merged into"))
    def admin_merged_into(self, obj: Server) -> str:
        if obj.merged_into is None:
            return "-"
        return admin_change_url(obj.merged_into)

    @admin.display(description=_("Merged with"))
    def admin_merged_with(self, obj: Server) -> str:
        merged_qs = Server.objects.filter(merged_into=obj)
        if merged_qs:
            return admin_change_urls(merged_qs)
        return "-"

    def has_delete_permission(self, *args: Any, **kwargs: Any) -> bool:
        return settings.DEBUG

    def get_queryset(self, request: HttpRequest) -> QuerySet:
        return (
            super()
            .get_queryset(request)
            .select_related("merged_into")
            .annotate(
                is_merged=Case(
                    When(merged_into__isnull=False, then=Value(True)),  # noqa: FBT003
                    default=Value(False),  # noqa: FBT003
                    output_field=BooleanField(),
                )
            )
        )

    def get_search_results(
        self,
        request: HttpRequest,
        queryset: QuerySet,
        search_term: str,
    ) -> tuple[QuerySet, bool]:
        if addr := self._get_addr_port_from_term(search_term):
            search_qs = queryset.filter(ip=addr[0], port=addr[1]).order_by()
            return search_qs, False
        return super().get_search_results(request, queryset, search_term)

    def _get_addr_port_from_term(self, term: str) -> tuple[str, int] | None:
        if ":" not in term:
            return None

        maybe_ip, maybe_port = term.split(":", maxsplit=1)

        try:
            validate_ipv4_address(maybe_ip)
        except ValidationError:
            return None

        try:
            maybe_valid_port = int(maybe_port)
        except (TypeError, ValueError):
            return None

        if not (0 < maybe_valid_port <= 65535):
            return None

        return maybe_ip, maybe_valid_port

    @admin.action(description=_("Merge selected servers"))
    def merge_servers(
        self, request: HttpRequest, queryset: QuerySet
    ) -> HttpResponseRedirect | None:
        ids = list(queryset.values_list("pk", flat=True))

        if len(ids) < 2:
            self.message_user(request, _("Select at least two servers"), level=messages.ERROR)
            return None

        url = reverse("admin:tracker_server_merge_form")
        ids_by_comma = ",".join(map(str, ids))

        return HttpResponseRedirect(f"{url}?ids={ids_by_comma}")

    def merge_servers_form(self, request: HttpRequest) -> HttpResponse:
        return_url = reverse("admin:tracker_server_changelist")

        if not (server_ids_comma := request.GET.get("ids")):
            return HttpResponseRedirect(return_url)

        try:
            server_ids = [int(server_id) for server_id in server_ids_comma.split(",")]
        except ValueError as exc:
            logger.exception("unable to patse server ids %s due to %s", server_ids_comma, exc)
            return HttpResponseRedirect(return_url)

        # fmt: off
        queryset = (
            Server.objects
            .filter(pk__in=server_ids, merged_into__isnull=True)
            .order_by("-pk")
        )
        # fmt: on
        form = ServerMergeForm(data=request.POST or None, queryset=queryset)

        if request.method == "POST" and form.is_valid():
            logger.info(
                "firing merge servers task with main_server_id=%s merged_server_ids=%s",
                form.cleaned_data["main_server"],
                concat_it(form.cleaned_data["merged_servers"]),
            )
            merge_servers.delay(
                main_server_id=form.cleaned_data["main_server"],
                merged_server_ids=form.cleaned_data["merged_servers"],
            )
            self.message_user(request, _("Server merge task has been scheduled"))
            return HttpResponseRedirect(return_url)

        return render(
            request,
            "admin/tracker/server/merge_servers.html",
            {"form": form, "title": _("Merge servers")},
        )

    def get_urls(self) -> list[URLPattern]:
        urls = super().get_urls()
        extra_urls = [
            path(
                "merge/",
                self.admin_site.admin_view(self.merge_servers_form),
                name=f"{self.model._meta.app_label}_{self.model._meta.model_name}_merge_form",
            ),
        ]
        return extra_urls + urls
