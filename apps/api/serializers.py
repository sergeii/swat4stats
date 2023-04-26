import logging
from typing import Any
from collections.abc import Callable
from urllib.parse import quote as urlquote

import voluptuous
from django.db import transaction
from django.utils.safestring import SafeString
from django.utils.text import slugify
from django.utils.translation import gettext_lazy as _
from django.core.validators import MinValueValidator, MaxValueValidator
from rest_framework import serializers
from rest_framework.exceptions import ValidationError

from apps.news.models import Article
from apps.tracker.entities import GameType, CoopStatus
from apps.tracker.models import Server, Map, Game, Player, Objective, Procedure, Weapon, PlayerStats, Profile, Loadout
from apps.tracker.schema import coop_status_encoded, serverquery_schema
from apps.tracker.utils import force_clean_name, format_name, html
from apps.tracker.utils.game import (
    get_player_portrait_image,
    gametype_rules_text,
    map_briefing_text,
    map_background_picture,
)
from apps.tracker.utils.geo import country

logger = logging.getLogger(__name__)

port_validators = [MinValueValidator(1), MaxValueValidator(65535)]


class NewsArticleSerializer(serializers.ModelSerializer):
    html = serializers.SerializerMethodField()

    class Meta:
        fields = ('id', 'title', 'html', 'signature', 'date_published')
        model = Article

    def get_html(self, obj: Article) -> str:
        if isinstance(obj.rendered, SafeString):
            return obj.rendered
        return html.escape(obj.rendered)


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
    teamkills = serializers.IntegerField(source='tkills')
    deaths = serializers.IntegerField()
    arrests = serializers.IntegerField()
    arrested = serializers.IntegerField()
    vip_escapes = serializers.IntegerField(source='vescaped')
    vip_captures = serializers.IntegerField(source='arrestedvip')
    vip_rescues = serializers.IntegerField(source='unarrestedvip')
    vip_kills_valid = serializers.IntegerField(source='validvipkills')
    vip_kills_invalid = serializers.IntegerField(source='invalidvipkills')
    rd_bombs_defused = serializers.IntegerField(source='bombsdiffused')
    rd_crybaby = serializers.IntegerField(source='rdcrybaby')
    sg_crybaby = serializers.IntegerField(source='sgcrybaby')
    sg_escapes = serializers.IntegerField(source='escapedcase')
    sg_kills = serializers.IntegerField(source='killedcase')
    special = serializers.SerializerMethodField()
    url = serializers.SerializerMethodField()

    def get_coop_status(self, obj: dict[str, Any]) -> str:
        return _(obj.get('coop_status') or self.default_coop_status)

    def get_coop_status_slug(self, obj: dict[str, Any]) -> str:
        return slugify(obj.get('coop_status') or self.default_coop_status)

    def get_special(self, obj: dict[str, Any]) -> int:
        return (obj['vescaped'] +
                obj['arrestedvip'] +
                obj['unarrestedvip'] +
                obj['bombsdiffused'] +
                obj['escapedcase'])

    def get_url(self, obj: dict[str, Any]) -> str:
        html_name = urlquote(obj['name'])
        return f"/search/?player={html_name}"


class StatusBaseSerializer(serializers.Serializer):
    hostname = serializers.CharField()
    hostname_html = serializers.SerializerMethodField()
    hostname_clean = serializers.SerializerMethodField()
    port = serializers.IntegerField(source='hostport')
    passworded = serializers.BooleanField(source='password')
    gamename = serializers.SerializerMethodField()
    gamever = serializers.CharField()
    gametype = serializers.SerializerMethodField()
    gametype_slug = serializers.SerializerMethodField()
    mapname = serializers.SerializerMethodField()
    player_num = serializers.IntegerField(source='numplayers')
    player_max = serializers.IntegerField(source='maxplayers')
    round_num = serializers.IntegerField(source='round')
    round_max = serializers.IntegerField(source='numrounds')
    mapname_slug = serializers.SerializerMethodField()
    mapname_background = serializers.SerializerMethodField()

    def get_gamename(self, obj: dict) -> str:
        return _(obj['gamevariant'])

    def get_hostname_html(self, obj: dict) -> str:
        return format_name(obj['hostname'])

    def get_hostname_clean(self, obj: dict) -> str:
        return force_clean_name(obj['hostname'])

    def get_mapname(self, obj: dict) -> str:
        return _(obj['mapname'])

    def get_gametype(self, obj: dict) -> str:
        return _(obj['gametype'])

    def get_gametype_slug(self, obj: dict) -> str:
        return slugify(obj['gametype'])

    def get_mapname_slug(self, obj: dict) -> str:
        return slugify(obj['mapname'])

    def get_mapname_background(self, obj: dict) -> str:
        return map_background_picture(obj['mapname'])


