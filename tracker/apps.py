from django import apps


class AppConfig(apps.AppConfig):
    name = 'tracker'

    def ready(self):
        from swat4tracker import celery  # noqa
