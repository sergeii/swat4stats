import factory
from django.utils import timezone
from factory import fuzzy

from apps.tracker.entities import LegacyStatCategory
from apps.tracker.models import PlayerStats, ServerStats, MapStats, GametypeStats

from tests.factories.tracker import ProfileFactory, ServerFactory, MapFactory


class AbstractStatsFactory(factory.django.DjangoModelFactory):
    category = fuzzy.FuzzyChoice(["score", "kills", "deaths", "teamkills", "suicides"])
    profile = factory.SubFactory(ProfileFactory)
    year = factory.LazyAttribute(lambda o: timezone.now().year)
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
    map = factory.SubFactory(MapFactory)  # noqa: A003

    class Meta:
        model = MapStats


class GametypeStatsFactory(AbstractStatsFactory):
    gametype = "VIP Escort"

    class Meta:
        model = GametypeStats
