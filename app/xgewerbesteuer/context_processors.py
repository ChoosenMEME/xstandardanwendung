"""Globale Template-Kontexte fuer die XGewerbesteuer-Oberflaeche."""

from django.conf import settings

from .calculations import build_plausibility_check
from .constants import RESULT_SESSION_KEY
from .services.assistant import build_assistant_ui_context
from .services.bescheid import build_due_date_calendar


def login_enabled(request):
    """Stellt LOGIN_ENABLED fuer Navigation und Templates bereit."""
    return {"LOGIN_ENABLED": settings.LOGIN_ENABLED}


def _build_assistant_panel_context(session_data):
    """Leichtgewichtiger Ausschnitt des Ergebniskontexts fuer das Assistant-Panel.

    Dieser Context Processor laeuft auf jeder gerenderten Seite. Modus und
    Beispielfragen des Panels benoetigen nur wenige Felder; der vollstaendige
    Ergebniskontext (Liquiditaet, Hinweisbereich, Statusampel) wird deshalb
    bewusst nicht aufgebaut — er entsteht weiterhin nur in den Ergebnis-Views.
    """
    current_bescheid = session_data.get("current_bescheid")

    if not current_bescheid:
        return None

    return {
        "current_bescheid": current_bescheid,
        "change_comparison_items": session_data.get("change_comparison_items"),
        "due_date_calendar": build_due_date_calendar(current_bescheid),
        "plausibility_check": build_plausibility_check(current_bescheid),
    }


def assistant_context(request):
    """Stellt das globale Assistant-Panel ohne Rohdaten oder Secrets bereit."""

    session_data = request.session.get(RESULT_SESSION_KEY)
    result_context = None

    if session_data:
        result_context = _build_assistant_panel_context(session_data)

    return build_assistant_ui_context(result_context=result_context)
