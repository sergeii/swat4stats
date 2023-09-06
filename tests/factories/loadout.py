from factory import django, fuzzy

from apps.tracker.models import Loadout
from apps.tracker.schema import ammo_encoded, equipment_encoded


class LoadoutFactory(django.DjangoModelFactory):
    class Meta:
        model = Loadout
        django_get_or_create = (
            "primary",
            "secondary",
            "primary_ammo",
            "secondary_ammo",
            "equip_one",
            "equip_two",
            "equip_three",
            "equip_four",
            "equip_five",
            "head",
            "body",
            "breacher",
        )

    primary = "None"
    primary_ammo = "None"
    secondary = "None"
    secondary_ammo = "None"
    equip_one = "None"
    equip_two = "None"
    equip_three = "None"
    equip_four = "None"
    equip_five = "None"
    breacher = "None"
    head = "None"
    body = "None"


class RandomLoadoutFactory(LoadoutFactory):
    primary = fuzzy.FuzzyChoice(equipment_encoded.values())
    primary_ammo = fuzzy.FuzzyChoice(ammo_encoded.values())
    secondary = fuzzy.FuzzyChoice(equipment_encoded.values())
    secondary_ammo = fuzzy.FuzzyChoice(ammo_encoded.values())
    equip_one = fuzzy.FuzzyChoice(equipment_encoded.values())
    equip_two = fuzzy.FuzzyChoice(equipment_encoded.values())
    equip_three = fuzzy.FuzzyChoice(equipment_encoded.values())
    equip_four = fuzzy.FuzzyChoice(equipment_encoded.values())
    equip_five = fuzzy.FuzzyChoice(equipment_encoded.values())
    breacher = fuzzy.FuzzyChoice(equipment_encoded.values())
    head = fuzzy.FuzzyChoice(equipment_encoded.values())
    body = fuzzy.FuzzyChoice(equipment_encoded.values())