class StatusObjectiveSerializer(serializers.Serializer):
    name = serializers.SerializerMethodField()
    status = serializers.SerializerMethodField()
    status_slug = serializers.SerializerMethodField()

    def get_name(self, obj: dict) -> str:
        return _(obj['name'])

    def get_status(self, obj: dict) -> str:
        return _(obj['status'])

    def get_status_slug(self, obj: dict) -> str:
        return slugify(obj['status'])


class StatusFullSerializer(StatusBaseSerializer):
    time_round = serializers.IntegerField(source='timeleft')
    time_special = serializers.IntegerField(source='timespecial')
    score_swat = serializers.IntegerField(source='swatscore')
    score_sus = serializers.IntegerField(source='suspectsscore')
    vict_swat = serializers.IntegerField(source='swatwon')
    vict_sus = serializers.IntegerField(source='suspectswon')
    bombs_defused = serializers.IntegerField(source='bombsdefused')
    bombs_total = serializers.IntegerField(source='bombstotal')
    coop_reports = serializers.CharField(source='tocreports')
    coop_weapons = serializers.CharField(source='weaponssecured')
    players = StatusPlayerSerializer(many=True)
    objectives = StatusObjectiveSerializer(many=True)
    rules = serializers.SerializerMethodField()
    briefing = serializers.SerializerMethodField()

    def get_rules(self, obj: dict) -> str | None:
        return gametype_rules_text(obj['gametype'])

    def get_briefing(self, obj: dict) -> str | None:
        if obj['gametype'] in (GameType.co_op, GameType.co_op_qmm):
            return map_briefing_text(obj['mapname'])
        return None


class ServerBaseSerializer(serializers.ModelSerializer):
    port = serializers.IntegerField(default=10480, validators=port_validators)
    status = StatusBaseSerializer(read_only=True)
    country_human = serializers.SerializerMethodField()
    name_clean = serializers.SerializerMethodField()
    address = serializers.CharField(read_only=True)

    class Meta:
        model = Server
        read_only_fields = (
            'id', 'address', 'pinned',
            'country', 'country_human', 'hostname', 'name_clean', 'status',
        )
        fields = read_only_fields + ('ip', 'port',)
        validators: list[Callable] = []

    def get_country_human(self, obj: Server) -> str | None:
        if obj.country:
            return country(obj.country)
        return None

    def get_name_clean(self, obj: Server) -> str:
        return force_clean_name(obj.name)


class ServerFullSerializer(ServerBaseSerializer):
    status = StatusFullSerializer(read_only=True)
    merged_into = ServerBaseSerializer(read_only=True)

    class Meta(ServerBaseSerializer.Meta):
        read_only_fields = ServerBaseSerializer.Meta.read_only_fields + ('merged_into',)
        fields = ServerBaseSerializer.Meta.fields + ('merged_into',)


class ServerCreateSerializer(ServerFullSerializer):

    def _validate_instance(self, ip: str, port: int) -> Server | None:
        try:
            instance = Server.objects.get(ip=ip, port=port)
        except Server.DoesNotExist:
            return None

        if instance.listed:
            raise ValidationError(_('The specified server already exists'))

        return instance

    def validate(self, attrs: dict[str, Any]) -> dict[str, Any]:
        ip = attrs['ip']
        port = attrs['port']

        wrong_port_error = ValidationError(_('Ensure the server is running at port %(port)s') % {'port': port})

        instance = self._validate_instance(ip, port)
        probe_or_exc = Server.objects.probe_server_addr((ip, port))

        if isinstance(probe_or_exc, Exception):
            raise wrong_port_error

        try:
            validated_status = serverquery_schema(probe_or_exc)
        except voluptuous.Invalid as exc:
            logger.warning('unable to create server %s:%s due to schema error: %s',
                           ip, port, exc, exc_info=True)
            raise wrong_port_error

        if validated_status['hostport'] != port:
            logger.warning('unable to create server %s:%s due to reported port mismatch: %s',
                           ip, port, validated_status['hostport'])
            raise wrong_port_error

        attrs.update({
            'instance': instance,
            'listed': True,
            'failures': 0,
            'status': validated_status,
            'hostname': validated_status['hostname'],
        })

        return attrs

    @transaction.atomic
    def create(self, validated_data: dict[str, Any]) -> Server:
        instance = validated_data.pop('instance')
        status = validated_data.pop('status')

        if instance is None:
            instance = super().create(validated_data)
        else:
            instance = self.update(instance, validated_data)

        instance.update_with_status(status)
        instance.status = status

        return instance


