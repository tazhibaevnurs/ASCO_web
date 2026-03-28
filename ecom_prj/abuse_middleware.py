"""
Лимиты злоупотреблений: размер тела запроса для «API»-путей и частота запросов (django-ratelimit + кэш).
"""
import re

from django.conf import settings
from django.http import JsonResponse
from django_ratelimit import ALL
from django_ratelimit.core import is_ratelimited


def _path_matches_api_rate_limit(path: str) -> bool:
    path = path or "/"
    if not path.endswith("/"):
        path = path + "/"
    for prefix in getattr(settings, "API_RATE_LIMIT_PATH_PREFIXES", ()):
        p = prefix if prefix.endswith("/") else prefix + "/"
        if path.startswith(p):
            return True
    for pattern in getattr(settings, "API_RATE_LIMIT_PATH_REGEXES", ()):
        if re.match(pattern, path):
            return True
    return False


def _path_matches_api_body_limit(path: str) -> bool:
    """Те же правила + /api/ всегда."""
    if path.startswith("/api/") or path.startswith("/api"):
        return True
    return _path_matches_api_rate_limit(path)


class ApiRequestBodySizeLimitMiddleware:
    """Для перечисленных путей: макс. 1 МБ по Content-Length (до чтения тела)."""

    def __init__(self, get_response):
        self.get_response = get_response
        self.max_bytes = int(
            getattr(settings, "API_MAX_REQUEST_BODY_BYTES", 1024 * 1024)
        )

    def __call__(self, request):
        if not _path_matches_api_body_limit(request.path):
            return self.get_response(request)
        raw = request.META.get("CONTENT_LENGTH")
        if not raw:
            return self.get_response(request)
        try:
            size = int(raw)
        except ValueError:
            return JsonResponse({"error": "Invalid Content-Length"}, status=400)
        if size > self.max_bytes:
            return JsonResponse(
                {"error": "Payload too large", "max_bytes": self.max_bytes},
                status=413,
            )
        return self.get_response(request)


class ApiUserRateLimitMiddleware:
    """До 100 запросов в минуту на пользователя (или IP для анонимов) для API-путей."""

    def __init__(self, get_response):
        self.get_response = get_response
        self.rate = getattr(settings, "API_RATE_LIMIT", "100/m")

    def __call__(self, request):
        if not _path_matches_api_rate_limit(request.path):
            return self.get_response(request)
        limited = is_ratelimited(
            request,
            group="api_endpoints",
            key="user_or_ip",
            rate=self.rate,
            method=ALL,
            increment=True,
        )
        if limited:
            return JsonResponse(
                {"error": "Too many requests", "retry_after": 60},
                status=429,
                headers={"Retry-After": "60"},
            )
        return self.get_response(request)
