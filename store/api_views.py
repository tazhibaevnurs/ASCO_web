import json
import logging

from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.views.decorators.http import require_POST

from plugin.ai_quota import release_ai_generation_slot, try_consume_ai_generation

logger = logging.getLogger(__name__)


@login_required
@require_POST
def ai_generate(request):
    """
    Эндпоинт AI: сначала валидация тела, затем квота, затем вызов провайдера (заглушка).
    При сбое провайдера квота откатывается.
    """
    try:
        body = request.body.decode("utf-8") if request.body else "{}"
        data = json.loads(body) if body.strip() else {}
    except (UnicodeDecodeError, json.JSONDecodeError):
        return JsonResponse({"error": "Invalid JSON"}, status=400)

    prompt = (data.get("prompt") or "")[:8000]
    if not prompt.strip():
        return JsonResponse({"error": "prompt is required"}, status=400)

    ok, msg = try_consume_ai_generation(request.user)
    if not ok:
        return JsonResponse({"error": msg}, status=429)

    try:
        # Здесь: вызов Anthropic/OpenAI с таймаутом. Ошибка → откат квоты и 503.
        # result = call_llm(prompt)
        _ = prompt  # заглушка до подключения API
    except Exception as exc:
        logger.warning("ai_generate provider error: %s", exc)
        release_ai_generation_slot(request.user)
        return JsonResponse(
            {"error": "AI service temporarily unavailable"},
            status=503,
            headers={"Retry-After": "60"},
        )

    return JsonResponse(
        {
            "ok": True,
            "note": "Подключите вызов LLM в store/api_views.ai_generate; квота учтена.",
            "prompt_echo_chars": len(prompt),
        }
    )