class MapSerializer(serializers.ModelSerializer):
    class Meta:
        model = Map
        fields = ('id', 'name', 'slug', 'preview_picture', 'background_picture')
        read_only_fields = fields


class ProfileBaseSerializer(serializers.ModelSerializer):
    country_human = serializers.SerializerMethodField()
    portrait_picture = serializers.SerializerMethodField()

    class Meta:
        model = Profile
        fields = ('id', 'name', 'team', 'country', 'country_human', 'portrait_picture')
        read_only_fields = fields

    def get_portrait_picture(self, obj: Profile) -> str:
        return get_player_portrait_image(
            team=obj.team,
            head=obj.loadout.head if obj.loadout else None,
            body=obj.loadout.body if obj.loadout else None,
        )

    def get_country_human(self, obj: Profile) -> str | None:
        if obj.country:
            return country(obj.country)
        return None


class PlayerSerializer(serializers.ModelSerializer):
    profile = ProfileBaseSerializer()
    portrait_picture = serializers.SerializerMethodField()
    country = serializers.SerializerMethodField()
    country_human = serializers.SerializerMethodField()
    coop_status = serializers.SerializerMethodField()
    coop_status_slug = serializers.SerializerMethodField()

    class Meta:
        model = Player
        fields = ('id', 'name', 'portrait_picture', 'country', 'profile',
                  'country_human', 'team', 'coop_status', 'coop_status_slug', 'vip', 'dropped',
                  'score', 'time', 'kills', 'teamkills', 'deaths', 'suicides', 'arrests',
                  'arrested', 'kill_streak', 'arrest_streak', 'death_streak',
                  'vip_captures', 'vip_rescues', 'vip_escapes', 'vip_kills_valid', 'vip_kills_invalid',
                  'rd_bombs_defused', 'sg_escapes', 'sg_kills',
                  'coop_hostage_arrests', 'coop_hostage_hits', 'coop_hostage_incaps', 'coop_hostage_kills',
                  'coop_enemy_arrests', 'coop_enemy_incaps', 'coop_enemy_kills', 'coop_enemy_incaps_invalid',
                  'coop_enemy_kills_invalid', 'coop_toc_reports',
                  'special')

    def get_portrait_picture(self, obj: Player) -> str:
        return get_player_portrait_image(
            team=obj.team,
            is_vip=obj.vip,
            head=obj.loadout.head if obj.loadout else None,
            body=obj.loadout.body if obj.loadout else None,
        )

    def get_country(self, obj: Player) -> str | None:
        if obj.alias.isp and obj.alias.isp.country:
            return obj.alias.isp.country
        return None

    def get_country_human(self, obj: Player) -> str | None:
        if obj.alias.isp and obj.alias.isp.country:
            return country(obj.alias.isp.country)
        return None

    def get_coop_status(self, obj: Player) -> str:
        return _(obj.coop_status or CoopStatus.ready.value)

    def get_coop_status_slug(self, obj: Player) -> str:
        return slugify(obj.coop_status or CoopStatus.ready.value)


class PlayerWeaponSerializer(serializers.ModelSerializer):

    class Meta:
        model = Weapon
        fields = ('id', 'name', 'time', 'shots', 'hits', 'teamhits', 'kills', 'teamkills')


class ObjectiveSerializer(serializers.ModelSerializer):
    name = serializers.SerializerMethodField()
    status = serializers.SerializerMethodField()
    status_slug = serializers.SerializerMethodField()

    class Meta:
        model = Objective
        fields = ('id', 'name', 'status', 'status_slug')
        read_only_fields = fields

    def get_name(self, obj: Objective) -> str:
        return _(obj.name)

    def get_status(self, obj: Objective) -> str:
        return _(obj.status)

    def get_status_slug(self, obj: Objective) -> str:
        return slugify(obj.status)


class ProcedureSerializer(serializers.ModelSerializer):
    name = serializers.SerializerMethodField()
    is_penalty = serializers.SerializerMethodField()

    penalties = (
        'Failed to report a downed officer',
        'Incapacitated a hostage',
        'Killed a hostage',
        'Incapacitated a fellow officer',
        'Injured a fellow officer',
        'Unauthorized use of deadly force',
        'Unauthorized use xof force',
        'Failed to prevent destruction of evidence.',
        'Failed to apprehend fleeing suspect.',
    )

    class Meta:
        model = Procedure
        fields = ('id', 'name', 'status', 'score', 'is_penalty')
        read_only_fields = fields

    def get_name(self, obj: Procedure) -> str:
        return _(obj.name)

    def get_is_penalty(self, obj: Procedure) -> bool:
        return obj.name in self.penalties


