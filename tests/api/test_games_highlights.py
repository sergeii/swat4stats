from apps.tracker.factories import GameFactory, PlayerFactory, WeaponFactory


def test_get_game_highlights_unknown_404(db, api_client):
    resp = api_client.get("/api/games/100500/highlights/")
    assert resp.status_code == 404


def test_get_game_highlights_no_players(db, api_client):
    game = GameFactory()
    resp = api_client.get(f"/api/games/{game.pk}/highlights/")
    assert resp.status_code == 200
    assert resp.data == []


def test_get_game_highlights_versus_game(db, api_client, django_assert_num_queries):
    game = GameFactory(gametype="VIP Escort")
    dropped = PlayerFactory(game=game, dropped=True, alias__name="Grasz", alias__isp__country="pl")
    WeaponFactory(player=dropped, name="9mm SMG", kills=10, hits=100, shots=100)

    player1 = PlayerFactory(
        game=game,
        dropped=False,
        alias__name="|MYT|dimonkey",
        alias__isp__country="gb",
        score=21,
        kills=21,
        kill_streak=9,
        arrest_streak=4,
        deaths=9,
    )
    WeaponFactory(player=player1, name="9mm SMG", kills=10, hits=100, shots=200)
    WeaponFactory(player=player1, name="9mm Handgun", kills=1, hits=1, shots=2000)

    player2 = PlayerFactory(
        game=game,
        dropped=False,
        alias__name="Pioterator",
        alias__isp__country="pl",
        vip=True,
        score=4,
        kills=10,
        teamkills=2,
        kill_streak=10,
    )
    WeaponFactory(player=player2, name="9mm SMG", hits=1, shots=9999)
    WeaponFactory(player=player2, name="Suppressed 9mm SMG", hits=1, shots=1)
    WeaponFactory(player=player2, name="Flashbang", hits=4, shots=10)
    WeaponFactory(player=player2, name="Stinger", hits=1, shots=10)

    player3 = PlayerFactory(
        game=game,
        dropped=False,
        alias__name="|MYT|Ven>SrM<",
        score=12,
        arrests=1,
        kills=7,
        deaths=10,
        kill_streak=5,
    )
    WeaponFactory(player=player3, name="Flashbang", hits=12, shots=5)
    WeaponFactory(player=player3, name="Stinger", hits=0, shots=5)

    player4 = PlayerFactory(
        game=game,
        dropped=False,
        alias__name="|MYT|Q",
        score=34,
        arrests=1,
        kills=4,
        deaths=12,
        kill_streak=5,
        vip_captures=2,
    )
    WeaponFactory(player=player4, name="Colt M4A1 Carbine", kills=10, hits=20, shots=200)
    WeaponFactory(player=player4, name="9mm SMG", kills=1, hits=65, shots=65)

    with django_assert_num_queries(6):
        resp = api_client.get(f"/api/games/{game.pk}/highlights/")

    assert resp.status_code == 200
    hl1, hl2, hl3, hl4, hl5, hl6, hl7, hl8 = resp.data

    assert hl1["player"]["id"] == player4.pk
    assert hl1["title"] == "No Exit"
    assert hl1["description"] == "2 VIP captures"

    assert hl2["player"]["id"] == player2.pk
    assert hl2["title"] == "Undying"
    assert hl2["description"] == "10 enemies killed in a row"

    assert hl3["player"]["id"] == player4.pk
    assert hl3["title"] == "Top Gun"
    assert hl3["description"] == "34 points earned"

    assert hl4["player"]["id"] == player3.pk
    assert hl4["title"] == "Fire in the hole!"
    assert hl4["description"] == "100% of grenades hit their targets"

    assert hl5["player"]["id"] == player4.pk
    assert hl5["title"] == "Sharpshooter"
    assert hl5["description"] == "32% of all shots hit targets"

    assert hl6["player"]["id"] == player1.pk
    assert hl6["player"]["name"] == "|MYT|dimonkey"
    assert hl6["player"]["country"] == "gb"
    assert hl6["player"]["country_human"] == "United Kingdom"
    assert hl6["title"] == "Killing Machine"
    assert hl6["description"] == "21 enemies eliminated"

    assert hl7["player"]["id"] == player2.pk
    assert hl7["title"] == "Resourceful"
    assert hl7["description"] == "10000 rounds of ammo fired"

    assert hl8["player"]["id"] == player1.pk
    assert hl8["title"] == "9mm SMG Expert"
    assert hl8["description"] == "10 kills with average accuracy of 50%"


def test_get_coop_game_highlights(db, api_client):
    game = GameFactory(gametype="CO-OP")
    player1 = PlayerFactory(
        game=game,
        alias__name="Mosquito",
        dropped=False,
        coop_hostage_arrests=1,
        coop_enemy_arrests=1,
        coop_enemy_incaps=5,
        coop_enemy_kills=4,
        coop_toc_reports=15,
    )
    player2 = PlayerFactory(
        game=game,
        alias__name="|||ALPHA|||boti",
        dropped=False,
        coop_hostage_arrests=9,
        coop_enemy_arrests=8,
        coop_enemy_incaps=5,
        coop_toc_reports=12,
    )
    player3 = PlayerFactory(  # noqa: F841
        game=game,
        alias__name="Serge",
        dropped=False,
        coop_hostage_arrests=6,
        coop_enemy_arrests=6,
        coop_enemy_kills=5,
        coop_toc_reports=14,
    )
    player4 = PlayerFactory(  # noqa: F841
        game=game, alias__name="Spieler", dropped=True, coop_hostage_arrests=10, coop_toc_reports=17
    )

    resp = api_client.get(f"/api/games/{game.pk}/highlights/")
    assert resp.status_code == 200
    hl1, hl2, hl3, hl4 = resp.data

    assert hl1["title"] == "Entry team to TOC!"
    assert hl1["description"] == "15 reports sent to TOC"
    assert hl1["player"]["id"] == player1.pk

    assert hl2["title"] == "Hostage Crisis"
    assert hl2["description"] == "9 civilians rescued"
    assert hl2["player"]["id"] == player2.pk

    assert hl3["title"] == "The pacifist"
    assert hl3["description"] == "8 suspects secured"
    assert hl3["player"]["id"] == player2.pk

    assert hl4["title"] == "No Mercy"
    assert hl4["description"] == "9 suspects neutralized"
    assert hl4["player"]["id"] == player1.pk
