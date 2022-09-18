import datetime
from unittest.mock import patch, PropertyMock

import pytest
from django.db.models import ProtectedError
from django.utils import timezone
from django.utils.safestring import SafeText, SafeData

from tracker import models
from tracker.definitions import STAT
from tracker.factories import ProfileFactory


class TestRank:

    def test_overwrite_category_points(self, db):
        profile = ProfileFactory()

        models.Rank.objects.store(profile=profile,
                                  category=STAT.SCORE,
                                  year=2014,
                                  points=77)
        assert models.Rank.objects.get(profile=profile, category=STAT.SCORE, year=2014).points == 77

        models.Rank.objects.store(profile=profile,
                                  category=STAT.SCORE,
                                  year=2014,
                                  points=78)
        assert models.Rank.objects.get(profile=profile, category=STAT.SCORE, year=2014).points == 78

        assert models.Rank.objects.count() == 1

    def test_set_multiple_category_points(self, db):
        profile = ProfileFactory()
        cats = [STAT.SCORE, STAT.TIME, STAT.SPM, STAT.SPR, STAT.GAMES]

        for cat in cats:
            models.Rank.objects.store(category=cat, year=2014, profile=profile, points=77)
        assert models.Rank.objects.filter(year=2014, profile=profile).count() == 5

        # another period, same categories
        for cat in cats:
            models.Rank.objects.store(category=cat, year=2015, profile=profile, points=77)
        assert models.Rank.objects.filter(year=2015, profile=profile).count() == 5

        assert models.Rank.objects.filter(profile=profile).count() == 10

    def test_position_is_empty_by_default(self, db):
        profile = ProfileFactory()
        cats = [STAT.SCORE, STAT.TIME, STAT.SPM, STAT.SPR, STAT.GAMES]
        for cat in cats:
            models.Rank.objects.store(category=cat, year=2013, profile=profile, points=77)
        for cat in cats:
            assert models.Rank.objects.get(category=cat, year=2013, profile=profile).position is None


