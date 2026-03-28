"""
Идемпотентное завершение оплаты Stripe Checkout (браузерный return и вебхук).
"""
from __future__ import annotations

import logging
from decimal import Decimal
from typing import Literal, Optional

from django.conf import settings
from django.db import transaction
from django.template.loader import render_to_string
from django.core.mail import EmailMultiAlternatives

import stripe

from customer import models as customer_models
from store import models as store_models
from store.cart_utils import clear_cart_items

logger = logging.getLogger(__name__)

FulfillResult = Literal["fulfilled", "already_fulfilled", "failed"]


def _send_order_paid_emails(order: store_models.Order) -> None:
    customer_merge_data = {
        "order": order,
        "order_items": order.order_items(),
    }
    subject = "New Order!"
    text_body = render_to_string(
        "email/order/customer/customer_new_order.txt", customer_merge_data
    )
    html_body = render_to_string(
        "email/order/customer/customer_new_order.html", customer_merge_data
    )
    msg = EmailMultiAlternatives(
        subject=subject,
        from_email=settings.FROM_EMAIL,
        to=[order.address.email],
        body=text_body,
    )
    msg.attach_alternative(html_body, "text/html")
    msg.send()

    for item in order.order_items():
        vendor_merge_data = {"item": item}
        text_b = render_to_string(
            "email/order/vendor/vendor_new_order.txt", vendor_merge_data
        )
        html_b = render_to_string(
            "email/order/vendor/vendor_new_order.html", vendor_merge_data
        )
        msg_v = EmailMultiAlternatives(
            subject=subject,
            from_email=settings.FROM_EMAIL,
            to=[item.vendor.email],
            body=text_b,
        )
        msg_v.attach_alternative(html_b, "text/html")
        msg_v.send()


def try_fulfill_stripe_checkout_session(
    *,
    order_pk: int,
    session_id: str,
    request=None,
    clear_cart: bool = False,
) -> FulfillResult:
    """
    Проверяет Session Stripe и при успехе один раз переводит заказ в Paid (select_for_update).
    """
    stripe.api_key = settings.STRIPE_SECRET_KEY
    if not stripe.api_key:
        logger.error("STRIPE_SECRET_KEY не задан")
        return "failed"

    try:
        session = stripe.checkout.Session.retrieve(session_id)
    except Exception as exc:
        logger.warning("Stripe Session.retrieve failed: %s", exc)
        return "failed"

    meta_oid = (session.metadata or {}).get("order_id")
    meta_pk = (session.metadata or {}).get("order_pk")

    if meta_pk and str(order_pk) != str(meta_pk):
        return "failed"
    if not meta_oid:
        return "failed"

    outcome: FulfillResult = "failed"

    try:
        with transaction.atomic():
            order = store_models.Order.objects.select_for_update().get(pk=order_pk)
            if meta_oid != str(order.order_id):
                return "failed"

            expected_cents = int((order.total * Decimal("100")).quantize(Decimal("1")))
            if (
                session.amount_total is not None
                and int(session.amount_total) != expected_cents
            ):
                return "failed"

            if session.payment_status != "paid":
                return "failed"

            if order.payment_status != "Processing":
                outcome = "already_fulfilled"
            else:
                order.payment_status = "Paid"
                order.payment_method = order.payment_method or "Stripe"
                order.save(update_fields=["payment_status", "payment_method"])
                outcome = "fulfilled"
    except store_models.Order.DoesNotExist:
        return "failed"

    if outcome == "fulfilled":
        if clear_cart and request is not None:
            clear_cart_items(request)
        customer_models.Notifications.objects.create(
            type="New Order",
            user=order.customer if order.customer_id else None,
        )
        try:
            _send_order_paid_emails(order)
        except Exception as exc:
            logger.exception("Order paid emails failed: %s", exc)

    return outcome
