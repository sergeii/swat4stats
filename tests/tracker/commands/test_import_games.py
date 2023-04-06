from django.core.management import call_command

from apps.tracker.factories import ServerGameDataFactory
from apps.tracker.models import Game


def test_import_games(db, tmpdir):
    game_data = ServerGameDataFactory(tag='foobar', with_players_count=16)
    path = tmpdir.join('data.txt')

    with path.open('wb') as f:
        f.write(game_data.to_julia_v1().encode())
        f.write(b'\n')

    call_command('import_games', str(path))
    game = Game.objects.get(tag='foobar')
    assert game.player_set.count() == 16