class GameBaseSerializer(serializers.ModelSerializer):
    gametype = serializers.SerializerMethodField()
    gametype_short = serializers.SerializerMethodField()
    gametype_slug = serializers.SerializerMethodField()
    map = MapSerializer()
    server = ServerBaseSerializer()

    gametype_to_short_mapping: dict[str, str] = {
        GameType.barricaded_suspects.value: _('BS'),
        GameType.vip_escort.value: _('VIP'),
        GameType.rapid_deployment.value: _('RD'),
        GameType.co_op.value: _('COOP'),
        GameType.smash_and_grab.value: _('SG'),
        GameType.co_op_qmm.value: _('COOP'),
    }
    gametype_short_default = 'UNK'

    class Meta:
        model = Game
        fields: tuple[str, ...] = (
            'id', 'gametype', 'gametype_slug', 'gametype_short',
            'map', 'server', 'coop_score', 'score_swat', 'score_sus',
            'date_finished',
        )
        read_only_fields: tuple[str, ...] = fields

    def get_gametype(self, obj: Game) -> str:
        return _(obj.gametype)

    def get_gametype_short(self, obj: Game) -> str:
        """
        Map full gametype name to its short version (e.g. VIP Escort -> VIP)
        """
        return self.gametype_to_short_mapping.get(obj.gametype) or self.gametype_short_default

    def get_gametype_slug(self, obj: Game) -> str:
        return slugify(obj.gametype)


class GameNeighborsSerializer(serializers.Serializer):
    next = GameBaseSerializer()
    prev = GameBaseSerializer()


class GameSerializer(GameBaseSerializer):
    neighbors = GameNeighborsSerializer(source='get_neighboring_games', read_only=True)
    players = PlayerSerializer(many=True, source='player_set')
    objectives = ObjectiveSerializer(many=True, source='objective_set')
    procedures = ProcedureSerializer(many=True, source='procedure_set')
    rules = serializers.SerializerMethodField()
    briefing = serializers.SerializerMethodField()
    coop_rank = serializers.SerializerMethodField()

    class Meta(GameBaseSerializer.Meta):
        fields = GameBaseSerializer.Meta.fields + ('neighbors', 'players', 'objectives', 'procedures',
                                                   'time', 'outcome', 'player_num',
                                                   'rules', 'briefing', 'coop_rank',
                                                   'vict_swat', 'vict_sus', 'rd_bombs_defused', 'rd_bombs_total')
        read_only_fields: tuple[str, ...] = fields

    coop_ranks = {
        100: _('Chief Inspector'),
        95: _('Inspector'),
        90: _('Captain'),
        85: _('Lieutenant'),
        80: _('Sergeant'),
        75: _('Patrol Officer'),
        70: _('Reserve Officer'),
        60: _('Non-sworn Officer'),
        50: _('Recruit'),
        35: _('Washout'),
        20: _('Vigilante'),
    }
    coop_rank_default = _('Menace')

    def get_rules(self, obj: Game) -> str:
        return gametype_rules_text(obj.gametype)

    def get_briefing(self, obj: Game) -> str | None:
        if obj.gametype in (GameType.co_op, GameType.co_op_qmm):
            return map_briefing_text(obj.map.name)
        return None

    def get_coop_rank(self, obj: Game) -> str | None:
        if obj.gametype not in (GameType.co_op, GameType.co_op_qmm):
            return None

        for min_score, title in self.coop_ranks.items():
            if obj.coop_score >= min_score:
                return title

        return self.coop_rank_default


class GamePlayerHighlightSerializer(serializers.Serializer):
    player = PlayerSerializer()
    title = serializers.CharField()
    description = serializers.CharField()


class LoadoutSerializer(serializers.ModelSerializer):
    class Meta:
        model = Loadout
        fields = ('primary', 'secondary',
                  'equip_one', 'equip_two', 'equip_three', 'equip_four', 'equip_five',
                  'breacher', 'head', 'body')


class ProfileSerializer(serializers.ModelSerializer):
    loadout = LoadoutSerializer()

    class Meta:
        model = Profile
        fields = ('id', 'name', 'team', 'loadout',
                  'country', 'country_human', 'first_seen_at', 'last_seen_at')
        read_only_fields = fields


class PlayerStatSerializer(serializers.ModelSerializer):
    profile = ProfileSerializer()

    class Meta:
        model = PlayerStats
        fields = ('id', 'category', 'year', 'profile', 'points', 'position')
        read_only_fields = fields
