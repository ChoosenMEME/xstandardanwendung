"""Context-Prozessoren fuer die XGewerbesteuer-App."""

from django.conf import settings


def login_enabled(request):
    return {"LOGIN_ENABLED": settings.LOGIN_ENABLED}
