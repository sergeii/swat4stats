import logging
from collections.abc import Callable
from typing import Any, ClassVar
from urllib.parse import quote as urlquote

import voluptuous
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import transaction
from django.utils.text import slugify
from django.utils.translation import gettext_lazy as _
from rest_framework import serializers
from rest_framework.exceptions import ValidationError

from apps.tracker.entities import GameType
from apps.tracker.models import (
    Loadout,
    PlayerStats,
    Profile,
    Server,
)
from apps.tracker.schema import coop_status_encoded, serverquery_schema
from apps.tracker.utils.game import (
    gametype_rules_text,
    map_background_picture,
    map_briefing_text,
)
from apps.tracker.utils.geo import country
from apps.tracker.utils.misc import force_clean_name, format_name

logger = logging.getLogger(__name__)

port_validators = [MinValueValidator(1), MaxValueValidator(65535)]


class ServerFilterSerializer(serializers.Serializer):
    gamename = serializers.CharField(allow_null=True, default=None)
    gamever = serializers.CharField(allow_null=True, default=None)
    gametype = serializers.CharField(allow_null=True, default=None)
    mapname = serializers.CharField(allow_null=True, default=None)
    passworded = serializers.BooleanField(default=None, allow_null=True)
    full = serializers.BooleanField(default=None, allow_null=True)
    empty = serializers.BooleanField(default=None, allow_null=True)


class StatusPlayerSerializer(serializers.Serializer):
    default_coop_status = coop_status_encoded[1]

    id = serializers.IntegerField()
    name = serializers.CharField()
    ping = serializers.IntegerField()
    score = serializers.IntegerField()
    team = serializers.CharField()
    vip = serializers.BooleanField()
    coop_status = serializers.SerializerMethodField()
    coop_status_slug = serializers.SerializerMethodField()
    kills = serializers.IntegerField()
    teamkills = serializers.IntegerField(source="tkills")
    deaths = serializers.IntegerField()
    arrests = serializers.IntegerField()
    arrested = serializers.IntegerField()
    vip_escapes = serializers.SerializerMethodField()
    vip_captures = serializers.IntegerField(source="arrestedvip")
    vip_rescues = serializers.IntegerField(source="unarrestedvip")
    vip_kills_valid = serializers.IntegerField(source="validvipkills")
    vip_kills_invalid = serializers.IntegerField(source="invalidvipkills")
    rd_bombs_defused = serializers.IntegerField(source="bombsdiffused")
    rd_crybaby = serializers.IntegerField(source="rdcrybaby")
    sg_crybaby = serializers.IntegerField(source="sgcrybaby")
    sg_escapes = serializers.IntegerField(source="escapedcase")
    sg_kills = serializers.IntegerField(source="killedcase")
    special = serializers.SerializerMethodField()
    url = serializers.SerializerMethodField()

    def get_coop_status(self, obj: dict[str, Any]) -> str:
        return _(obj.get("coop_status") or self.default_coop_status)

    def get_coop_status_slug(self, obj: dict[str, Any]) -> str:
        return slugify(obj.get("coop_status") or self.default_coop_status)

    def get_vip_escapes(self, obj: dict[str, Any]) -> int:
        return obj["vescaped"] if obj["vescaped"] > 0 else obj["vipescaped"]

    def get_special(self, obj: dict[str, Any]) -> int:
        return (
            obj["vescaped"]
            + obj["vipescaped"]
            + obj["arrestedvip"]
            + obj["unarrestedvip"]
            + obj["bombsdiffused"]
            + obj["escapedcase"]
        )

    def get_url(self, obj: dict[str, Any]) -> str:
        html_name = urlquote(obj["name"])
        return f"/search/?player={html_name}"


