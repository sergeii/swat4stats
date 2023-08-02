from django.db import models

from apps.tracker.entities import Equipment
from apps.tracker.schema import ammo_reversed, equipment_reversed


class LoadoutManager(models.Manager):
    equipment_fields = (
        "primary",
        "secondary",
        "equip_one",
        "equip_two",
        "equip_three",
        "equip_four",
        "equip_five",
        "breacher",
        "head",
        "body",
    )
    ammo_fields = ("primary_ammo", "secondary_ammo")
    loadout_fields = equipment_fields + ammo_fields

    def obtain(self, **loadout):
        # substitute missing loadout keys with None's
        loadout = {
            field: loadout.get(field) or Equipment.none.value
            for field in LoadoutManager.loadout_fields
        }

        legacy_loadout = {}
        for field in LoadoutManager.ammo_fields:
            legacy_loadout[f"{field}_legacy"] = ammo_reversed[loadout[field]]
        for field in LoadoutManager.equipment_fields:
            legacy_loadout[f"{field}_legacy"] = equipment_reversed[loadout[field]]

        obj, _ = self.get_or_create(**loadout, defaults=legacy_loadout)
        return obj
