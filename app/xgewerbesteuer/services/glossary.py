"""Zentrale kurze Begriffserklaerungen fuer fachliche UI-Hilfen."""

CORE_GLOSSARY_TERMS = [
    "Gewerbesteuermessbetrag",
    "Hebesatz",
    "Gewerbesteuerbetrag",
    "Festsetzung",
    "Vorauszahlung",
    "Fälligkeit",
    "Erhebungszeitraum",
    "Änderungsbescheid",
]

GLOSSARY_TERMS = {
    "Gewerbesteuermessbetrag": {
        "term": "Gewerbesteuermessbetrag",
        "description": (
            "Vom Finanzamt ermittelter Ausgangswert. Mit dem Hebesatz der Gemeinde "
            "ergibt sich daraus vereinfacht die Gewerbesteuer."
        ),
    },
    "Hebesatz": {
        "term": "Hebesatz",
        "description": (
            "Prozentwert der Gemeinde. Er wird auf den Messbetrag angewendet und "
            "beeinflusst die Hoehe der Gewerbesteuer."
        ),
    },
    "Gewerbesteuerbetrag": {
        "term": "Gewerbesteuerbetrag",
        "description": (
            "Der rechnerische Steuerbetrag aus Messbetrag und Hebesatz. Der echte "
            "Bescheid kann Rundungen oder weitere Angaben enthalten."
        ),
    },
    "Festsetzung": {
        "term": "Festsetzung",
        "description": (
            "Die im Bescheid festgehaltene steuerliche Entscheidung. Diese Anzeige "
            "erklaert sie nur vereinfacht und ersetzt keine Beratung."
        ),
    },
    "Vorauszahlung": {
        "term": "Vorauszahlung",
        "description": (
            "Vorab zu zahlender Betrag fuer einen Zeitraum. Er wird spaeter mit der "
            "endgueltigen Festsetzung abgeglichen."
        ),
    },
    "Zahlungsart": {
        "term": "Zahlungsart",
        "description": (
            "Einordnung, ob ein Betrag zum Beispiel als Vorauszahlung, Nachzahlung "
            "oder Erstattung angezeigt wird."
        ),
    },
    "Fälligkeit": {
        "term": "Fälligkeit",
        "description": (
            "Datum, zu dem ein Betrag laut Bescheid gezahlt werden soll. Bitte pruefen "
            "Sie die Angaben im Originalbescheid."
        ),
    },
    "Erhebungszeitraum": {
        "term": "Erhebungszeitraum",
        "description": (
            "Zeitraum, fuer den die Gewerbesteuer betrachtet wird. Meist entspricht "
            "er dem angegebenen Steuerjahr."
        ),
    },
    "Änderungsbescheid": {
        "term": "Änderungsbescheid",
        "description": (
            "Ein Bescheid, der fruehere Angaben fuer denselben Zeitraum aendert. "
            "Vergleiche zeigen nur die ausgelesenen Unterschiede."
        ),
    },
}

GLOSSARY_ALIASES = {
    "Messbetrag": "Gewerbesteuermessbetrag",
    "Steuerjahr / Erhebungszeitraum": "Erhebungszeitraum",
    "Steuerjahr": "Erhebungszeitraum",
    "Zeitraum": "Erhebungszeitraum",
    "Fälligkeiten": "Fälligkeit",
    "Faelligkeit": "Fälligkeit",
    "Faelligkeiten": "Fälligkeit",
    "Zahlbetrag": "Gewerbesteuerbetrag",
    "Ausgelesener Zahlbetrag": "Gewerbesteuerbetrag",
    "Rechnerisch erwarteter Betrag": "Gewerbesteuerbetrag",
    "Vorauszahlungen": "Vorauszahlung",
    "Nachzahlung": "Zahlungsart",
    "Erstattung": "Zahlungsart",
    "Zahlungsart": "Zahlungsart",
    "Änderung": "Änderungsbescheid",
    "Aenderung": "Änderungsbescheid",
}


def normalize_glossary_term(label):
    """Ordnet UI-Labels dem zentralen Glossarbegriff zu."""
    if not label:
        return ""

    text = str(label).strip()
    return GLOSSARY_ALIASES.get(text, text)


def get_glossary_definition(label):
    """Gibt die zentrale Erklaerung zu einem UI-Label zurueck, falls vorhanden."""
    return GLOSSARY_TERMS.get(normalize_glossary_term(label))


def get_missing_core_terms(labels):
    """Meldet Kernbegriffe ohne Erklaerung fuer Tests und Review."""
    return [
        label
        for label in labels
        if get_glossary_definition(label) is None
    ]