class StatusBaseSerializer(serializers.Serializer):
    hostname = serializers.CharField()
    hostname_html = serializers.SerializerMethodField()
    hostname_clean = serializers.SerializerMethodField()
    port = serializers.IntegerField(source="hostport")
    passworded = serializers.BooleanField(source="password")
    gamename = serializers.SerializerMethodField()
    gamever = serializers.CharField()
    gametype = serializers.SerializerMethodField()
    gametype_slug = serializers.SerializerMethodField()
    mapname = serializers.SerializerMethodField()
    player_num = serializers.IntegerField(source="numplayers")
    player_max = serializers.IntegerField(source="maxplayers")
    round_num = serializers.IntegerField(source="round")
    round_max = serializers.IntegerField(source="numrounds")
    mapname_slug = serializers.SerializerMethodField()
    mapname_background = serializers.SerializerMethodField()

    def get_gamename(self, obj: dict) -> str:
        return _(obj["gamevariant"])

    def get_hostname_html(self, obj: dict) -> str:
        return format_name(obj["hostname"])

    def get_hostname_clean(self, obj: dict) -> str:
        return force_clean_name(obj["hostname"])

    def get_mapname(self, obj: dict) -> str:
        return _(obj["mapname"])

    def get_gametype(self, obj: dict) -> str:
        return _(obj["gametype"])

    def get_gametype_slug(self, obj: dict) -> str:
        return slugify(obj["gametype"])

    def get_mapname_slug(self, obj: dict) -> str:
        return slugify(obj["mapname"])

    def get_mapname_background(self, obj: dict) -> str:
        return map_background_picture(obj["mapname"])


class StatusObjectiveSerializer(serializers.Serializer):
    name = serializers.SerializerMethodField()
    status = serializers.SerializerMethodField()
    status_slug = serializers.SerializerMethodField()

    def get_name(self, obj: dict) -> str:
        return _(obj["name"])

    def get_status(self, obj: dict) -> str:
        return _(obj["status"])

    def get_status_slug(self, obj: dict) -> str:
        return slugify(obj["status"])


class StatusFullSerializer(StatusBaseSerializer):
    time_round = serializers.IntegerField(source="timeleft")
    time_special = serializers.IntegerField(source="timespecial")
    score_swat = serializers.IntegerField(source="swatscore")
    score_sus = serializers.IntegerField(source="suspectsscore")
    vict_swat = serializers.IntegerField(source="swatwon")
    vict_sus = serializers.IntegerField(source="suspectswon")
    bombs_defused = serializers.IntegerField(source="bombsdefused")
    bombs_total = serializers.IntegerField(source="bombstotal")
    coop_reports = serializers.CharField(source="tocreports")
    coop_weapons = serializers.CharField(source="weaponssecured")
    players = StatusPlayerSerializer(many=True)
    objectives = StatusObjectiveSerializer(many=True)
    rules = serializers.SerializerMethodField()
    briefing = serializers.SerializerMethodField()

    def get_rules(self, obj: dict) -> str | None:
        return gametype_rules_text(obj["gametype"])

    def get_briefing(self, obj: dict) -> str | None:
        if obj["gametype"] in (GameType.co_op, GameType.co_op_qmm):
            return map_briefing_text(obj["mapname"])
        return None


class ServerBaseSerializer(serializers.ModelSerializer):
    port = serializers.IntegerField(default=10480, validators=port_validators)
    status = StatusBaseSerializer(read_only=True)
    country_human = serializers.SerializerMethodField()
    name_clean = serializers.SerializerMethodField()
    address = serializers.CharField(read_only=True)

    class Meta:
        model = Server
        read_only_fields: tuple[str, ...] = (
            "id",
            "address",
            "pinned",
            "country",
            "country_human",
            "hostname",
            "name_clean",
            "status",
            "first_game_played_at",
            "latest_game_played_at",
            "game_count",
        )
        fields: tuple[str, ...] = (
            *read_only_fields,
            "ip",
            "port",
        )
        validators: ClassVar[list[Callable]] = []

    def get_country_human(self, obj: Server) -> str | None:
        if obj.country:
            return country(obj.country)
        return None

    def get_name_clean(self, obj: Server) -> str:
        if not obj.hostname_clean:
            return obj.address
        return obj.hostname_clean


