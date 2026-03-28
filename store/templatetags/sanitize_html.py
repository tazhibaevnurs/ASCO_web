import bleach
from django import template
from django.utils.safestring import mark_safe

register = template.Library()

# Белый список для контента из CKEditor (ужесточайте при необходимости).
_ALLOWED_TAGS = frozenset(
    [
        "p",
        "br",
        "strong",
        "b",
        "em",
        "i",
        "u",
        "s",
        "sub",
        "sup",
        "ul",
        "ol",
        "li",
        "a",
        "h1",
        "h2",
        "h3",
        "h4",
        "blockquote",
        "pre",
        "code",
        "img",
        "table",
        "thead",
        "tbody",
        "tr",
        "th",
        "td",
        "span",
        "div",
        "hr",
    ]
)
_ALLOWED_ATTRS = {
    "a": ["href", "title", "target", "rel", "name", "class"],
    "img": ["src", "alt", "title", "width", "height", "class"],
    "td": ["colspan", "rowspan", "class"],
    "th": ["colspan", "rowspan", "class"],
    "p": ["class"],
    "span": ["class"],
    "div": ["class"],
    "table": ["class"],
}


@register.filter(name="sanitize_html")
def sanitize_html(value):
    if not value:
        return ""
    clean = bleach.clean(
        str(value),
        tags=_ALLOWED_TAGS,
        attributes=_ALLOWED_ATTRS,
        strip=True,
    )
    return mark_safe(clean)
