import logging

from django.contrib.auth.signals import user_logged_in, user_login_failed
from django.dispatch import receiver

from ecom_prj.structured_security import log_security_event

logger = logging.getLogger("asco.security")


def _ip(request):
    if not request:
        return None
    return request.META.get("REMOTE_ADDR")


@receiver(user_logged_in)
def log_successful_login(sender, request, user, **kwargs):
    log_security_event(
        logger,
        "auth_login_success",
        extra={
            "user_id": user.pk,
            "email": getattr(user, "email", "")[:254],
            "ip": _ip(request),
        },
    )


@receiver(user_login_failed)
def log_failed_login(sender, credentials, request, **kwargs):
    ident = ""
    if isinstance(credentials, dict):
        ident = (credentials.get("username") or credentials.get("email") or "")[:254]
    log_security_event(
        logger,
        "auth_login_failed",
        level=logging.WARNING,
        extra={"identifier": ident, "ip": _ip(request)},
    )
