from django import apps


class AppConfig(apps.AppConfig):
    name = "apps.tracker"

    def ready(self) -> None:
        from swat4stats import celery  # noqa: F401
        from . import signals  # noqa: F401
