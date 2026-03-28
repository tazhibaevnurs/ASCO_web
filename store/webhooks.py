"""
Входящие вебхуки: подпись и идемпотентность.
Stripe: https://stripe.com/docs/webhooks/signatures
ЮKassa: сверка уведомления с GET /v3/payments/{id} (см. plugin/yookassa_webhook.py).
Telegram: secret_token при setWebhook.
"""
import logging

import stripe
from django.conf import settings
from django.db import IntegrityError
from django.http import HttpResponse, HttpResponseForbidden
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST

from plugin.webhook_verify import constant_time_equals
from plugin.yookassa_webhook import verify_yookassa_notification
from store.models import StripeWebhookEvent
from store.stripe_fulfillment import try_fulfill_stripe_checkout_session

logger = logging.getLogger(__name__)


@csrf_exempt
@require_POST
def stripe_webhook(request):
    secret = (getattr(settings, "STRIPE_WEBHOOK_SECRET", "") or "").strip()
    if not secret:
        logger.warning("stripe_webhook: STRIPE_WEBHOOK_SECRET не задан")
        return HttpResponseForbidden("Webhook disabled")

    payload = request.body
    sig_header = request.META.get("HTTP_STRIPE_SIGNATURE", "")

    try:
        event = stripe.Webhook.construct_event(payload, sig_header, secret)
    except ValueError:
        return HttpResponse(status=400)
    except stripe.error.SignatureVerificationError:
        return HttpResponse(status=400)
    except Exception as exc:
        logger.exception("stripe_webhook verify failed: %s", exc)
        return HttpResponse(status=400)

    eid = event.get("id")
    etype = event.get("type", "")
    if not eid:
        return HttpResponse(status=400)

    try:
        StripeWebhookEvent.objects.create(event_id=eid, event_type=etype)
    except IntegrityError:
        return HttpResponse(status=200)

    if etype == "checkout.session.completed":
        sess = (event.get("data") or {}).get("object") or {}
        meta_pk = (sess.get("metadata") or {}).get("order_pk")
        sid = sess.get("id")
        if meta_pk and sid:
            try:
                result = try_fulfill_stripe_checkout_session(
                    order_pk=int(meta_pk),
                    session_id=sid,
                    request=None,
                    clear_cart=False,
                )
                if result == "failed":
                    StripeWebhookEvent.objects.filter(event_id=eid).delete()
                    return HttpResponse(status=500)
            except Exception:
                logger.exception("stripe_webhook fulfillment")
                StripeWebhookEvent.objects.filter(event_id=eid).delete()
                return HttpResponse(status=500)

    return HttpResponse(status=200)


@csrf_exempt
@require_POST
def yookassa_webhook(request):
    body = request.body
    ok, err = verify_yookassa_notification(body)
    if not ok:
        logger.warning("yookassa_webhook: %s", err)
        return HttpResponseForbidden("Invalid notification")

    return HttpResponse(status=200)


@csrf_exempt
@require_POST
def telegram_webhook(request):
    secret = (getattr(settings, "TELEGRAM_WEBHOOK_SECRET", "") or "").strip()
    if not secret:
        logger.warning("telegram_webhook: TELEGRAM_WEBHOOK_SECRET не задан")
        return HttpResponseForbidden("Webhook disabled")

    token = request.headers.get("X-Telegram-Bot-Api-Secret-Token", "")
    if not constant_time_equals(token, secret):
        return HttpResponseForbidden("Invalid secret token")

    return HttpResponse(status=200)
