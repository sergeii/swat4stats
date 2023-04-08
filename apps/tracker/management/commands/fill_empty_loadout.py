import logging

from django.core.management.base import BaseCommand

from apps.tracker.models import Loadout, Player
from apps.utils.misc import iterate_queryset

logger = logging.getLogger(__name__)


class Command(BaseCommand):

    def handle(self, *args, **options):
        console = logging.StreamHandler()
        logger.addHandler(console)

        empty_loadout, _ = (
            Loadout.objects
            .get_or_create(
                primary='None',
                primary_ammo='None',
                secondary='None',
                secondary_ammo='None',
                equip_one='None',
                equip_two='None',
                equip_three='None',
                equip_four='None',
                equip_five='None',
                breacher='None',
                head='None',
                body='None',
                defaults={
                    'primary_legacy': 0,
                    'primary_ammo_legacy': 0,
                    'secondary_legacy': 0,
                    'secondary_ammo_legacy': 0,
                    'equip_one_legacy': 0,
                    'equip_two_legacy': 0,
                    'equip_three_legacy': 0,
                    'equip_four_legacy': 0,
                    'equip_five_legacy': 0,
                    'breacher_legacy': 0,
                    'head_legacy': 0,
                    'body_legacy': 0,
                }
            )
        )

        qs = Player.objects.filter(loadout__isnull=True)
        for chunk in iterate_queryset(qs, chunk_size=5000):
            for item in chunk:
                item.loadout_id = empty_loadout.pk
            Player.objects.bulk_update(chunk, ['loadout_id'])
