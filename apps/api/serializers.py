import logging

import voluptuous
from django.db import transaction
from django.utils.safestring import SafeString
from django.utils.text import slugify
from django.utils.translation import gettext_lazy as _
from django.core.validators import MinValueValidator, MaxValueValidator
from django.templatetags.static import static
from rest_framework import serializers
from rest_framework.exceptions import ValidationError

from apps.news.models import Article
from apps.tracker.models import Server, Map, Game, Player, Objective, Procedure, Weapon, PlayerStats, Profile, Loadout
from apps.tracker.schema import coop_status_encoded, serverquery_schema
from apps.tracker.utils import force_clean_name, format_name, html
from apps.tracker.templatetags import country, gametype_rules_text, map_background_picture, map_briefing_text


logger = logging.getLogger(__name__)

port_validators = [MinValueValidator(1), MaxValueValidator(65535)]


class NewsArticleSerializer(serializers.ModelSerializer):
    html = serializers.SerializerMethodField()

    class Meta:
        fields = ('id', 'title', 'html', 'signature', 'date_published')
        model = Article

    def get_html(self, obj):
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

    def get_coop_status(self, obj):
        return _(obj.get('coop_status') or self.default_coop_status)

    def get_coop_status_slug(self, obj):
        return slugify(obj.get('coop_status') or self.default_coop_status)

    def get_special(self, obj):
        return (obj['vescaped'] +
                obj['arrestedvip'] +
                obj['unarrestedvip'] +
                obj['bombsdiffused'] +
                obj['escapedcase'])

    def get_url(self, obj):
        return f"search/?player={obj['name']}/"


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

    def get_gamename(self, obj):
        return _(obj['gamevariant'])

    def get_hostname_html(self, obj):
        return format_name(obj['hostname'])

    def get_hostname_clean(self, obj):
        return force_clean_name(obj['hostname'])

    def get_mapname(self, obj):
        return _(obj['mapname'])

    def get_gametype(self, obj):
        return _(obj['gametype'])

    def get_gametype_slug(self, obj):
        return slugify(obj['gametype'])

    def get_mapname_slug(self, obj):
        return slugify(obj['mapname'])

    def get_mapname_background(self, obj):
        return map_background_picture(obj['mapname'])


class StatusObjectiveSerializer(serializers.Serializer):
    name = serializers.SerializerMethodField()
    status = serializers.SerializerMethodField()
    status_slug = serializers.SerializerMethodField()

    def get_name(self, obj):
        return _(obj['name'])

    def get_status(self, obj):
        return _(obj['status'])

    def get_status_slug(self, obj):
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

    def get_rules(self, obj):
        return gametype_rules_text(obj['gametype'])

    def get_briefing(self, obj):
        if obj['gametype'] in ('CO-OP', 'CO-OP QMM'):
            return map_briefing_text(obj['mapname'])


class ServerBaseSerializer(serializers.ModelSerializer):
    port = serializers.IntegerField(default=10480, validators=port_validators)
    status = StatusBaseSerializer(read_only=True)
    country_human = serializers.SerializerMethodField()
    name_clean = serializers.SerializerMethodField()
    address = serializers.CharField(read_only=True)

    class Meta:
        model = Server
        read_only_fields = ('id', 'pinned',
                            'country', 'country_human', 'hostname', 'name_clean', 'status',
                            'address')
        fields = read_only_fields + ('ip', 'port',)
        validators = []

    def get_country_human(self, obj):
        if obj.country:
            return country(obj.country)
        return None

    def get_name_clean(self, obj):
        return force_clean_name(obj.name)

    def validate(self, attrs):
        ip = attrs['ip']
        port = attrs['port']

        queryset = Server.objects.filter(ip=ip, port=port)
        if queryset.exists():
            raise ValidationError(_('The specified server already exists'))

        addr_to_check = (ip, port)
        probe = Server.objects.probe_server_addrs({addr_to_check})
        raw_status = probe[addr_to_check]

        wrong_port_error = ValidationError(_('Ensure the server is running at port %(port)s') % {'port': port})

        if isinstance(raw_status, Exception):
            raise wrong_port_error

        try:
            validated_status = serverquery_schema(raw_status)
        except voluptuous.Invalid as exc:
            logger.warning('unable to create server %s:%s due to schema error: %s',
                           ip, port, exc, exc_info=True)
            raise wrong_port_error

        if validated_status['hostport'] != port:
            logger.warning('unable to create server %s:%s due to reported port mismatch: %s',
                           ip, port, validated_status['hostport'])
            raise wrong_port_error

        attrs.update({
            'listed': True,
            'status': validated_status,
            'hostname': validated_status['hostname'],
        })

        return attrs

    @transaction.atomic
    def create(self, validated_data):
        """
        Attempt to fetch status for the newly created server.

        If it fails, raise an exception to rollback the savepoint.
        """
        status = validated_data.pop('status')
        instance = super().create(validated_data)
        instance.update_with_status(status)
        instance.status = status
        return instance


class ServerFullSerializer(ServerBaseSerializer):
    status = StatusFullSerializer(read_only=True)


class MapSerializer(serializers.ModelSerializer):
    class Meta:
        model = Map
        fields = ('id', 'name', 'slug', 'preview_picture', 'background_picture')
        read_only_fields = fields


