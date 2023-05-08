import pytest
from django.utils.safestring import SafeText, SafeData

from apps.news.entities import RendererType
from apps.news.models import Article


class TestArticle:
    html_text = (
        ('<script>alert()</script>', '&lt;script&gt;alert()&lt;/script&gt;'),
        ("""<a href="javascript:document.location='http://www.google.com/'">xss</a>""",
         '<a>xss</a>'),
        ('<a href="https://example.org/" onclick=alert(1)>xss</a>',
         '<a href="https://example.org/">xss</a>'),
        ("""<img src="javascript:alert('XSS');">""", '<img>'),
        ('<p>foo</p>', '<p>foo</p>'),
        ('<b>foo</b>', '<b>foo</b>'),
        ('<a href="https://www.youtube.com/">foo</a>', '<a href="https://www.youtube.com/">foo</a>'),
        ('<iframe width="560" height="315" src="https://www.youtube.com/" frameborder="0" allowfullscreen></iframe>',
         '<iframe width="560" height="315" src="https://www.youtube.com/" frameborder="0" allowfullscreen=""></iframe>'),  # noqa
        ('<img src="http://example.org/picture.png" />', '<img src="http://example.org/picture.png">'),
    )
    markdown_text = (
        ('* foo', '<ul>\n<li>foo</li>\n</ul>'),
        ('* <b>foo</b>', '<ul>\n<li>&lt;b&gt;foo&lt;/b&gt;</li>\n</ul>'),
    )

    def test_html_renderer(self):
        text = '<b>Foo!</b>'
        article = Article(text=text, renderer=RendererType.HTML)
        assert article.rendered == text
        assert isinstance(article.rendered, SafeText)
        assert isinstance(article.rendered, SafeData)

    def test_plaintext_renderer(self):
        text = '<b>Foo!</b>'
        article = Article(text=text, renderer=RendererType.PLAINTEXT)
        assert article.rendered == text
        assert not isinstance(article.rendered, SafeData)

    def test_markdown_renderer(self):
        text = '* foo'
        article = Article(text=text, renderer=RendererType.MARKDOWN)
        assert article.rendered == '<ul>\n<li>foo</li>\n</ul>'
        assert isinstance(article.rendered, SafeText)

    def test_default_renderer_is_markdown(self, db):
        article = Article.objects.create(text='foo')
        assert Article.objects.get(pk=article.pk).renderer == RendererType.MARKDOWN

    def test_default_renderer_for_invalid_values_is_markdown(self, db):
        article = Article.objects.create(text='foo', renderer=9999)
        assert Article.objects.get(pk=article.pk).rendered == '<p>foo</p>'

    @pytest.mark.parametrize('raw_text, expected_html', html_text)
    def test_html_text(self, raw_text, expected_html):
        article = Article(text=raw_text, renderer=RendererType.HTML)
        assert article.rendered == expected_html

    @pytest.mark.parametrize('raw_text, expected_html', markdown_text)
    def test_markdown_text(self, raw_text, expected_html):
        article = Article(text=raw_text, renderer=RendererType.MARKDOWN)
        assert article.rendered == expected_html
