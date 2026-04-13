"""Теги для URL сжатых изображений (store.views_image.image_fit)."""
from urllib.parse import urlencode

from django import template

register = template.Library()


@register.simple_tag(takes_context=False)
def media_fit_url(image_field, width=960, fmt="webp", q=None):
    """
    Возвращает URL ресайза для ImageField/FileField или пустую строку.
    fmt: webp | jpeg | png
    q: опционально качество (60–95) для image_fit — меньше байт на мобильном LCP.
    """
    if not image_field:
        return ""
    name = getattr(image_field, "name", None) or ""
    if not name:
        return ""
    try:
        from django.urls import reverse

        base = reverse("store:image_fit", kwargs={"rel_path": name})
    except Exception:
        try:
            return image_field.url
        except Exception:
            return ""
    params = {"w": int(width), "fmt": fmt}
    if q is not None:
        params["q"] = int(q)
    return f"{base}?{urlencode(params)}"


@register.simple_tag(takes_context=False)
def media_fit_srcset(image_field, widths, fmt="webp", q=None):
    """
    srcset для responsive: widths — строка "400,800,1200" или список.
    q: опционально одно качество для всех дескрипторов (LCP / единый профиль).
    """
    if not image_field:
        return ""
    name = getattr(image_field, "name", None) or ""
    if not name:
        return ""
    try:
        from django.urls import reverse

        base = reverse("store:image_fit", kwargs={"rel_path": name})
    except Exception:
        return ""
    if isinstance(widths, str):
        parts = [int(x.strip()) for x in widths.split(",") if x.strip()]
    else:
        parts = [int(x) for x in widths]
    items = []
    for w in parts:
        params = {"w": w, "fmt": fmt}
        if q is not None:
            params["q"] = int(q)
        items.append(f"{base}?{urlencode(params)} {w}w")
    return ", ".join(items)
