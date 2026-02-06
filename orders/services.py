"""
Сервис отправки уведомлений о заказах в Telegram.
Использует requests для POST к Telegram Bot API.
"""
import logging
import requests
from django.conf import settings

logger = logging.getLogger(__name__)

# Заказы, для которых отправка идёт из view (delivery_request), а не из сигнала — чтобы не дублировать
TELEGRAM_SKIP_ORDER_IDS = set()


def send_order_to_telegram(order_id):
    """
    Формирует текстовое сообщение о заказе и отправляет его в Telegram.
    Принимает ID заказа (pk), извлекает Order и OrderItems.
    Ошибки перехватываются, чтобы сбой интернета не ломал оформление заказа.
    """
    token = (getattr(settings, "TELEGRAM_BOT_TOKEN", None) or "").strip()
    chat_id = str(getattr(settings, "TELEGRAM_CHAT_ID", None) or "").strip()
    if not token or not chat_id:
        logger.warning("TELEGRAM_BOT_TOKEN or TELEGRAM_CHAT_ID not set; skip sending order to Telegram")
        print("[Telegram] ОТКЛЮЧЕНО: в .env нет TELEGRAM_BOT_TOKEN или TELEGRAM_CHAT_ID")
        return

    try:
        from store.models import Order
        order = Order.objects.select_related("address").get(pk=order_id)
    except Exception as e:
        logger.exception("Failed to load order pk=%s for Telegram: %s", order_id, e)
        print("[Telegram] Ошибка загрузки заказа:", e)
        return

    items_qs = order.order_items().select_related("product")
    items_lines = []
    for item in items_qs:
        # Название x Кол-во - Цена (сумма по позиции можно item.sub_total)
        line = f"• {item.product.name} x {item.qty} — {item.sub_total} сом"
        items_lines.append(line)

    # Не отправлять сообщение без товаров — только одно сообщение с полным составом
    if not items_lines:
        logger.info("Order pk=%s has no items; skip Telegram (will send from view after items created)", order_id)
        return

    items_text = "\n".join(items_lines)

    name = "—"
    phone = "—"
    address_line = "—"
    if order.address:
        name = order.address.full_name or "—"
        phone = order.address.mobile or "—"
        city = getattr(order.address, "city", None) or ""
        addr = getattr(order.address, "address", None) or ""
        address_line = f"{city}, {addr}".strip(", ") or "—"

    message = (
        f"📦 Новый заказ №{order.order_id}\n\n"
        f"👤 Клиент: {name} | {phone}\n\n"
        f"🏠 Адрес: {address_line}\n\n"
        f"🛒 Товары:\n{items_text}\n\n"
        f"💰 Итого: {order.total} сом."
    )

    url = f"https://api.telegram.org/bot{token}/sendMessage"
    payload = {
        "chat_id": chat_id,
        "text": message,
        "disable_web_page_preview": True,
    }

    try:
        resp = requests.post(url, json=payload, timeout=10)
        resp.raise_for_status()
        logger.info("Order %s sent to Telegram successfully", order.order_id)
        print("[Telegram] Отправлено: заказ №%s в группу" % order.order_id)
    except requests.RequestException as e:
        logger.warning("Telegram send failed for order pk=%s: %s", order_id, e)
        print("[Telegram] Ошибка отправки:", e)
        if hasattr(e, "response") and e.response is not None:
            try:
                print("[Telegram] Ответ API:", e.response.text[:200])
            except Exception:
                pass
