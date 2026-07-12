"""XML-Datenextraktion fuer XGewerbesteuer-Bescheide."""

SUPPORTED_MESSAGE_TYPES = {
    "bescheide.gewerbesteuer.0001": {
        "label": "Gewerbesteuerbescheid",
        "category": "assessment",
        "supports_comparison": True,
        "summary": "Normaler Gewerbesteuerbescheid mit Festsetzungsdaten.",
    },
    "bescheide.zinsen.0002": {
        "label": "Zinsbescheid",
        "category": "interest",
        "supports_comparison": False,
        "summary": "Zinsbescheid; Steuerberechnungen sind nur eingeschraenkt pruefbar.",
    },
    "bescheide.vorauszahlung.0003": {
        "label": "Vorauszahlungsbescheid",
        "category": "advance_payment",
        "supports_comparison": True,
        "summary": "Vorauszahlungsbescheid mit gesonderter Einordnung der Vorauszahlungen.",
    },
    "bescheide.gewerbesteuer.generisch.0010": {
        "label": "Generische Gewerbesteuernachricht",
        "category": "generic",
        "supports_comparison": True,
        "summary": "Generische Gewerbesteuernachricht mit automatisch ausgelesenen Kerndaten.",
    },
    "berechnung.gewerbesteuer.0021": {
        "label": "Gewerbesteuerberechnung",
        "category": "calculation",
        "supports_comparison": False,
        "summary": "Gewerbesteuerberechnung; Zahlungs- und Faelligkeitsdaten koennen fehlen.",
    },
}


def get_local_name(tag):
    """Entfernt den Namespace-Anteil aus einem XML-Tag-Namen."""
    if "}" in tag:
        return tag.split("}", 1)[1]
    return tag


def detect_message_type(root):
    """Bestimmt den XGewerbesteuer-Nachrichtentyp aus dem Wurzelelement."""
    return get_local_name(root.tag)


def get_message_type_config(message_type):
    """Liefert die Konfiguration eines unterstuetzten Nachrichtentyps oder None."""
    return SUPPORTED_MESSAGE_TYPES.get(message_type)


def is_supported_message_type(message_type):
    """True, wenn der Nachrichtentyp von der Anwendung verarbeitet werden kann."""
    return message_type in SUPPORTED_MESSAGE_TYPES


def build_message_type_summary(message_type):
    """Baut Anzeigedaten (Label, Kategorie, Vergleichsfaehigkeit) zum Nachrichtentyp."""
    config = get_message_type_config(message_type)

    if not config:
        return {
            "message_type": message_type,
            "message_type_label": "Nicht unterstuetzter Nachrichtentyp",
            "message_type_category": "unsupported",
            "message_type_summary": (
                "Der Nachrichtentyp der XML-Datei wird derzeit nicht unterstuetzt."
            ),
            "supports_comparison": False,
        }

    return {
        "message_type": message_type,
        "message_type_label": config["label"],
        "message_type_category": config["category"],
        "message_type_summary": config["summary"],
        "supports_comparison": config["supports_comparison"],
    }


def clean_text(text):
    """Normalisiert Whitespace in Elementtexten; None fuer leere Inhalte."""
    if text and text.strip():
        return " ".join(text.split())
    return None


# Container-Elemente, deren Inhalte zu einzelnen Vorauszahlungen gehoeren.
# Bescheid-weite Werte (Zahlbetrag, Messbetrag, Hebesatz, Faelligkeiten)
# duerfen nicht aus diesen Teilbaeumen stammen: Je nach Dokumentreihenfolge
# wuerde sonst z. B. der Betrag einer Vorauszahlung als Zahlbetrag des
# gesamten Bescheids angezeigt. Vorauszahlungen liest extract_advance_payments
# separat aus.
ADVANCE_PAYMENT_CONTAINER_TAGS = [
    "gwstvorauszahlungen",
    "vorauszahlungen",
    "vorauszahlung",
]


def iter_elements_excluding_containers(root, excluded_container_tags):
    """Iteriert alle Elemente, ueberspringt aber die genannten Teilbaeume."""
    excluded_tags = {tag.lower() for tag in excluded_container_tags}

    def walk(element):
        yield element

        for child in element:
            if get_local_name(child.tag).lower() in excluded_tags:
                continue

            yield from walk(child)

    yield from walk(root)


def find_first_text_by_tag_names(root, tag_names, exclude_container_tags=None):
    """Sucht namespace-unabhaengig den ersten nicht-leeren Text zu den Tag-Namen."""
    normalized_tag_names = {tag_name.lower() for tag_name in tag_names}

    if exclude_container_tags:
        elements = iter_elements_excluding_containers(root, exclude_container_tags)
    else:
        elements = root.iter()

    for element in elements:
        tag_name = get_local_name(element.tag).lower()

        if tag_name in normalized_tag_names:
            value = clean_text(element.text)

            if value:
                return value

    return None


def extract_municipality(root):
    """Liest die Gemeinde/Kommune aus (bevorzugt aus dem Kommune-Element)."""
    for element in root.iter():
        tag_name = get_local_name(element.tag).lower()

        if tag_name == "kommune":
            for child in element.iter():
                child_tag_name = get_local_name(child.tag).lower()

                if child_tag_name in ["namebehoerde", "namebehörde", "name"]:
                    value = clean_text(child.text)

                    if value:
                        return value

    return find_first_text_by_tag_names(
        root,
        [
            "namebehoerde",
            "namebehörde",
            "behoerde",
            "behörde",
            "gemeinde",
            "kommune",
            "gemeindename",
            "gebietskörperschaft",
            "gebietskoerperschaft",
            "steuerberechtigtegemeinde",
            "hebeberechtigtegemeinde",
        ],
    )


