from typing import ClassVar

import bleach
import markdown
from django.utils.html import escape
from django.utils.safestring import mark_safe


class BaseRenderer:
    @classmethod
    def render(cls, value: str) -> str:
        raise NotImplementedError


class PlainRenderer(BaseRenderer):
    @classmethod
    def render(cls, value: str) -> str:
        return value


class HtmlRenderer(BaseRenderer):
    ALLOWED_TAGS: ClassVar[list[str]] = [
        "a",
        "abbr",
        "acronym",
        "b",
        "blockquote",
        "code",
        "em",
        "i",
        "li",
        "ol",
        "strong",
        "ul",
        "img",
        "iframe",
        "p",
        "div",
        "pre",
    ]

    ALLOWED_ATTRIBUTES: ClassVar[dict[str, list[str]]] = {
        "a": ["href", "title"],
        "abbr": ["title"],
        "acronym": ["title"],
        "img": ["src", "title"],
        "iframe": ["src", "title", "width", "height", "frameborder", "allowfullscreen"],
    }

    @classmethod
    def render(cls, value: str) -> str:
        value = bleach.clean(value, tags=cls.ALLOWED_TAGS, attributes=cls.ALLOWED_ATTRIBUTES)
        return mark_safe(value)


class MarkdownRenderer(HtmlRenderer):
    @classmethod
    def render(cls, value: str) -> str:
        md_html = markdown.markdown(escape(value))
        return super().render(md_html)
