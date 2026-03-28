"""
Дополнительные security-заголовки: CSP (опционально), Permissions-Policy, Referrer-Policy.
X-Frame-Options и X-Content-Type-Options задаются Django (см. settings).
"""
from __future__ import annotations

from typing import Callable

from django.conf import settings


class ExtraSecurityHeadersMiddleware:
    def __init__(self, get_response: Callable):
        self.get_response = get_response

    def __call__(self, request):
        response = self.get_response(request)
        # Referrer-Policy (если не задан Django SecurityMiddleware в вашей версии — дублирование безопасно)
        rp = getattr(settings, "SECURE_REFERRER_POLICY", None)
        if rp and "Referrer-Policy" not in response:
            response["Referrer-Policy"] = rp

        pp = getattr(settings, "PERMISSIONS_POLICY", None)
        if pp and "Permissions-Policy" not in response:
            response["Permissions-Policy"] = pp

        csp = getattr(settings, "SECURE_CONTENT_SECURITY_POLICY", None)
        if csp:
            report_only = getattr(
                settings, "SECURE_CONTENT_SECURITY_POLICY_REPORT_ONLY", False
            )
            header = (
                "Content-Security-Policy-Report-Only"
                if report_only
                else "Content-Security-Policy"
            )
            if header not in response and "Content-Security-Policy" not in response:
                response[header] = csp

        return response
