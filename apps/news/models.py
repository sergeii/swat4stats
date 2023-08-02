import logging
from typing import ClassVar

from django.db import models
from django.utils import timezone
from django.utils.functional import cached_property
from django.utils.translation import gettext_lazy as _

from apps.news.entities import RendererType
from apps.news.renderer import PlainRenderer, MarkdownRenderer, HtmlRenderer, BaseRenderer

logger = logging.getLogger(__name__)


class PublishedArticleQuerySet(models.QuerySet):
    def published(self) -> models.QuerySet["Article"]:
        return self.filter(is_published=True, date_published__lte=timezone.now())

    def latest_published(self, limit: int) -> models.QuerySet["Article"]:
        return self.published().order_by("-date_published", "pk")[:limit]


class Article(models.Model):
    renderers: ClassVar[dict[RendererType, type[BaseRenderer]]] = {
        RendererType.PLAINTEXT: PlainRenderer,
        RendererType.MARKDOWN: MarkdownRenderer,
        RendererType.HTML: HtmlRenderer,
    }

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

    objects = PublishedArticleQuerySet.as_manager()

    class Meta:
        db_table = "tracker_article"

    def __str__(self) -> str:
        return self.title

    @cached_property
    def rendered(self) -> str:
        """
        Render article text according to the specified renderer.

        :return: Rendered article text
        """
        try:
            renderer = self.renderers[self.renderer]
        except KeyError:
            logger.error("No article renderer %s", self.renderer)
            renderer = self.renderers[self._meta.get_field("renderer").default]

        return renderer.render(self.text)
