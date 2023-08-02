from random import choice
from typing import Any, ClassVar

from django import forms
from django.utils.translation import gettext_lazy as _
from django.http import HttpRequest, HttpResponse, HttpResponseBadRequest
from django.views.generic import TemplateView

from apps.tracker.models import PlayerStats, GametypeStats
from apps.tracker.utils.misc import get_current_stat_year


class MotdBaseForm(forms.Form):
    initial = forms.IntegerField(min_value=0, required=False)
    repeat = forms.IntegerField(min_value=0, required=False)
    nodelay = forms.BooleanField(required=False)


class MotdLeaderboardForm(MotdBaseForm):
    class Defaults:
        initial = 60  # start displaying in 60 seconds after a map launch
        repeat = 0  # display once
        limit = 5

    gametypes: ClassVar[dict[str, str]] = {
        "coop": "CO-OP",
        "vip": "VIP Escort",
        "rd": "Rapid Deployment",
        "sg": "Smash And Grab",
    }

    class Cats:
        coop: ClassVar[dict[str, str]] = {
            "coop_score": _("CO-OP Score"),
            "coop_time": _("Time Played"),
            "coop_games": _("Missions Played"),
            "coop_wins": _("Missions Completed"),
            "coop_enemy_arrests": _("Suspects Arrested"),
            "coop_enemy_kills": _("Suspects Neutralized"),
            "coop_toc_reports": _("TOC Reports"),
        }
        common: ClassVar[dict[str, str]] = {
            "score": _("Score"),
            "top_score": _("Best Score"),
            "time": _("Time Played"),
            "wins": _("Wins"),
            "kills": _("Kills"),
            "arrests": _("Arrests"),
            "top_kill_streak": _("Best Kill Streak"),
            "top_arrest_streak": _("Best Arrest Streak"),
            "spm_ratio": _("Score/Minute"),
            "spr_ratio": _("Score/Round"),
            "kd_ratio": _("K/D Ratio"),
            "weapon_hit_ratio": _("Accuracy"),
        }
        vip: ClassVar[dict[str, str]] = {
            "vip_escapes": _("VIP Escapes"),
            "vip_captures": _("VIP Captures"),
            "vip_rescues": _("VIP Rescues"),
            "vip_kills_valid": _("VIP Kills"),
        }
        rd: ClassVar[dict[str, str]] = {
            "rd_bombs_defused": _("Bombs Disarmed"),
        }
        sg: ClassVar[dict[str, str]] = {
            "sg_escapes": _("Case Escapes"),
            "sg_kills": _("Case Carrier Kills"),
        }
        combined = coop | common | vip | sg | rd

    # custom mapping schema, other categories map as is
    alias_to_category: ClassVar[dict[str, str]] = {
        "spm": "spm_ratio",
        "kdr": "kd_ratio",
        "kill_streak": "top_kill_streak",
        "arrest_streak": "top_arrest_streak",
        "accuracy": "weapon_hit_ratio",
        "ammo_accuracy": "weapon_hit_ratio",
    }

    limit = forms.IntegerField(min_value=1, max_value=20, required=False)
    category = forms.ChoiceField(
        choices=(Cats.combined | alias_to_category).items(), required=False
    )
    gametype = forms.ChoiceField(choices=gametypes.items(), required=False)

    def clean(self) -> dict[str, Any]:
        cleaned_data = super().clean()

        if self.errors:
            return cleaned_data

        category = cleaned_data.get("category") or choice(list(self.Cats.common))
        # the requested category could be an alias to another category name
        if category in self.alias_to_category:
            category = self.alias_to_category[category]

        if gametype_slug := cleaned_data.get("gametype"):
            gametype = self.gametypes[gametype_slug]
        else:
            gametype = self._guess_gametype_by_category(category)

        cleaned_data.update(
            {
                "category": category,
                "gametype": gametype,
                "title": self.Cats.combined[category],
                "limit": cleaned_data["limit"] or self.Defaults.limit,
                "nodelay": bool(cleaned_data["nodelay"]),
                "initial": self.Defaults.initial
                if cleaned_data["initial"] is None
                else cleaned_data["initial"],
                "repeat": self.Defaults.repeat
                if cleaned_data["repeat"] is None
                else cleaned_data["repeat"],
            }
        )

        return cleaned_data

    def _guess_gametype_by_category(self, category: str) -> str | None:
        """Try to detect gametype for some gametype-related categories"""
        prefix = category.split("_", maxsplit=1)[0]
        match prefix:
            case "vip" | "rd" | "sg" | "coop":
                return self.gametypes[prefix]
        return None


class APIMotdLeaderboardView(TemplateView):
    template_name = "tracker/api/motd/leaderboard.html"

    def get(self, request: HttpRequest, *args: Any, **kwargs: Any) -> HttpResponse:
        req = dict(self.request.GET.dict(), **kwargs)
        form = MotdLeaderboardForm(data=req)

        if not form.is_valid():
            return HttpResponseBadRequest()

        context_data = self.get_context_data(form=form)
        return self.render_to_response(context_data)

    def get_context_data(self, *, form: MotdLeaderboardForm, **kwargs: Any) -> dict[str, Any]:
        context_data = super().get_context_data(**kwargs)

        context_data.update(form.cleaned_data)
        context_data["players"] = self._get_players_for_leaderboard(
            form.cleaned_data["category"], form.cleaned_data["gametype"], form.cleaned_data["limit"]
        )

        return context_data

    def _get_players_for_leaderboard(
        self, category: str, gametype: str | None, limit: int
    ) -> list[PlayerStats | GametypeStats]:
        effective_year = get_current_stat_year()

        if gametype:
            qs = GametypeStats.objects.filter(
                category=category, gametype=gametype, year=effective_year
            )
        else:
            qs = PlayerStats.objects.filter(category=category, year=effective_year)

        qs = (
            qs.filter(position__isnull=False, position__lte=limit)
            .select_related("profile")
            .order_by("position")[:limit]
        )

        return list(qs)


class APILegacySummaryView(TemplateView):
    template_name = "tracker/api/motd/summary.html"
