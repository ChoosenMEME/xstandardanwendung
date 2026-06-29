"""XML-Datenextraktion fuer XGewerbesteuer-Bescheide."""


def get_local_name(tag):
    if "}" in tag:
        return tag.split("}", 1)[1]
    return tag


def clean_text(text):
    if text and text.strip():
        return " ".join(text.split())
    return None


def find_first_text_by_tag_names(root, tag_names):
    normalized_tag_names = {tag_name.lower() for tag_name in tag_names}

    for element in root.iter():
        tag_name = get_local_name(element.tag).lower()

        if tag_name in normalized_tag_names:
            value = clean_text(element.text)

            if value:
                return value

    return "Nicht gefunden"


def extract_municipality(root):
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
    )


def extract_trade_tax_assessment_amount(root):
    return find_first_text_by_tag_names(
        root,
        [
            "gewerbesteuermessbetrag",
            "steuermessbetrag",
            "messbetrag",
            "festgesetztergewerbesteuermessbetrag",
        ],
    )


def extract_assessment_rate(root):
    return find_first_text_by_tag_names(
        root,
        [
            "hebesatz",
            "gewerbesteuerhebesatz",
            "hebensatz",
            "kommunalerhebesatz",
        ],
    )


def extract_advance_payment_period(payment_element):
    for element in payment_element.iter():
        tag_name = get_local_name(element.tag).lower()
        value = clean_text(element.text)

        if not value:
            continue

        if tag_name in ["bezugsjahr", "steuerjahr", "jahr"]:
            return value

    return "Nicht gefunden"


def extract_advance_payments(root):
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
            item["period"],
            item["due_date"],
            item["amount"],
        ),
    )


def extract_due_dates(root):
    due_dates = []

    for element in root.iter():
        tag_name = get_local_name(element.tag).lower()

        if tag_name in [
            "faelligkeit",
            "fälligkeit",
            "faelligkeitsdatum",
            "fälligkeitsdatum",
            "zahlungstermin",
            "zahlungsfrist",
            "datumfaelligkeit",
        ]:
            value = clean_text(element.text)

            if value and value not in due_dates:
                due_dates.append(value)

    if due_dates:
        return ", ".join(due_dates)

    return "Nicht gefunden"
