"""
Проверки конфигурации деплоя (manage.py check --deploy).
"""
import ipaddress
import socket
from django.conf import settings
from django.core.checks import Warning, register


def _db_host() -> str:
    return str(settings.DATABASES.get("default", {}).get("HOST") or "")


def _resolve_maybe_ip(host: str):
    if not host:
        return None
    try:
        return ipaddress.ip_address(host)
    except ValueError:
        try:
            infos = socket.getaddrinfo(host, None, type=socket.SOCK_STREAM)
            for info in infos:
                addr = info[4][0]
                try:
                    return ipaddress.ip_address(addr)
                except ValueError:
                    continue
        except OSError:
            return None
    return None


@register(deploy=True)
def check_database_host_not_publicly_routable(app_configs, **kwargs):
    """
    Предупреждение, если хост БД выглядит как глобальный IPv4/IPv6 (часто значит открытый доступ в интернет).
    Отключите: DATABASE_ALLOW_PUBLIC_HOST=true (осознанно).
    """
    if getattr(settings, "DEBUG", True):
        return []
    if settings.DATABASES.get("default", {}).get("ENGINE", "").endswith("sqlite3"):
        return []
    if getattr(settings, "DATABASE_ALLOW_PUBLIC_HOST", False):
        return []

    host = _db_host()
    if not host or host in ("localhost", "127.0.0.1", "::1"):
        return []

    ip = _resolve_maybe_ip(host)
    if ip is not None and ip.is_global:
        return [
            Warning(
                f"База данных указывает на глобальный адрес {host}. "
                "Рекомендуется private network / VPC и отсутствие публичного порта PostgreSQL.",
                id="asco.security.W001",
            )
        ]
    return []


@register(deploy=True)
def check_cors_origins_in_production(app_configs, **kwargs):
    """В production не используйте CORS wildcard."""
    if getattr(settings, "DEBUG", True):
        return []
    if getattr(settings, "CORS_ALLOW_ALL_ORIGINS", False):
        return [
            Warning(
                "CORS_ALLOW_ALL_ORIGINS=True небезопасно в production.",
                id="asco.security.W002",
            )
        ]
    return []
