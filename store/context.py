from store import models as store_models
from customer import models as customer_models
from decimal import Decimal
from django.db.models import Sum

WISHLIST_SESSION_KEY = "wishlist_product_ids"

# Страницы без slick/ion/smoothproducts — главная, блог, статика, ЛК (PageSpeed: −сотни KiB JS на первом экране).
_NO_THEME_JQUERY_PREFIXES = (
    "/blog/",
    "/about/",
    "/contact/",
    "/faqs/",
    "/privacy_policy/",
    "/terms_conditions/",
    "/delivery_request/",
    "/order_tracker",
    "/customer/",
    "/vendor/",
    "/auth/",
    "/password-reset",
    "/admin/",
    "/api/",
)


def _load_theme_jquery_plugins(path: str) -> bool:
    p = path or "/"
    if p in ("/", ""):
        return False
    for prefix in _NO_THEME_JQUERY_PREFIXES:
        if p.startswith(prefix):
            return False
    return True


def default(request):
    category_ = store_models.Category.objects.all()
    total_cart_items = 0
    cart_items = []
    cart_sub_total = Decimal("0.00")
    try:
        cart_id = request.session["cart_id"]
        cart_qs = store_models.Cart.objects.filter(cart_id=cart_id).select_related("product")
        total_cart_items = cart_qs.count()
        cart_items = list(cart_qs[:5])
        sub = cart_qs.aggregate(s=Sum("sub_total"))["s"]
        cart_sub_total = sub or Decimal("0.00")
    except Exception:
        pass

    wishlist_count = 0
    wishlist_product_ids = set()
    if getattr(request, "user", None) and request.user.is_authenticated:
        wishlist_count = customer_models.Wishlist.objects.filter(user=request.user).count()
        wishlist_product_ids = set(
            customer_models.Wishlist.objects.filter(user=request.user).values_list("product_id", flat=True)
        )
    else:
        ids = request.session.get(WISHLIST_SESSION_KEY) or []
        try:
            wishlist_product_ids = set(int(x) for x in ids if x is not None)
        except (TypeError, ValueError):
            wishlist_product_ids = set()
        wishlist_count = len(wishlist_product_ids)

    return {
        "total_cart_items": total_cart_items,
        "cart_items": cart_items,
        "cart_sub_total": cart_sub_total,
        "wishlist_count": wishlist_count,
        "wishlist_product_ids": wishlist_product_ids,
        "category_": category_,
        "asco_load_theme_jquery_plugins": _load_theme_jquery_plugins(request.path),
    }