class TestRankPositions:

    def test_rank_positions_same_score_sorts_by_id(self, db):
        profiles = ProfileFactory.create_batch(5)
        for profile in profiles[:-1]:
            models.Rank.objects.store(STAT.SPM, 2014, profile, 77)
        models.Rank.objects.store(STAT.SPM, 2014, profiles[-1], 78)

        models.Rank.objects.rank(2014)
        assert models.Rank.objects.get(category=STAT.SPM, profile=profiles[-1].pk).position == 1
        assert models.Rank.objects.get(category=STAT.SPM, profile=profiles[0].pk).position == 2
        assert models.Rank.objects.get(category=STAT.SPM, profile=profiles[1].pk).position == 3
        assert models.Rank.objects.get(category=STAT.SPM, profile=profiles[2].pk).position == 4
        assert models.Rank.objects.get(category=STAT.SPM, profile=profiles[3].pk).position == 5

    def test_rank_positions_specific_year(self, db):
        profiles = ProfileFactory.create_batch(5)

        time_stats_2014 = [1023, 475, 1575, 2575, 6575]
        score_stats_2014 = [452, 473, 21]
        for i, points in enumerate(time_stats_2014):
            models.Rank.objects.store(STAT.TIME, 2014, profiles[i], points)
        for i, points in enumerate(score_stats_2014):
            models.Rank.objects.store(STAT.SCORE, 2014, profiles[i], points)

        time_stats_2013 = [1123, 2457, 9827, 4571, 2524]
        for i, points in enumerate(time_stats_2013):
            models.Rank.objects.store(STAT.TIME, 2013, profiles[i], points)

        models.Rank.objects.rank(2014)

        assert models.Rank.objects.get(year=2014, category=STAT.TIME, profile=profiles[0]).position == 4
        assert models.Rank.objects.get(year=2014, category=STAT.TIME, profile=profiles[1]).position == 5
        assert models.Rank.objects.get(year=2014, category=STAT.TIME, profile=profiles[2]).position == 3
        assert models.Rank.objects.get(year=2014, category=STAT.TIME, profile=profiles[3]).position == 2
        assert models.Rank.objects.get(year=2014, category=STAT.TIME, profile=profiles[4]).position == 1

        assert models.Rank.objects.get(year=2014, category=STAT.SCORE, profile=profiles[0]).position == 2
        assert models.Rank.objects.get(year=2014, category=STAT.SCORE, profile=profiles[1]).position == 1
        assert models.Rank.objects.get(year=2014, category=STAT.SCORE, profile=profiles[2]).position == 3

        for rank in models.Rank.objects.filter(year=2013):
            assert rank.position is None

        models.Rank.objects.rank(2013)

        assert models.Rank.objects.get(year=2013, category=STAT.TIME, profile=profiles[0]).position == 5
        assert models.Rank.objects.get(year=2013, category=STAT.TIME, profile=profiles[1]).position == 4
        assert models.Rank.objects.get(year=2013, category=STAT.TIME, profile=profiles[2]).position == 1
        assert models.Rank.objects.get(year=2013, category=STAT.TIME, profile=profiles[3]).position == 2
        assert models.Rank.objects.get(year=2013, category=STAT.TIME, profile=profiles[4]).position == 3

    def test_recalculate_positions(self, db):
        profiles = ProfileFactory.create_batch(5)

        time_stats = [1023, 475, 1575, 2575, 6575]
        for i, points in enumerate(time_stats):
            models.Rank.objects.store(STAT.TIME, 2014, profiles[i], points)

        models.Rank.objects.rank(2014)
        assert models.Rank.objects.get(year=2014, category=STAT.TIME, profile=profiles[0]).position == 4
        assert models.Rank.objects.get(year=2014, category=STAT.TIME, profile=profiles[1]).position == 5
        assert models.Rank.objects.get(year=2014, category=STAT.TIME, profile=profiles[2]).position == 3
        assert models.Rank.objects.get(year=2014, category=STAT.TIME, profile=profiles[3]).position == 2
        assert models.Rank.objects.get(year=2014, category=STAT.TIME, profile=profiles[4]).position == 1

        models.Rank.objects.store(STAT.TIME, 2014, profiles[0], 9999)
        models.Rank.objects.rank(2014)
        assert models.Rank.objects.get(year=2014, category=STAT.TIME, profile=profiles[0]).position == 1
        assert models.Rank.objects.get(year=2014, category=STAT.TIME, profile=profiles[1]).position == 5
        assert models.Rank.objects.get(year=2014, category=STAT.TIME, profile=profiles[2]).position == 4
        assert models.Rank.objects.get(year=2014, category=STAT.TIME, profile=profiles[3]).position == 3
        assert models.Rank.objects.get(year=2014, category=STAT.TIME, profile=profiles[4]).position == 2


class TestPlayerForeignFields:

    @pytest.fixture
    def test_profile(self, db):
        return models.Profile.objects.create()

    @pytest.fixture
    def test_alias(self, test_profile):
        return models.Alias.objects.create(profile=test_profile, name='Serge')

    @pytest.fixture
    def test_server(self, db):
        return models.Server.objects.create(ip='127.0.0.100', port=10480, enabled=True)

    @pytest.fixture
    def test_game(self, test_server):
        return models.Game.objects.create(server=test_server)

    def test_cannot_delete_related_loadout(self, test_alias, test_game):
        loadout = models.Loadout.objects.create()
        player = models.Player.objects.create(game=test_game, alias=test_alias, loadout=loadout, ip='127.0.0.1')
        assert models.Player.objects.get(pk=player.pk).loadout.pk == loadout.pk
        with pytest.raises(ProtectedError):
            loadout.delete()

    def test_cannot_delete_related_alias(self, test_alias, test_game):
        player = models.Player.objects.create(game=test_game, alias=test_alias, ip='127.0.0.1')
        assert models.Player.objects.get(pk=player.pk).alias.pk == test_alias.pk
        with pytest.raises(ProtectedError):
            test_alias.delete()

    def test_delete_related_game_removes_the_player_oncascade(self, test_alias, test_game):
        player = models.Player.objects.create(game=test_game, alias=test_alias, ip='127.0.0.1')
        assert models.Player.objects.get(pk=player.pk).game.pk == test_game.pk
        test_game.delete()
        assert models.Player.objects.filter(pk=player.pk).count() == 0

    def test_delete_related_profile_removes_the_alias_oncascade(self, test_profile, test_alias, test_game):
        test_profile.delete()
        assert models.Alias.objects.filter(pk=test_alias.pk).count() == 0


