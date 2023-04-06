import logging

from django.core.management.base import BaseCommand
from django.db.models import Q, Model


logger = logging.getLogger(__name__)


def fill_profile_last_seen(profile_model: type[Model]):
    queryset = (profile_model.objects
                .only('game_first__date_finished', 'game_last__date_finished')
                .select_related('game_first', 'game_last')
                .filter(Q(first_seen_at__isnull=True) | Q(last_seen_at__isnull=True)))

    logger.info('updating last_seen for %s profiles', queryset.count())

    for profile in queryset:
        game_first_date = profile.game_first and profile.game_first.date_finished
        game_last_date = profile.game_last and profile.game_last.date_finished

        logger.info('setting last_seen=%s first_seen=%s for profile %s',
                    game_first_date, game_last_date, profile.pk)
        profile.first_seen_at = game_first_date
        profile.last_seen_at = game_last_date

    profile_model.objects.bulk_update(queryset, fields=['first_seen_at', 'last_seen_at'], batch_size=100)


class Command(BaseCommand):

    def handle(self, *args, **options):
        from apps.tracker.models import Profile

        console = logging.StreamHandler()
        logger.addHandler(console)
        fill_profile_last_seen(Profile)
