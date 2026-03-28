"""Утилиты корзины (без циклических импортов с views)."""

from store import models as store_models


def clear_cart_items(request):
    try:
        cart_id = request.session["cart_id"]
        store_models.Cart.objects.filter(cart_id=cart_id).delete()
    except Exception:
        pass
