import factory
from django.utils.encoding import force_bytes
from factory import fuzzy


class PlayerQueryResponse(dict):
    def to_items(self):
        items = []
        player_id = self.pop("id")
        for key, value in self.items():
            items.extend(
                [
                    f"{key}_{player_id}",
                    value,
                ]
            )
        return items


class ServerQueryResponse(dict):
    def to_items(self):
        items = []
        for key, value in self.items():
            if key in ("players", "objectives"):
                for sub_item in value:
                    items.extend(sub_item.to_items())
            else:
                items.extend((key, value))
        return items

    def as_gamespy(self) -> bytes:
        items = [*self.to_items(), "queryid", "1", "final"]
        return b"\\" + b"\\".join(map(force_bytes, items)) + b"\\"


class PlayerQueryFactory(factory.Factory):
    id = factory.Sequence(str)
    player = factory.Faker("first_name")
    ping = fuzzy.FuzzyInteger(25, 9999)
    score = fuzzy.FuzzyInteger(10, 30)
    kills = fuzzy.FuzzyInteger(0, 1)
    vip = 0

    class Meta:
        model = PlayerQueryResponse


class ServerQueryFactory(factory.Factory):
    hostname = "Swat4 Server"
    hostport = 10480
    password = 0
    gamevariant = "SWAT 4"
    gamever = "1.1"
    gametype = "VIP Escort"
    mapname = "A-Bomb Nightclub"
    numplayers = 0
    maxplayers = 16
    round = 4
    numrounds = 5
    swatscore = 100
    suspectsscore = 0
    players = []
    objectives = []

    class Meta:
        model = ServerQueryResponse

    @factory.post_generation
    def with_players_count(obj, create, extracted, **kwargs):
        if extracted:
            obj["players"] = PlayerQueryFactory.create_batch(extracted)


class ServerStatusFactory(factory.DictFactory):
    hostname = "Swat4 Server"
    hostport = 10480
    password = 0
    statsenabled = 0
    gamevariant = "SWAT 4"
    gamever = "1.1"
    gametype = "VIP Escort"
    mapname = "A-Bomb Nightclub"
    numplayers = 0
    maxplayers = 16
    round = 4
    numrounds = 5
    timeleft = 100
    timespecial = 0
    swatscore = 10
    suspectsscore = 10
    swatwon = 1
    suspectswon = 2
    bombsdefused = 0
    bombstotal = 0
    tocreports = 0
    weaponssecured = 0
    players = []
    objectives = []
