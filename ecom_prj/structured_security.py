"""
Структурированные JSON-логи для событий безопасности (stdout; удобно для Loki, Datadog, CloudWatch).
"""
from __future__ import annotations

import logging
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, Optional

from pythonjsonlogger import jsonlogger


class AscoJsonFormatter(jsonlogger.JsonFormatter):
    def add_fields(self, log_record, record, message_dict):
        super().add_fields(log_record, record, message_dict)
        log_record["timestamp"] = datetime.now(timezone.utc).isoformat()
        log_record.setdefault("event_id", str(uuid.uuid4()))
        log_record["level"] = record.levelname


def log_security_event(
    logger: logging.Logger,
    event: str,
    *,
    level: int = logging.INFO,
    extra: Optional[Dict[str, Any]] = None,
) -> None:
    """Поле security_event + произвольные поля (в JSON через extra)."""
    data = {"security_event": event, **(extra or {})}
    logger.log(level, event, extra=data)
