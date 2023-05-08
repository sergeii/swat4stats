from django.db.models import QuerySet
from rest_framework.mixins import ListModelMixin
from rest_framework.viewsets import GenericViewSet

from apps.api.serializers import NewsArticleSerializer
from apps.news.models import Article


class ArticleViewSet(ListModelMixin, GenericViewSet):
    queryset = Article.objects.all()
    serializer_class = NewsArticleSerializer
    pagination_class = None

    def get_queryset(self) -> QuerySet[Article]:
        return super().get_queryset().latest_published(5)
