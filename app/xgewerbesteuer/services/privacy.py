"""Zentrale Maskierung fuer den Datenschutzmodus."""

from copy import deepcopy


MASK_PREFIX = "••••"
MISSING_VALUES = {"", "Nicht gefunden", None}

SENSITIVE_KEYS = {
    "file_name",
    "uploaded_file_name",
    "municipality",
    "tax_number",
    "tax_number_bund",
    "steuernummer",
    "steuernummer_bund",
    "message_id",
    "nachrichten_id",
    "aktenzeichen",
    "court_reference",
    "address",
    "street",
    "postal_code",
}

SENSITIVE_LABEL_PARTS = [
    "gemeinde",
    "kommune",
    "steuernummer",
    "identifikator",
    "identifier",
    "nachrichten-id",
    "nachrichtenid",
    "aktenzeichen",
    "adresse",
    "anschrift",
    "name",
]


def anonymize_value(value):
    """Maskiert einen einzelnen Wert ohne fachliche Zahlenwerte zu verändern."""
    if value in MISSING_VALUES:
        return value

    text = str(value)

    if text.startswith(MASK_PREFIX):
        return text

    if len(text) <= 4:
        return "•" * len(text)

    return f"{MASK_PREFIX}{text[-4:]}"


def is_sensitive_label(label):
    """True, wenn ein Anzeige-Label auf einen sensiblen Wert hindeutet."""
    normalized = str(label or "").casefold()

    return any(part in normalized for part in SENSITIVE_LABEL_PARTS)


def _is_sensitive_key(key):
    normalized = str(key or "").casefold()

    return normalized in SENSITIVE_KEYS or any(
        part in normalized
        for part in [
            "steuernummer",
            "aktenzeichen",
            "message_id",
            "nachrichten_id",
            "nachrichtenid",
        ]
    )


def _anonymize_item(value):
    if isinstance(value, list):
        return [_anonymize_item(item) for item in value]

    if not isinstance(value, dict):
        return value

    anonymized = {}
    item_label = value.get("label") or value.get("Beschreibung")
    item_has_sensitive_label = is_sensitive_label(item_label)

    for key, item_value in value.items():
        if _is_sensitive_key(key):
            anonymized[key] = anonymize_value(item_value)
        elif item_has_sensitive_label and key in ["value", "current_value", "previous_value"]:
            anonymized[key] = anonymize_value(item_value)
        else:
            anonymized[key] = _anonymize_item(item_value)

    return anonymized


def anonymize_result_context(context):
    """Erzeugt eine maskierte Kopie des fertigen Darstellungskontexts."""
    anonymized = _anonymize_item(deepcopy(context))
    anonymized["privacy_mode_enabled"] = True

    return anonymized
