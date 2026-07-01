"""Supportfreundliche Fehler-IDs ohne sensible Falldaten."""

import logging
import uuid


logger = logging.getLogger(__name__)
logger.addHandler(logging.NullHandler())


def generate_error_id():
    """Erzeugt eine kurze neutrale ID, die keine Eingabedaten enthaelt."""
    return f"XGST-{uuid.uuid4().hex[:8].upper()}"


def log_upload_issue(error_id, code, level="warning", exception=None):
    """Loggt nur neutrale Metadaten, damit keine Bescheiddaten im Log landen."""
    exception_type = exception.__class__.__name__ if exception else None
    message = f"upload_issue error_id={error_id} code={code}"

    if exception_type:
        message = f"{message} exception_type={exception_type}"

    log_method = logger.error if level == "error" else logger.warning
    log_method(message)
