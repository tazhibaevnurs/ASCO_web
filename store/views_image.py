"""
Сжатие и ресайз изображений из MEDIA для уменьшения LCP и трафика (PageSpeed).
Кэш на диске: MEDIA_ROOT/.cache/fit/
"""
from __future__ import annotations

import hashlib
import os
from io import BytesIO
from pathlib import Path

from django.conf import settings
from django.http import Http404, HttpResponse
from django.views.decorators.cache import cache_control
from django.views.decorators.http import require_GET

from PIL import Image, ImageOps


_ALLOWED_EXT = {".jpg", ".jpeg", ".png", ".webp", ".gif"}


def _safe_relpath(path: str) -> str:
    if not path or ".." in path or path.startswith(("/", "\\")):
        raise Http404()
    normalized = os.path.normpath(path.replace("\\", "/"))
    if normalized.startswith(".."):
        raise Http404()
    return normalized


def _cache_path(rel_path: str, w: int, q: int, fmt: str, webp_method: int | None = None) -> Path:
    key = f"{rel_path}|{w}|{q}|{fmt}"
    if fmt == "webp" and webp_method is not None:
        key += f"|wm{webp_method}"
    h = hashlib.sha256(key.encode("utf-8")).hexdigest()[:32]
    ext = ".webp" if fmt == "webp" else ".jpg" if fmt == "jpeg" else ".png"
    d = Path(settings.MEDIA_ROOT) / ".cache" / "fit"
    d.mkdir(parents=True, exist_ok=True)
    return d / f"{h}{ext}"


@require_GET
@cache_control(public=True, max_age=31536000, immutable=True)
def image_fit(request, rel_path: str):
    """
    GET ?w=800&q=82&fmt=webp|jpeg|png
    """
    rel_path = _safe_relpath(rel_path)
    full_path = Path(settings.MEDIA_ROOT) / rel_path
    if not full_path.is_file():
        raise Http404()

    ext = full_path.suffix.lower()
    if ext not in _ALLOWED_EXT:
        raise Http404()

    try:
        w = int(request.GET.get("w", "960"))
    except ValueError:
        w = 960
    w = max(200, min(w, 2560))

    # Меньше q для мелких ширин — меньше байт на карточках и мобильном LCP без явного ?q=
    if w <= 640:
        default_q = 74
    elif w <= 960:
        default_q = 78
    else:
        default_q = 82
    try:
        q = int(request.GET.get("q", str(default_q)))
    except ValueError:
        q = default_q
    q = max(60, min(q, 95))

    fmt = (request.GET.get("fmt") or "webp").lower()
    if fmt not in ("webp", "jpeg", "png"):
        fmt = "webp"

    webp_method = (4 if w <= 800 else 6) if fmt == "webp" else None
    cache_file = _cache_path(rel_path, w, q, fmt, webp_method)
    if cache_file.is_file():
        data = cache_file.read_bytes()
        return _response(data, fmt)

    with Image.open(full_path) as im:
        if getattr(im, "is_animated", False):
            im.seek(0)
        im = ImageOps.exif_transpose(im)
        if im.mode == "P":
            im = im.convert("RGBA")

        if im.width > w:
            new_h = max(1, int(im.height * (w / im.width)))
            im = im.resize((w, new_h), Image.Resampling.LANCZOS)

        buf = BytesIO()
        if fmt == "jpeg":
            if im.mode == "RGBA":
                bg = Image.new("RGB", im.size, (255, 255, 255))
                bg.paste(im, mask=im.split()[3])
                im = bg
            elif im.mode != "RGB":
                im = im.convert("RGB")
            im.save(buf, format="JPEG", quality=q, optimize=True)
        elif fmt == "png":
            if im.mode not in ("RGB", "RGBA"):
                im = im.convert("RGBA")
            im.save(buf, format="PNG", optimize=True)
        else:
            # webp: method 4 быстрее на CPU при холодном кэше (лучше TTFB/LCP), 6 — для крупных десктопных кадров
            if im.mode == "RGBA":
                im.save(buf, format="WEBP", quality=q, method=webp_method)
            else:
                im = im.convert("RGB") if im.mode != "RGB" else im
                im.save(buf, format="WEBP", quality=q, method=webp_method)

        data = buf.getvalue()

    try:
        cache_file.write_bytes(data)
    except OSError:
        pass

    return _response(data, fmt)


def _response(data: bytes, fmt: str) -> HttpResponse:
    ct = {
        "webp": "image/webp",
        "jpeg": "image/jpeg",
        "png": "image/png",
    }[fmt]
    resp = HttpResponse(data, content_type=ct)
    resp["Vary"] = "Accept"
    return resp
