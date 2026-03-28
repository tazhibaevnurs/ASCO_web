"""
Аудит ответов (4xx/5xx), подсчёт 401/403 и аномально высокого трафика с одного IP (кэш).
"""
from __future__ import annotations

import logging
from typing import Callable

from django.conf import settings
from django.core.cache import caches

from ecom_prj.structured_security import log_security_event

logger = logging.getLogger("asco.security")


def _client_ip(request) -> str:
    meta = getattr(settings, "RATELIMIT_IP_META_KEY", None)
    if meta and isinstance(meta, str) and meta in request.META:
        return request.META.get(meta) or ""
    return request.META.get("REMOTE_ADDR") or "unknown"


class SecurityAuditMiddleware:
    """Логирование подозрительной активности и ошибок API/сайта."""

    def __init__(self, get_response: Callable):
        self.get_response = get_response
        self.denied_threshold = int(
            getattr(settings, "SECURITY_DENIED_PER_IP_THRESHOLD", 30)
        )
        self.denied_window = int(
            getattr(settings, "SECURITY_DENIED_WINDOW_SEC", 300)
        )
        self.rpm_anomaly = int(
            getattr(settings, "SECURITY_REQUESTS_PER_MINUTE_ANOMALY", 500)
        )
        cache_name = getattr(settings, "RATELIMIT_USE_CACHE", "default")
        self.cache = caches[cache_name]

    def __call__(self, request):
        response = self.get_response(request)
        self._audit(request, response)
        return response

    def _audit(self, request, response) -> None:
        if getattr(settings, "DISABLE_SECURITY_AUDIT_MIDDLEWARE", False):
            return

        status = getattr(response, "status_code", 0)
        path = request.path
        ip = _client_ip(request)
        user_id = (
            request.user.pk
            if getattr(request, "user", None) and request.user.is_authenticated
            else None
        )

        # 5xx — всегда; 4xx — без массового шума от 404 на несуществующих URL (сканеры).
        if status >= 500 or (
            400 <= status < 500
            and (status != 404 or path.startswith(("/api/", "/webhooks/", "/admin/")))
        ):
            level = logging.WARNING if 400 <= status < 500 else logging.ERROR
            log_security_event(
                logger,
                "http_error_response",
                level=level,
                extra={
                    "status": status,
                    "path": path[:2048],
                    "method": request.method,
                    "ip": ip,
                    "user_id": user_id,
                },
            )

        # Подозрительная активность: много 401/403 с одного IP
        if status in (401, 403):
            key = f"sec:denied:{ip}"
            try:
                n = self.cache.incr(key)
            except ValueError:
                self.cache.add(key, 1, timeout=self.denied_window)
                n = 1
            if n == self.denied_threshold:
                log_security_event(
                    logger,
                    "suspicious_auth_failures_burst",
                    level=logging.WARNING,
                    extra={
                        "ip": ip,
                        "count": n,
                        "window_sec": self.denied_window,
                        "path": path[:512],
                    },
                )

        # Аномалия: много запросов в минуту с одного IP (грубый индикатор DDoS/сканера)
        if request.method in ("GET", "POST", "PUT", "PATCH", "DELETE", "HEAD"):
            from django.utils import timezone

            bucket = int(timezone.now().timestamp()) // 60
            rk = f"sec:rpm:{ip}:{bucket}"
            try:
                c = self.cache.incr(rk)
            except ValueError:
                self.cache.add(rk, 1, timeout=120)
                c = 1
            if c == self.rpm_anomaly:
                log_security_event(
                    logger,
                    "traffic_anomaly_high_rpm",
                    level=logging.WARNING,
                    extra={"ip": ip, "requests_per_minute": c, "sample_path": path[:256]},
                )
