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
    Возвращает True при успешной отправке, False иначе (удобно для логов на проде).
    """
    token = (getattr(settings, "TELEGRAM_BOT_TOKEN", None) or "").strip()
    raw_chat = getattr(settings, "TELEGRAM_CHAT_ID", None)
    if raw_chat is None or raw_chat == "":
        chat_id = ""
    elif isinstance(raw_chat, (int, float)):
        chat_id = str(int(raw_chat))
    else:
        chat_id = str(raw_chat).strip()
    if not token or not chat_id:
        logger.error(
            "Telegram: пропуск отправки заказа pk=%s — в окружении пусто TELEGRAM_BOT_TOKEN или TELEGRAM_CHAT_ID "
            "(проверьте .env у контейнера web на сервере).",
            order_id,
        )
        return False

    try:
        from store.models import Order
        order = Order.objects.select_related("address").get(pk=order_id)
    except Exception as e:
        logger.exception("Failed to load order pk=%s for Telegram: %s", order_id, e)
        return False

    items_qs = order.order_items().select_related("product")
    items_lines = []
    for item in items_qs:
        # Название x Кол-во - Цена (сумма по позиции можно item.sub_total)
        line = f"• {item.product.name} x {item.qty} — {item.sub_total} сом"
        items_lines.append(line)

    # Не отправлять сообщение без товаров — только одно сообщение с полным составом
    if not items_lines:
        logger.warning(
            "Telegram: заказ pk=%s без позиций — сообщение не отправлено (проверьте создание OrderItem).",
            order_id,
        )
        return False

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
        resp = requests.post(url, json=payload, timeout=15)
        try:
            body = resp.json()
        except ValueError:
            body = {"raw": (resp.text or "")[:500]}
        if not resp.ok:
            logger.error(
                "Telegram API ошибка для заказа %s: HTTP %s — %s",
                order.order_id,
                resp.status_code,
                body,
            )
            return False
        if not body.get("ok"):
            logger.error(
                "Telegram API ok=false для заказа %s: %s",
                order.order_id,
                body,
            )
            return False
        logger.info("Заказ %s отправлен в Telegram (chat_id=%s)", order.order_id, chat_id)
        return True
    except requests.RequestException as e:
        logger.error("Telegram: сеть/SSL при отправке заказа pk=%s: %s", order_id, e)
        if getattr(e, "response", None) is not None:
            try:
                logger.error("Telegram: тело ответа: %s", e.response.text[:500])
            except Exception:
                pass
        return False
