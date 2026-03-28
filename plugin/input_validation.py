"""
Серверная валидация пользовательского ввода (аналог строгих схем вроде Zod).
Django ORM всегда использует параметризованные запросы — сырой конкатенации SQL нет.
"""

from __future__ import annotations

import os
from decimal import Decimal, InvalidOperation
from typing import Any, Sequence

# --- Текст / поиск ---

MAX_SEARCH_QUERY_LEN = 200
MAX_SLUG_LEN = 200
MAX_CART_COLOR_SIZE_LEN = 120
MAX_CONTACT_FIELD = 500
MAX_COMMENT_LEN = 5000
MAX_WISHLIST_SYNC_IDS = 200
MAX_CATEGORY_FILTER_IDS = 50
MAX_PRODUCT_QTY = 9_999
MAX_DECIMAL_PRICE = Decimal("99999999.99")


def clamp_text(value: str | None, max_len: int) -> str:
    if not value:
        return ""
    s = str(value).strip()
    return s[:max_len] if len(s) > max_len else s


def parse_search_q(raw: str | None) -> str:
    return clamp_text(raw, MAX_SEARCH_QUERY_LEN)


def parse_category_slug(raw: str | None) -> str | None:
    if not raw:
        return None
    s = str(raw).strip()[:MAX_SLUG_LEN]
    if not s:
        return None
    for ch in s:
        if not (ch.isalnum() or ch in "-_"):
            return None
    return s


def parse_rating_list(raw_list: list[Any], *, max_items: int = 5) -> list[str]:
    allowed = frozenset({"1", "2", "3", "4", "5"})
    out: list[str] = []
    for x in raw_list[:max_items]:
        s = str(x).strip()
        if s in allowed:
            out.append(s)
    return out


def parse_filter_tokens(
    raw_list: list[Any], *, max_items: int = 40, max_token_len: int = 120
) -> list[str]:
    out: list[str] = []
    for x in raw_list[:max_items]:
        s = str(x).strip()[:max_token_len]
        if s:
            out.append(s)
    return out


def parse_int_id_list(
    raw_list: Sequence[Any], *, max_items: int = MAX_CATEGORY_FILTER_IDS
) -> list[int]:
    out: list[int] = []
    for x in raw_list[:max_items]:
        try:
            v = int(str(x).strip())
        except (TypeError, ValueError):
            continue
        if v > 0:
            out.append(v)
    return out


def parse_bounded_decimal(
    raw: str | None,
    *,
    min_val: Decimal = Decimal("0"),
    max_val: Decimal = MAX_DECIMAL_PRICE,
) -> Decimal | None:
    if raw is None or str(raw).strip() == "":
        return None
    try:
        d = Decimal(str(raw).strip())
    except (InvalidOperation, TypeError, ValueError):
        return None
    if d < min_val or d > max_val:
        return None
    return d


ALLOWED_SHOP_SORT = frozenset(
    {"price_asc", "price_desc", "newest", "name", "", "lowest", "highest"}
)


def parse_shop_sort(sort: str | None, prices: str | None) -> tuple[str, str | None]:
    """Возвращает (sort_key, prices_legacy) только из белого списка."""
    s = (sort or "").strip()
    if s in ("price_asc", "price_desc", "newest", "name", ""):
        return s, None
    p = (prices or "").strip()
    if p in ("lowest", "highest"):
        return "", p
    return "", None


def parse_positive_int(raw: str | None, *, default: int | None = None, max_val: int = 2_147_483_647) -> int | None:
    if raw is None or str(raw).strip() == "":
        return default
    try:
        v = int(str(raw).strip())
    except (TypeError, ValueError):
        return default
    if v < 1 or v > max_val:
        return default
    return v


def parse_product_qty(raw: str | None) -> int | None:
    return parse_positive_int(raw, default=None, max_val=MAX_PRODUCT_QTY)


# --- Загрузка файлов ---

ALLOWED_IMAGE_EXTENSIONS = frozenset({".jpg", ".jpeg", ".png", ".gif", ".webp"})
# Часть браузеров отдаёт загрузки как application/octet-stream — расширение уже ограничено.
ALLOWED_IMAGE_CONTENT_TYPES = frozenset(
    {
        "image/jpeg",
        "image/png",
        "image/gif",
        "image/webp",
        "application/octet-stream",
    }
)
DEFAULT_MAX_IMAGE_BYTES = 5 * 1024 * 1024  # 5 MiB


def validate_uploaded_image(
    f,
    *,
    max_bytes: int = DEFAULT_MAX_IMAGE_BYTES,
    field_name: str = "Файл",
) -> str | None:
    """
    Возвращает None если ок, иначе строку ошибки для пользователя.
    """
    if f is None:
        return None
    size = getattr(f, "size", None)
    if size is not None and size > max_bytes:
        return f"{field_name}: размер не более {max_bytes // (1024 * 1024)} МБ."

    name = getattr(f, "name", "") or ""
    ext = os.path.splitext(name)[1].lower()
    if ext and ext not in ALLOWED_IMAGE_EXTENSIONS:
        return f"{field_name}: допустимы только изображения ({', '.join(sorted(ALLOWED_IMAGE_EXTENSIONS))})."

    ct = (getattr(f, "content_type", None) or "").split(";")[0].strip().lower()
    if ct and ct not in ALLOWED_IMAGE_CONTENT_TYPES:
        return f"{field_name}: недопустимый тип файла."

    return None
