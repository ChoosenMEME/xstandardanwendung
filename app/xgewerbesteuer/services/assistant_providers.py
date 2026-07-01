"""Provider-Schnittstellen fuer den optionalen KI-Assistenten."""

import json
import socket
import urllib.error
import urllib.request

from django.conf import settings


class AssistantProviderError(Exception):
    """Benutzerverstaendlicher Fehler beim Aufruf eines Assistant-Providers."""


class AssistantProvider:
    """Basisklasse fuer austauschbare Assistant-Provider."""

    provider_name = "disabled"
    display_name = "Nicht konfiguriert"
    processing_notice = "Keine KI-Verarbeitung konfiguriert"

    def answer(self, prompt):
        raise NotImplementedError


class DisabledAssistantProvider(AssistantProvider):
    """Standardprovider, wenn keine KI konfiguriert ist."""

    provider_name = "disabled"
    display_name = "Nicht konfiguriert"

    def answer(self, prompt):
        raise AssistantProviderError(
            "Der KI-Assistent ist aktuell nicht konfiguriert. Upload, Auswertung, "
            "Exporte und gespeicherte Auswertungen koennen weiterhin ohne "
            "Einschraenkung genutzt werden."
        )


class OllamaAssistantProvider(AssistantProvider):
    """Lokaler Ollama-Provider ohne externe Python-Abhaengigkeiten."""

    provider_name = "ollama"
    display_name = "Ollama"
    processing_notice = "Lokale KI-Verarbeitung ueber Ollama"

    def __init__(self, base_url, model, timeout_seconds):
        self.base_url = (base_url or "").rstrip("/")
        self.model = model
        self.timeout_seconds = timeout_seconds

    def answer(self, prompt):
        if not self.base_url or not self.model:
            raise AssistantProviderError(
                "Der KI-Assistent ist nicht vollstaendig konfiguriert."
            )

        request_body = json.dumps({
            "model": self.model,
            "prompt": prompt,
            "stream": False,
        }).encode("utf-8")
        request = urllib.request.Request(
            f"{self.base_url}/api/generate",
            data=request_body,
            headers={"Content-Type": "application/json"},
            method="POST",
        )

        try:
            with urllib.request.urlopen(
                request,
                timeout=self.timeout_seconds,
            ) as response:
                payload = json.loads(response.read().decode("utf-8"))
        except socket.timeout as exc:
            raise AssistantProviderError(
                "Der KI-Assistent hat nicht rechtzeitig geantwortet."
            ) from exc
        except urllib.error.URLError as exc:
            raise AssistantProviderError(
                "Der KI-Assistent ist aktuell nicht erreichbar."
            ) from exc
        except (json.JSONDecodeError, UnicodeDecodeError) as exc:
            raise AssistantProviderError(
                "Die Antwort des KI-Assistenten konnte nicht verarbeitet werden."
            ) from exc

        answer = payload.get("response")

        if not isinstance(answer, str) or not answer.strip():
            raise AssistantProviderError(
                "Die Antwort des KI-Assistenten war nicht verwertbar."
            )

        return answer.strip()


def get_assistant_settings():
    """Liest nur nicht geheime Assistant-Konfiguration aus Django-Settings."""

    return {
        "enabled": bool(getattr(settings, "AI_ASSISTANT_ENABLED", False)),
        "provider": getattr(settings, "AI_ASSISTANT_PROVIDER", "disabled"),
        "model": getattr(settings, "AI_ASSISTANT_MODEL", ""),
        "base_url": getattr(settings, "AI_ASSISTANT_BASE_URL", ""),
        "timeout_seconds": getattr(settings, "AI_ASSISTANT_TIMEOUT_SECONDS", 10),
    }


def get_assistant_provider():
    """Erzeugt den konfigurierten Provider oder den sicheren deaktivierten Standard."""

    config = get_assistant_settings()

    if not config["enabled"]:
        return DisabledAssistantProvider()

    provider_name = (config["provider"] or "disabled").lower()

    if provider_name == "ollama":
        return OllamaAssistantProvider(
            base_url=config["base_url"],
            model=config["model"],
            timeout_seconds=config["timeout_seconds"],
        )

    return DisabledAssistantProvider()


def get_assistant_provider_status():
    """Status fuer die UI ohne Secrets, Tokens oder technische Endpunkte."""

    provider = get_assistant_provider()
    enabled = not isinstance(provider, DisabledAssistantProvider)

    return {
        "enabled": enabled,
        "provider": provider.provider_name,
        "display_name": provider.display_name,
        "processing_notice": provider.processing_notice,
        "unconfigured_message": (
            ""
            if enabled
            else (
                "Der KI-Assistent ist aktuell nicht konfiguriert. Upload, "
                "Auswertung, Exporte und gespeicherte Auswertungen koennen "
                "weiterhin ohne Einschraenkung genutzt werden."
            )
        ),
    }
