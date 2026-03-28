from django.conf import settings
from django.http import HttpResponseRedirect
from django.shortcuts import redirect
from django.urls import NoReverseMatch, reverse
from django.utils.http import url_has_allowed_host_and_scheme


def redirect_after_login(request, next_url, fallback="store:index"):
    """
    Avoid open redirects: reject scheme-relative URLs (//evil.com), external hosts,
    and control characters. Allow relative same-site paths or a named URL route.
    """
    if not next_url or next_url in ("undefined", "/undefined/"):
        return redirect(fallback)

    if isinstance(next_url, str) and next_url.startswith("/"):
        if (
            next_url.startswith("//")
            or "\n" in next_url
            or "\r" in next_url
            or "\x00" in next_url
        ):
            return redirect(fallback)
        full = request.build_absolute_uri(next_url)
        hosts = settings.ALLOWED_HOSTS
        if not hosts or "*" in hosts:
            allowed_hosts = {request.get_host()}
        else:
            allowed_hosts = set(hosts)
        if url_has_allowed_host_and_scheme(
            url=full,
            allowed_hosts=allowed_hosts,
            allowed_schemes=("http", "https"),
            require_https=request.is_secure(),
        ):
            return HttpResponseRedirect(next_url)
        return redirect(fallback)

    # Имя маршрута Django (например store:index). Нельзя делать redirect(next_url) со строкой —
    # иначе next=https://evil.com уходит в open redirect через HttpResponseRedirect.
    if not isinstance(next_url, str):
        return redirect(fallback)
    name = next_url.strip()
    try:
        return redirect(reverse(name))
    except NoReverseMatch:
        return redirect(fallback)
