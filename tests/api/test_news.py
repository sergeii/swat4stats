from datetime import timedelta

from django.utils import timezone

from apps.news.entities import RendererType
from apps.news.factories import ArticleFactory


def test_get_articles(db, api_client):
    now = timezone.now()

    future_article = ArticleFactory(date_published=now + timedelta(hours=1))  # noqa: F841
    plain_article = ArticleFactory(
        title="New master server patch is out",
        text='Download it <a href="http://example.com/">here</a>',
        signature="Kind regards, Serge.",
        date_published=now - timedelta(days=1),
        renderer=RendererType.PLAINTEXT,
    )
    markdown_article = ArticleFactory(
        title="New master server patch is out",
        text="Download it [here](http://example.com/)",
        date_published=now,
        renderer=RendererType.MARKDOWN,
    )
    html_article = ArticleFactory(
        date_published=now,
        title="New master server patch is out",
        text='Download it <a href="http://example.com/">here</a>',
        renderer=RendererType.HTML,
    )
    older_articles = ArticleFactory.create_batch(5, date_published=now - timedelta(days=7))

    response = api_client.get("/api/articles/")
    assert [obj["id"] for obj in response.data] == [
        markdown_article.pk,
        html_article.pk,
        plain_article.pk,
        older_articles[0].pk,
        older_articles[1].pk,
    ]

    md_article_obj = response.data[0]
    assert md_article_obj["title"] == "New master server patch is out"
    assert md_article_obj["html"] == '<p>Download it <a href="http://example.com/">here</a></p>'
    assert md_article_obj["signature"] == ""

    html_article_obj = response.data[1]
    assert html_article_obj["title"] == "New master server patch is out"
    assert html_article_obj["html"] == 'Download it <a href="http://example.com/">here</a>'
    assert html_article_obj["signature"] == ""

    plain_article_obj = response.data[2]
    assert plain_article_obj["title"] == "New master server patch is out"
    assert (
        plain_article_obj["html"]
        == "Download it &lt;a href=&quot;http://example.com/&quot;&gt;here&lt;/a&gt;"
    )
    assert plain_article_obj["signature"] == "Kind regards, Serge."
