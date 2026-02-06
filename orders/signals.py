"""
Сигналы для уведомлений о заказах (например, отправка в Telegram).
"""
from django.db import transaction
from django.db.models.signals import post_save
from django.dispatch import receiver

from store.models import Order


@receiver(post_save, sender=Order)
def on_order_created(sender, instance, created, **kwargs):
    if not created:
        return
    order_pk = instance.id
    try:
        from orders.services import send_order_to_telegram
        # Отправляем после коммита транзакции, чтобы в заказе уже были все OrderItem
        transaction.on_commit(lambda: _safe_send_order_to_telegram(order_pk))
    except Exception:
        pass


def _safe_send_order_to_telegram(order_pk):
    try:
        from orders.services import send_order_to_telegram, TELEGRAM_SKIP_ORDER_IDS
        # Заказ в один клик отправляем из delivery_request после создания позиций — здесь не дублируем
        if order_pk in TELEGRAM_SKIP_ORDER_IDS:
            TELEGRAM_SKIP_ORDER_IDS.discard(order_pk)
            return
        send_order_to_telegram(order_pk)
    except Exception:
        pass  # не ломаем оформление заказа при сбое Telegram

