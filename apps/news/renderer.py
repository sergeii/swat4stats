import bleach
import markdown
from django.utils.html import escape
from django.utils.safestring import mark_safe


class PlainRenderer:

    @classmethod
    def render(cls, value):
        return value


class HtmlRenderer:
    ALLOWED_TAGS = [
        'a', 'abbr', 'acronym',
        'b', 'blockquote',
        'code', 'em', 'i', 'li', 'ol',
        'strong', 'ul', 'img', 'iframe',
        'p', 'div', 'pre',
    ]

    ALLOWED_ATTRIBUTES = {
        'a': ['href', 'title'],
        'abbr': ['title'],
        'acronym': ['title'],
        'img': ['src', 'title'],
        'iframe': ['src', 'title', 'width', 'height', 'frameborder', 'allowfullscreen'],
    }

    @classmethod
    def render(cls, value):
        value = bleach.clean(value,
                             tags=cls.ALLOWED_TAGS,
                             attributes=cls.ALLOWED_ATTRIBUTES)
        return mark_safe(value)


class MarkdownRenderer(HtmlRenderer):

    @classmethod
    def render(cls, value):
        md_html = markdown.markdown(escape(value))
        return super().render(md_html)
