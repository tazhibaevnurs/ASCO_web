"""Дневной лимит «AI»-запросов по плану подписки (кэш Django, Redis/LocMem)."""
from __future__ import annotations

from typing import Tuple

from django.conf import settings
from django.core.cache import cache
from django.utils import timezone


def _daily_key(user_id: int) -> str:
    day = timezone.now().date().isoformat()
    return f"ai_gen:{user_id}:{day}"


def get_ai_daily_limit_for_user(user) -> int:
    tier = "free"
    try:
        profile = user.profile
        tier = (profile.subscription_plan or "free").lower()
    except Exception:
        pass
    if tier == "pro":
        return int(getattr(settings, "AI_GENERATION_LIMIT_PRO_PER_DAY", 50))
    return int(getattr(settings, "AI_GENERATION_LIMIT_FREE_PER_DAY", 5))


def try_consume_ai_generation(user) -> Tuple[bool, str]:
    """
    Атомарно увеличивает счётчик за сутки. Возвращает (True, '') или (False, сообщение).
    """
    limit = get_ai_daily_limit_for_user(user)
    key = _daily_key(user.pk)
    ttl = int(getattr(settings, "AI_QUOTA_CACHE_TTL", 86400))
    try:
        n = cache.incr(key)
    except ValueError:
        cache.add(key, 0, timeout=ttl)
        n = cache.incr(key)
    if n > limit:
        try:
            cache.decr(key)
        except ValueError:
            pass
        return False, f"Дневной лимит генераций исчерпан ({limit} для вашего плана)."
    return True, ""


def release_ai_generation_slot(user) -> None:
    """Откат счётчика при ошибке после списания (сеть, LLM). Не уходит ниже 0."""
    key = _daily_key(user.pk)
    try:
        cache.decr(key)
    except ValueError:
        pass
