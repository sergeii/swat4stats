from django import apps


class AppConfig(apps.AppConfig):
    name = "apps.tracker"

    def ready(self):
        from swat4stats import celery  # noqa: F401
        from . import signals  # noqa: F401
