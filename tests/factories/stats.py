import factory
from django.utils import timezone
from factory import fuzzy

from apps.tracker.entities import LegacyStatCategory
from apps.tracker.models import GametypeStats, MapStats, PlayerStats, ServerStats
from tests.factories.tracker import MapFactory, ProfileFactory, ServerFactory


class AbstractStatsFactory(factory.django.DjangoModelFactory):
    category = fuzzy.FuzzyChoice(["score", "kills", "deaths", "teamkills", "suicides"])
    profile = factory.SubFactory(ProfileFactory)
    year = factory.LazyAttribute(lambda _: timezone.now().year)
    points = fuzzy.FuzzyFloat(-1000, 1000)
    position = None


class PlayerStatsFactory(AbstractStatsFactory):
    category_legacy = factory.LazyAttribute(lambda o: getattr(LegacyStatCategory, o.category))

    class Meta:
        model = PlayerStats


class ServerStatsFactory(AbstractStatsFactory):
    server = factory.SubFactory(ServerFactory)

    class Meta:
        model = ServerStats


class MapStatsFactory(AbstractStatsFactory):
    map = factory.SubFactory(MapFactory)

    class Meta:
        model = MapStats


class GametypeStatsFactory(AbstractStatsFactory):
    gametype = "VIP Escort"

    class Meta:
        model = GametypeStats
