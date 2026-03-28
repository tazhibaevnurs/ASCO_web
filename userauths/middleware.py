from django.conf import settings
from django.contrib.auth.views import redirect_to_login


def _path_allowed_without_auth(path):
    """Guest-accessible URLs under /customer/ (wishlist for anonymous users)."""
    if not path.startswith("/customer/"):
        return False
    if path.startswith("/customer/sync_wishlist_from_storage"):
        return True
    if "/add_to_wishlist/" in path:
        return True
    if "/toggle_wishlist/" in path:
        return True
    return False


def _store_path_requires_login(path):
    """Оформление заказа и оплата — только для авторизованных (дублирует @login_required)."""
    if path.startswith("/create_order"):
        return True
    if path.startswith("/checkout/"):
        return True
    if path.startswith("/coupon_apply/"):
        return True
    if path.startswith("/payment_status/"):
        return True
    if path.startswith("/stripe_payment"):
        return True
    if path.startswith("/paypal_payment_verify/"):
        return True
    if path.startswith("/razorpay_payment_verify/"):
        return True
    if path.startswith("/paystack_payment_verify/"):
        return True
    if path.startswith("/flutterwave_payment_callback/"):
        return True
    return False


class RequireLoginForAppPrefixesMiddleware:
    """
    Defense in depth: require an authenticated session for /customer/* and /vendor/*
    except explicitly public customer wishlist endpoints; same for checkout/payment under /.
    """

    PROTECTED_PREFIXES = ("/customer/", "/vendor/")

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        path = request.path

        if _store_path_requires_login(path) and not request.user.is_authenticated:
            return redirect_to_login(
                next=request.get_full_path(),
                login_url=settings.LOGIN_URL,
            )

        if any(path.startswith(p) for p in self.PROTECTED_PREFIXES):
            if path.startswith("/customer/") and _path_allowed_without_auth(path):
                return self.get_response(request)

            if not request.user.is_authenticated:
                return redirect_to_login(
                    next=request.get_full_path(),
                    login_url=settings.LOGIN_URL,
                )

        return self.get_response(request)