class ServerFullSerializer(ServerBaseSerializer):
    status = StatusFullSerializer(read_only=True)
    merged_into = ServerBaseSerializer(read_only=True)

    class Meta(ServerBaseSerializer.Meta):
        read_only_fields = (
            *ServerBaseSerializer.Meta.read_only_fields,
            "merged_into",
        )
        fields = (
            *ServerBaseSerializer.Meta.fields,
            "merged_into",
        )


class ServerCreateSerializer(ServerFullSerializer):
    def _validate_instance(self, ip: str, port: int) -> Server | None:
        try:
            instance = Server.objects.get(ip=ip, port=port)
        except Server.DoesNotExist:
            return None

        if instance.listed:
            raise ValidationError(_("The specified server already exists"))

        return instance

    def validate(self, attrs: dict[str, Any]) -> dict[str, Any]:
        ip = attrs["ip"]
        port = attrs["port"]

        wrong_port_error = ValidationError(
            _("Ensure the server is running at port %(port)s") % {"port": port}
        )

        instance = self._validate_instance(ip, port)
        probe_or_exc = Server.objects.probe_server_addr((ip, port))

        if isinstance(probe_or_exc, Exception):
            raise wrong_port_error

        try:
            validated_status = serverquery_schema(probe_or_exc)
        except voluptuous.Invalid as exc:
            logger.warning(
                "unable to create server %s:%s due to schema error: %s",
                ip,
                port,
                exc,
                exc_info=True,
            )
            raise wrong_port_error

        if validated_status["hostport"] != port:
            logger.warning(
                "unable to create server %s:%s due to reported port mismatch: %s",
                ip,
                port,
                validated_status["hostport"],
            )
            raise wrong_port_error

        attrs.update(
            {
                "instance": instance,
                "listed": True,
                "failures": 0,
                "status": validated_status,
                "hostname": validated_status["hostname"],
                "hostname_clean": force_clean_name(validated_status["hostname"]),
            }
        )

        return attrs

    @transaction.atomic
    def create(self, validated_data: dict[str, Any]) -> Server:
        instance = validated_data.pop("instance")
        status = validated_data.pop("status")

        if instance is None:
            instance = super().create(validated_data)
        else:
            instance = self.update(instance, validated_data)

        Server.objects.update_server_with_status(instance, status)
        instance.status = status

        return instance


class LoadoutSerializer(serializers.ModelSerializer):
    class Meta:
        model = Loadout
        fields = (
            "primary",
            "secondary",
            "equip_one",
            "equip_two",
            "equip_three",
            "equip_four",
            "equip_five",
            "breacher",
            "head",
            "body",
        )


class ProfileSerializer(serializers.ModelSerializer):
    loadout = LoadoutSerializer()
    country_human = serializers.SerializerMethodField()

    class Meta:
        model = Profile
        fields = (
            "id",
            "name",
            "team",
            "loadout",
            "country",
            "country_human",
            "first_seen_at",
            "last_seen_at",
        )
        read_only_fields = fields

    def get_country_human(self, obj: Profile) -> str:
        return country(obj.country)


class PlayerStatSerializer(serializers.ModelSerializer):
    profile = ProfileSerializer()

    class Meta:
        model = PlayerStats
        fields = ("id", "category", "year", "profile", "points", "position")
        read_only_fields = fields


class ProfileSearchItemSerializer(serializers.Serializer):
    item = ProfileSerializer(source="*")
    headline = serializers.CharField()
    excerpt = serializers.CharField()

    class Meta:
        fields = ("item", "headline", "excerpt")
        read_only_fields = fields


class ServerSearchItemSerializer(serializers.Serializer):
    item = ServerBaseSerializer(source="*")
    headline = serializers.CharField()
    excerpt = serializers.SerializerMethodField()

    class Meta:
        fields = ("item", "headline", "excerpt")
        read_only_fields = fields

    def get_excerpt(self, _: Server) -> None:
        return None
