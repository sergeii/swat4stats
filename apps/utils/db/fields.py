from django.utils.translation import gettext_lazy as _
from django.db.models import TextField


class EnumField(TextField):
    description = _("Enum")

    def __init__(self, *, enum_type=None, **kwargs):
        self.enum_type = enum_type
        super().__init__(**kwargs)

    def db_type(self, connection):
        return self.enum_type

    def deconstruct(self):
        name, path, args, kwargs = super().deconstruct()
        kwargs["enum_type"] = self.enum_type
        return name, path, args, kwargs
