import logging

from django.db import models
from django.utils import timezone
from django.utils.translation import gettext_lazy as _

from apps.news.entities import RendererType

logger = logging.getLogger(__name__)


class Article(models.Model):
    title = models.CharField(blank=True, max_length=64)
    text = models.TextField()
    signature = models.CharField(max_length=128, blank=True)
    is_published = models.BooleanField(default=False)
    date_published = models.DateTimeField(blank=True, default=timezone.now)
    date_created = models.DateTimeField(auto_now_add=True)
    date_updated = models.DateTimeField(auto_now=True)
    renderer = models.SmallIntegerField(
        choices=(
            (RendererType.PLAINTEXT, _("Plain text")),
            (RendererType.HTML, _("HTML")),
            (RendererType.MARKDOWN, _("Markdown")),
        ),
        default=RendererType.MARKDOWN,
    )

    class Meta:
        db_table = "tracker_article"

    def __str__(self) -> str:
        return self.title
