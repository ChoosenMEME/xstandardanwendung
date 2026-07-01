"""Globale Template-Kontexte fuer die XGewerbesteuer-Oberflaeche."""

from django.conf import settings

from .services.assistant import build_assistant_ui_context
from .views import RESULT_SESSION_KEY, _build_result_context


def login_enabled(request):
    return {"LOGIN_ENABLED": settings.LOGIN_ENABLED}


def assistant_context(request):
    """Stellt das globale Assistant-Panel ohne Rohdaten oder Secrets bereit."""

    session_data = request.session.get(RESULT_SESSION_KEY)
    result_context = None

    if session_data:
        result_context = _build_result_context(session_data)

    return build_assistant_ui_context(result_context=result_context)
