"""Einfache Anfragebegrenzung fuer missbrauchsanfaellige Endpunkte.

Bewusst ohne Zusatzabhaengigkeit umgesetzt (analog zum Ollama-Provider):
ein Zaehler pro Client-IP und Endpunkt im Django-Cache (Fixed Window).

Grenzen des Ansatzes, dokumentiert statt versteckt:
- Der Standard-Cache (LocMemCache) zaehlt pro Prozess. Mit mehreren
  gunicorn-Workern vervielfacht sich das effektive Limit entsprechend;
  fuer den Schutz vor stumpfem Durchprobieren reicht das aus.
- Hinter einem Reverse-Proxy ist REMOTE_ADDR die Proxy-Adresse und das
  Limit wirkt global. X-Forwarded-For wird absichtlich nicht ausgewertet,
  weil der Header ohne vertrauenswuerdige Proxy-Kette faelschbar ist.
"""

from functools import wraps

from django.core.cache import cache
from django.http import HttpResponse, JsonResponse

RATE_LIMIT_MESSAGE = (
    "Zu viele Anfragen in kurzer Zeit. Bitte warten Sie einen Moment "
    "und versuchen Sie es dann erneut."
)


def get_client_identifier(request):
    return request.META.get("REMOTE_ADDR") or "unknown"


def is_rate_limited(request, scope, max_requests, window_seconds):
    """Zaehlt die Anfrage und meldet, ob das Fenster-Limit erreicht ist."""
    cache_key = f"ratelimit:{scope}:{get_client_identifier(request)}"

    # add() legt den Zaehler samt Ablaufzeit nur an, wenn er fehlt; incr()
    # erhoeht danach atomar innerhalb des laufenden Fensters.
    if cache.add(cache_key, 1, timeout=window_seconds):
        return False

    try:
        request_count = cache.incr(cache_key)
    except ValueError:
        # Fenster genau zwischen add() und incr() abgelaufen.
        cache.add(cache_key, 1, timeout=window_seconds)
        return False

    return request_count > max_requests


def build_rate_limit_response(request):
    wants_json = (
        request.headers.get("x-requested-with") == "XMLHttpRequest"
        or "application/json" in request.headers.get("accept", "")
    )

    if wants_json:
        return JsonResponse(
            {"ok": False, "answer": "", "error": RATE_LIMIT_MESSAGE},
            status=429,
        )

    return HttpResponse(
        RATE_LIMIT_MESSAGE,
        status=429,
        content_type="text/plain; charset=utf-8",
    )


def rate_limit(scope, max_requests, window_seconds, methods=("POST",)):
    """Dekorator: begrenzt Anfragen pro Client-IP fuer die genannten Methoden.

    Nur die angegebenen HTTP-Methoden zaehlen, damit z. B. das blosse
    Anzeigen des Login-Formulars (GET) das Limit nicht verbraucht.
    """

    def decorator(view):
        @wraps(view)
        def wrapped(request, *args, **kwargs):
            if request.method in methods and is_rate_limited(
                request, scope, max_requests, window_seconds
            ):
                return build_rate_limit_response(request)

            return view(request, *args, **kwargs)

        return wrapped

    return decorator