class TestProfile:

    @pytest.fixture
    def test_server(self, db):
        return models.Server.objects.create(ip='127.0.0.100', port=10480, enabled=True)

    @pytest.fixture
    def test_game(self, test_server):
        return models.Game.objects.create(server=test_server)

    @pytest.mark.parametrize('name', [
        'Player', 'player', 'Player2', 'player3',
        'newname', 'swat', 'lol', 'TODOsetname2231',
        'afk', 'afk5min', 'afk_dont_kick', 'killer',
        'spieler', 'gracz', 'testing', 'test', 'testing_mod',
    ])
    def test_popular_names(self, name):
        assert models.Profile.is_name_popular(name)

    def test_popular_qualification(self, test_server):
        real_now = timezone.now

        with patch.object(timezone, 'now') as mock:
            mock.return_value = real_now() - datetime.timedelta(seconds=models.Profile.TIME_POPULAR + 100)
            game = models.Game.objects.create(server=test_server)

        profile = models.Profile.objects.create()

        game.player_set.create(alias=profile.alias_set.create(name='Player', isp=None), ip='127.0.0.1')
        game.player_set.create(alias=profile.alias_set.create(name='Serge', isp=None), ip='127.0.0.1')

        assert profile.fetch_popular_name() is None

        game = models.Game.objects.create(server=test_server)
        game.player_set.create(alias=profile.alias_set.create(name='Serge', isp=None), ip='127.0.0.1')

        with patch.object(models.Profile, 'MIN_PLAYERS', new=PropertyMock(return_value=0)):
            assert profile.fetch_popular_name() == 'Serge'

    def test_popular_name(self, test_server, test_game):
        profile = models.Profile.objects.create()
        models.Player.objects.create(game=test_game,
                                     alias=profile.alias_set.create(name='afk', isp=None), ip='127.0.0.1')
        models.Player.objects.create(game=test_game,
                                     alias=profile.alias_set.create(name='Player', isp=None), ip='127.0.0.1')
        models.Player.objects.create(game=test_game,
                                     alias=profile.alias_set.create(name='Serge', isp=None), ip='127.0.0.1')
        models.Player.objects.create(game=test_game,
                                     alias=profile.alias_set.create(name='Serge', isp=None), ip='127.0.0.1')
        models.Player.objects.create(game=test_game,
                                     alias=profile.alias_set.create(name='Serge', isp=None), ip='127.0.0.4')
        models.Player.objects.create(game=test_game,
                                     alias=profile.alias_set.create(name='Player', isp=None), ip='127.0.0.3')

        another_profile = models.Profile.objects.create()
        models.Player.objects.create(game=test_game,
                                     alias=another_profile.alias_set.create(name='Player', isp=None), ip='127.0.0.1')
        models.Player.objects.create(game=test_game,
                                     alias=another_profile.alias_set.create(name='Serge', isp=None), ip='127.0.0.7')
        models.Player.objects.create(game=test_game,
                                     alias=another_profile.alias_set.create(name='Player', isp=None), ip='127.0.0.2')
        models.Player.objects.create(game=test_game,
                                     alias=another_profile.alias_set.create(name='Player', isp=None), ip='127.0.0.3')

        with patch.object(models.Profile, 'MIN_PLAYERS', new=PropertyMock(return_value=0)):
            assert profile.fetch_popular_name() == 'Serge'
            assert another_profile.fetch_popular_name() == 'Player'

    def test_popular_country(self, test_game):
        profile = models.Profile.objects.create()

        isp1 = models.ISP.objects.create(country='un')
        isp2 = models.ISP.objects.create(country='eu')
        isp3 = models.ISP.objects.create(country='uk')

        models.Player.objects.create(game=test_game,
                                     alias=profile.alias_set.create(name='Serge', isp=isp1), ip='127.0.0.1')
        models.Player.objects.create(game=test_game,
                                     alias=profile.alias_set.create(name='Player', isp=isp1), ip='127.0.0.121')
        models.Player.objects.create(game=test_game,
                                     alias=profile.alias_set.create(name='Serge', isp=isp2), ip='127.0.0.143')
        models.Player.objects.create(game=test_game,
                                     alias=profile.alias_set.create(name='Serge', isp=isp2), ip='127.0.0.11')
        models.Player.objects.create(game=test_game,
                                     alias=profile.alias_set.create(name='Serge', isp=isp2), ip='127.0.0.12')
        models.Player.objects.create(game=test_game,
                                     alias=profile.alias_set.create(name='Player', isp=isp3), ip='127.0.0.3')

        with patch.object(models.Profile, 'MIN_PLAYERS', new=PropertyMock(return_value=0)):
            assert profile.fetch_popular_country() == 'eu'

    def test_popular_team(self, test_game):
        profile = models.Profile.objects.create()

        models.Player.objects.create(game=test_game,
                                     alias=profile.alias_set.create(name='afk', isp=None), ip='127.0.0.1', team=0)
        models.Player.objects.create(game=test_game,
                                     alias=profile.alias_set.create(name='Player', isp=None), ip='127.0.0.1', team=0)
        models.Player.objects.create(game=test_game,
                                     alias=profile.alias_set.create(name='Serge', isp=None), ip='127.0.0.1', team=0)
        models.Player.objects.create(game=test_game,
                                     alias=profile.alias_set.create(name='Serge', isp=None), ip='127.0.0.1', team=1)
        models.Player.objects.create(game=test_game,
                                     alias=profile.alias_set.create(name='Serge', isp=None), ip='127.0.0.4', team=1)
        models.Player.objects.create(game=test_game,
                                     alias=profile.alias_set.create(name='Player', isp=None), ip='127.0.0.3', team=0)

        with patch.object(models.Profile, 'MIN_PLAYERS', new=PropertyMock(return_value=0)):
            assert profile.fetch_popular_team() == 0