class PlayerSerializer(serializers.ModelSerializer):
    default_coop_status = coop_status_encoded[1]

    portrait_picture = serializers.SerializerMethodField()
    country = serializers.SerializerMethodField()
    country_human = serializers.SerializerMethodField()
    coop_status = serializers.SerializerMethodField()
    coop_status_slug = serializers.SerializerMethodField()

    class Meta:
        model = Player
        fields = ('id', 'name', 'portrait_picture', 'country',
                  'country_human', 'team', 'coop_status', 'coop_status_slug', 'vip', 'dropped',
                  'score', 'time', 'kills', 'teamkills', 'deaths', 'suicides', 'arrests',
                  'arrested', 'kill_streak', 'arrest_streak', 'death_streak',
                  'vip_captures', 'vip_rescues', 'vip_escapes', 'vip_kills_valid', 'vip_kills_invalid',
                  'rd_bombs_defused', 'sg_escapes', 'sg_kills',
                  'coop_hostage_arrests', 'coop_hostage_hits', 'coop_hostage_incaps', 'coop_hostage_kills',
                  'coop_enemy_arrests', 'coop_enemy_incaps', 'coop_enemy_kills', 'coop_enemy_incaps_invalid',
                  'coop_enemy_kills_invalid', 'coop_toc_reports',
                  'special')

    def get_portrait_picture(self, obj):
        path_format = 'images/portraits/{name}.jpg'
        if obj.vip:
            static_path = path_format.format(name='vip')
        elif obj.loadout and obj.loadout.head and obj.loadout.body:
            head_slug = slugify(obj.loadout.head.lower())
            body_slug = slugify(obj.loadout.body.lower())
            static_path = path_format.format(name=f'{obj.team}-{body_slug}-{head_slug}')
        else:
            static_path = path_format.format(name=f'{obj.team}')
        return static(static_path)

    def get_country(self, obj):
        if obj.alias.isp and obj.alias.isp.country:
            return obj.alias.isp.country
        return None

    def get_country_human(self, obj):
        if obj.alias.isp and obj.alias.isp.country:
            return country(obj.alias.isp.country)
        return None

    def get_coop_status(self, obj):
        return _(obj.coop_status or self.default_coop_status)

    def get_coop_status_slug(self, obj):
        return slugify(obj.coop_status or self.default_coop_status)


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

    def get_name(self, obj):
        return _(obj.name)

    def get_status(self, obj):
        return _(obj.status)

    def get_status_slug(self, obj):
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
        'Unauthorized use of force',
        'Failed to prevent destruction of evidence.',
        'Failed to apprehend fleeing suspect.',
    )

    class Meta:
        model = Procedure
        fields = ('id', 'name', 'status', 'score', 'is_penalty')
        read_only_fields = fields

    def get_name(self, obj):
        return _(obj.name)

    def get_is_penalty(self, obj):
        return obj.name in self.penalties


class GameBaseSerializer(serializers.ModelSerializer):
    gametype = serializers.SerializerMethodField()
    gametype_short = serializers.SerializerMethodField()
    gametype_slug = serializers.SerializerMethodField()
    map = MapSerializer()
    server = ServerBaseSerializer()

    gametype_to_short_mapping = {
        'Barricaded Suspects': _('BS'),
        'VIP Escort': _('VIP'),
        'Rapid Deployment': _('RD'),
        'CO-OP': _('COOP'),
        'Smash And Grab': _('SG'),
        'CO-OP QMM': _('COOP'),
    }
    gametype_short_default = 'UNK'

    class Meta:
        model = Game
        fields = ('id', 'gametype', 'gametype_slug', 'gametype_short',
                  'map', 'server', 'coop_score', 'score_swat', 'score_sus',
                  'date_finished')
        read_only_fields = fields

    def get_gametype(self, obj):
        return _(obj.gametype)

    def get_gametype_short(self, obj):
        """
        Map full gametype name to its short version (e.g. VIP Escort -> VIP)
        """
        return self.gametype_to_short_mapping.get(obj.gametype) or self.gametype_short_default

    def get_gametype_slug(self, obj):
        return slugify(obj.gametype)


class GameSerializer(GameBaseSerializer):
    players = PlayerSerializer(many=True, source='player_set')
    objectives = ObjectiveSerializer(many=True, source='objective_set')
    procedures = ProcedureSerializer(many=True, source='procedure_set')
    rules = serializers.SerializerMethodField()
    briefing = serializers.SerializerMethodField()
    coop_rank = serializers.SerializerMethodField()

    class Meta(GameBaseSerializer.Meta):
        fields = GameBaseSerializer.Meta.fields + ('players', 'objectives', 'procedures',
                                                   'time', 'outcome', 'player_num',
                                                   'rules', 'briefing', 'coop_rank',
                                                   'vict_swat', 'vict_sus', 'rd_bombs_defused', 'rd_bombs_total')
        read_only_fields = fields

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

    def get_rules(self, obj):
        return gametype_rules_text(obj.gametype)

    def get_briefing(self, obj):
        if obj.gametype in ('CO-OP', 'CO-OP QMM'):
            return map_briefing_text(obj.map.name)

    def get_coop_rank(self, obj):
        if obj.gametype not in ('CO-OP', 'CO-OP QMM'):
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