def extract_tax_period(root):
    """Liest das Steuerjahr bzw. den Erhebungszeitraum aus.

    Bevorzugt strukturierte Zeitraum-Elemente (Bezugsjahr, Quartal,
    Beginn/Ende); faellt sonst auf einzelne Jahres-Tags zurueck.
    """
    for element in root.iter():
        tag_name = get_local_name(element.tag).lower()

        if tag_name in ["erhebungszeitraum", "zeitraum"]:
            bezugsjahr = None
            beginn = None
            ende = None
            quartal = None

            for child in element.iter():
                child_tag_name = get_local_name(child.tag).lower()
                value = clean_text(child.text)

                if not value:
                    continue

                if child_tag_name in ["bezugsjahr", "steuerjahr", "jahr"]:
                    bezugsjahr = value
                elif child_tag_name == "beginn":
                    beginn = value
                elif child_tag_name == "ende":
                    ende = value
                elif child_tag_name == "quartal":
                    quartal = value

            if bezugsjahr and quartal:
                return f"{bezugsjahr}, Quartal {quartal}"

            if beginn and ende:
                return f"{beginn} bis {ende}"

            if bezugsjahr:
                return bezugsjahr

    return find_first_text_by_tag_names(
        root,
        [
            "steuerjahr",
            "bezugsjahr",
            "erhebungsjahr",
            "veranlagungsjahr",
            "erhebungszeitraum",
        ],
    )


def extract_amount_due(root):
    """Liest den Zahlbetrag des Bescheids aus (ohne Vorauszahlungs-Teilbaeume)."""
    return find_first_text_by_tag_names(
        root,
        [
            "zahlbetrag",
            "faelligerzahlbetrag",
            "fälligerzahlbetrag",
            "zahlungsbetrag",
            "betragzuzahlen",
            "festgesetztegewerbesteuer",
            "gewerbesteuerbetrag",
            "festsetzungaktuell",
            "berechnungaktuell",
        ],
        exclude_container_tags=ADVANCE_PAYMENT_CONTAINER_TAGS,
    )


def extract_trade_tax_assessment_amount(root):
    """Liest den Gewerbesteuermessbetrag aus."""
    return find_first_text_by_tag_names(
        root,
        [
            "gewerbesteuermessbetrag",
            "steuermessbetrag",
            "messbetrag",
            "festgesetztergewerbesteuermessbetrag",
        ],
        exclude_container_tags=ADVANCE_PAYMENT_CONTAINER_TAGS,
    )


def extract_assessment_rate(root):
    """Liest den kommunalen Hebesatz aus."""
    return find_first_text_by_tag_names(
        root,
        [
            "hebesatz",
            "gewerbesteuerhebesatz",
            "hebensatz",
            "kommunalerhebesatz",
        ],
        exclude_container_tags=ADVANCE_PAYMENT_CONTAINER_TAGS,
    )


def extract_advance_payment_period(payment_element):
    """Liest das Bezugsjahr einer einzelnen Vorauszahlung aus."""
    for element in payment_element.iter():
        tag_name = get_local_name(element.tag).lower()
        value = clean_text(element.text)

        if not value:
            continue

        if tag_name in ["bezugsjahr", "steuerjahr", "jahr"]:
            return value

    return None


def extract_advance_payments(root):
    """Sammelt alle Vorauszahlungen (Betrag, Faelligkeit, Zeitraum) sortiert ein."""
    advance_payments = []

    for element in root.iter():
        tag_name = get_local_name(element.tag).lower()

        if tag_name in ["gwstvorauszahlungen", "vorauszahlungen", "vorauszahlung"]:
            amount = find_first_text_by_tag_names(
                element,
                [
                    "vorauszahlungsbetrag",
                    "vorauszahlungbetrag",
                    "festsetzungaktuell",
                    "zahlbetrag",
                    "betrag",
                ],
            )

            due_date = find_first_text_by_tag_names(
                element,
                [
                    "faelligkeit",
                    "fälligkeit",
                    "faelligkeitsdatum",
                    "fälligkeitsdatum",
                    "zahlungstermin",
                    "zahlungsfrist",
                    "zahlungbis",
                ],
            )

            period = extract_advance_payment_period(element)

            advance_payments.append(
                {
                    "amount": amount,
                    "due_date": due_date,
                    "period": period,
                    "type": "Vorauszahlung",
                }
            )

    return sorted(
        advance_payments,
        key=lambda item: (
            item["period"] or "",
            item["due_date"] or "",
            item["amount"] or "",
        ),
    )


def extract_due_dates(root):
    """Sammelt bescheidweite Faelligkeiten als kommaseparierte Liste."""
    due_dates = []

    # Faelligkeiten einzelner Vorauszahlungen gehoeren zu deren Eintraegen
    # (extract_advance_payments) und wuerden hier zu Doppelterminen im
    # Faelligkeitskalender fuehren.
    for element in iter_elements_excluding_containers(
        root,
        ADVANCE_PAYMENT_CONTAINER_TAGS,
    ):
        tag_name = get_local_name(element.tag).lower()

        if tag_name in [
            "faelligkeit",
            "fälligkeit",
            "faelligkeitsdatum",
            "fälligkeitsdatum",
            "zahlungstermin",
            "zahlungsfrist",
            "datumfaelligkeit",
            "zahlungbis",
        ]:
            value = clean_text(element.text)

            if value and value not in due_dates:
                due_dates.append(value)

    if due_dates:
        return ", ".join(due_dates)

    return None
