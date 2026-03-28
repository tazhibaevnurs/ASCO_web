"""
Проверка доступа к заказам (клиент и менеджер) для защиты от IDOR.
"""

from django.http import Http404
from django.shortcuts import get_object_or_404

from store import models as store_models

SESSION_ACCESSIBLE_ORDER_PKS = "accessible_order_pks"


def register_order_session_access(request, order_pk: int) -> None:
    """После создания заказа (в т.ч. гостевого) сохраняем pk в сессии для последующих шагов checkout."""
    pks = list(request.session.get(SESSION_ACCESSIBLE_ORDER_PKS, []))
    if order_pk not in pks:
        pks.append(order_pk)
    request.session[SESSION_ACCESSIBLE_ORDER_PKS] = pks
    request.session.modified = True


def customer_can_access_order(request, order: store_models.Order) -> bool:
    if order.customer_id:
        u = getattr(request, "user", None)
        return bool(u and u.is_authenticated and order.customer_id == u.pk)
    pks = request.session.get(SESSION_ACCESSIBLE_ORDER_PKS, [])
    return order.pk in pks


def get_order_for_customer(request, order_id: str) -> store_models.Order:
    order = get_object_or_404(store_models.Order, order_id=order_id)
    if not customer_can_access_order(request, order):
        raise Http404("Order not found")
    return order


def vendor_can_access_order(request, order: store_models.Order) -> bool:
    u = request.user
    if u.is_superuser or getattr(u, "role", None) == "superadmin":
        return True
    if order.vendors.filter(pk=u.pk).exists():
        return True
    return store_models.OrderItem.objects.filter(order=order, vendor=u).exists()


def get_order_for_vendor(request, order_id: str) -> store_models.Order:
    order = get_object_or_404(store_models.Order, order_id=order_id)
    if not vendor_can_access_order(request, order):
        raise Http404("Order not found")
    return order


def orders_queryset_for_vendor_user(user):
    """Заказы, которые менеджер имеет право видеть (свои вендорские позиции)."""
    if user.is_superuser or getattr(user, "role", None) == "superadmin":
        return store_models.Order.objects.all().order_by("-date")
    return (
        store_models.Order.objects.filter(vendors=user)
        .distinct()
        .order_by("-date")
    )
