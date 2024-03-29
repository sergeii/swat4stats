import factory

from apps.news.entities import RendererType
from apps.news.models import Article


class ArticleFactory(factory.django.DjangoModelFactory):
    title = factory.Faker("text", max_nb_chars=64)
    text = factory.Faker("text")
    signature = ""
    is_published = True
    renderer = RendererType.HTML

    class Meta:
        model = Article
