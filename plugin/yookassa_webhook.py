"""
Проверка уведомлений ЮKassa: сверка с API GET /v3/payments/{id} (Basic shopId:secretKey).
Документация: https://yookassa.ru/developers/using-api/webhooks
"""
from __future__ import annotations

import base64
import json
import logging
from typing import Any, Dict, Tuple

import requests
from django.conf import settings

logger = logging.getLogger(__name__)

YOOKASSA_API = "https://api.yookassa.ru/v3"


def verify_yookassa_notification(body: bytes) -> Tuple[bool, str]:
    """
    Возвращает (True, '') если JSON валиден и состояние платежа в API совпадает с уведомлением.
    """
    shop_id = (getattr(settings, "YOOKASSA_SHOP_ID", "") or "").strip()
    secret = (getattr(settings, "YOOKASSA_SECRET_KEY", "") or "").strip()
    if not shop_id or not secret:
        return False, "YOOKASSA_SHOP_ID / YOOKASSA_SECRET_KEY не заданы"

    try:
        data: Dict[str, Any] = json.loads(body.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        return False, f"invalid json: {exc}"

    obj = data.get("object")
    if not isinstance(obj, dict):
        return False, "missing object"

    payment_id = obj.get("id")
    if not payment_id:
        return False, "missing payment id"

    auth = base64.b64encode(f"{shop_id}:{secret}".encode("utf-8")).decode("ascii")
    url = f"{YOOKASSA_API}/payments/{payment_id}"
    try:
        resp = requests.get(
            url,
            headers={
                "Authorization": f"Basic {auth}",
                "Content-Type": "application/json",
            },
            timeout=20,
        )
    except requests.RequestException as exc:
        logger.warning("YooKassa API request failed: %s", exc)
        return False, "api unreachable"

    if resp.status_code != 200:
        logger.warning(
            "YooKassa payment verify HTTP %s: %s", resp.status_code, resp.text[:500]
        )
        return False, "api error"

    try:
        remote = resp.json()
    except ValueError:
        return False, "invalid api json"

    # Сверяем ключевые поля уведомления с источником правды (API).
    for key in ("status", "paid", "amount"):
        if key in obj and key in remote and obj[key] != remote[key]:
            return False, f"mismatch on {key}"

    return True, ""