class TestArticle:
    html_text = (
        ('<script>alert()</script>', '&lt;script&gt;alert()&lt;/script&gt;'),
        ("""<a href="javascript:document.location='http://www.google.com/'">xss</a>""",
         '<a>xss</a>'),
        ('<a href="https://example.org/" onclick=alert(1)>xss</a>',
         '<a href="https://example.org/">xss</a>'),
        ("""<img src="javascript:alert('XSS');">""", '<img>'),
        ('<p>foo</p>', '<p>foo</p>'),
        ('<b>foo</b>', '<b>foo</b>'),
        ('<a href="https://www.youtube.com/">foo</a>', '<a href="https://www.youtube.com/">foo</a>'),
        ('<iframe width="560" height="315" src="https://www.youtube.com/" frameborder="0" allowfullscreen></iframe>',
         '<iframe width="560" height="315" src="https://www.youtube.com/" frameborder="0" allowfullscreen=""></iframe>'),  # noqa
        ('<img src="http://example.org/picture.png" />', '<img src="http://example.org/picture.png">'),
    )
    markdown_text = (
        ('* foo', '<ul>\n<li>foo</li>\n</ul>'),
        ('* <b>foo</b>', '<ul>\n<li>&lt;b&gt;foo&lt;/b&gt;</li>\n</ul>'),
    )

    def test_html_renderer(self):
        text = '<b>Foo!</b>'
        article = models.Article(text=text, renderer=models.Article.RENDERER_HTML)
        assert article.rendered == text
        assert isinstance(article.rendered, SafeText)
        assert isinstance(article.rendered, SafeData)

    def test_plaintext_renderer(self):
        text = '<b>Foo!</b>'
        article = models.Article(text=text, renderer=models.Article.RENDERER_PLAINTEXT)
        assert article.rendered == text
        assert not isinstance(article.rendered, SafeData)

    def test_markdown_renderer(self):
        text = '* foo'
        article = models.Article(text=text, renderer=models.Article.RENDERER_MARKDOWN)
        assert article.rendered == '<ul>\n<li>foo</li>\n</ul>'
        assert isinstance(article.rendered, SafeText)

    def test_default_renderer_is_markdown(self, db):
        article = models.Article.objects.create(text='foo')
        assert models.Article.objects.get(pk=article.pk).renderer == models.Article.RENDERER_MARKDOWN

    def test_default_renderer_for_invalid_values_is_markdown(self, db):
        article = models.Article.objects.create(text='foo', renderer=9999)
        assert models.Article.objects.get(pk=article.pk).rendered == '<p>foo</p>'

    @pytest.mark.parametrize('raw_text, expected_html', html_text)
    def test_html_text(self, raw_text, expected_html):
        article = models.Article(text=raw_text, renderer=models.Article.RENDERER_HTML)
        assert article.rendered == expected_html

    @pytest.mark.parametrize('raw_text, expected_html', markdown_text)
    def test_markdown_text(self, raw_text, expected_html):
        article = models.Article(text=raw_text, renderer=models.Article.RENDERER_MARKDOWN)
        assert article.rendered == expected_html
