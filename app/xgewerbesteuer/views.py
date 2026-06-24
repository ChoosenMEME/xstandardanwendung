from decimal import Decimal, InvalidOperation, ROUND_HALF_UP
from pathlib import Path
from xml.etree.ElementTree import ParseError

from defusedxml import ElementTree
from defusedxml.common import DefusedXmlException
from django.shortcuts import render
from lxml import etree


SCHEMA_DIR = Path(__file__).resolve().parent / "schemas"

XSD_SCHEMA_FILES = [
    "xunternehmen-gewerbesteuer.xsd",
    "gewerbesteuer.xsd",
]

MAX_UPLOAD_SIZE_BYTES = 5 * 1024 * 1024


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


def parse_decimal_value(value):
    if not value or value == "Nicht gefunden":
        return None

    cleaned_value = (
        value.replace("EUR", "")
        .replace("€", "")
        .replace("%", "")
        .replace(" ", "")
        .strip()
    )

    if "," in cleaned_value and "." in cleaned_value:
        cleaned_value = cleaned_value.replace(".", "").replace(",", ".")
    elif "," in cleaned_value:
        cleaned_value = cleaned_value.replace(",", ".")

    try:
        return Decimal(cleaned_value)
    except InvalidOperation:
        return None


def format_decimal_value(value):
    rounded_value = value.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
    return f"{rounded_value:.2f}"


def build_calculation_explanation(trade_tax_assessment_amount, assessment_rate):
    parsed_trade_tax_assessment_amount = parse_decimal_value(trade_tax_assessment_amount)
    parsed_assessment_rate = parse_decimal_value(assessment_rate)

    if parsed_trade_tax_assessment_amount is None or parsed_assessment_rate is None:
        return {
            "can_calculate": False,
            "message": (
                "Die Berechnung kann nicht angezeigt werden, weil der "
                "Gewerbesteuermessbetrag oder der Hebesatz fehlt."
            ),
        }

    calculated_trade_tax = (
        parsed_trade_tax_assessment_amount * parsed_assessment_rate / Decimal("100")
    )

    return {
        "can_calculate": True,
        "formula": "Gewerbesteuer = Gewerbesteuermessbetrag × Hebesatz / 100",
        "example": (
            f"{format_decimal_value(parsed_trade_tax_assessment_amount)} × "
            f"{format_decimal_value(parsed_assessment_rate)} / 100 = "
            f"{format_decimal_value(calculated_trade_tax)} EUR"
        ),
        "message": (
            "Der Gewerbesteuermessbetrag wird mit dem kommunalen Hebesatz "
            "multipliziert. Danach wird durch 100 geteilt, weil der Hebesatz "
            "als Prozentwert verwendet wird."
        ),
    }


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


def classify_payment_type(amount_due, advance_payments):
    if advance_payments:
        return {
            "type": "Vorauszahlung",
            "message": (
                "Dieser Bescheid enthält Vorauszahlungen. Diese werden getrennt "
                "von endgültigen Festsetzungen, Nachzahlungen und Erstattungen angezeigt."
            ),
        }

    parsed_amount_due = parse_decimal_value(amount_due)

    if parsed_amount_due is None:
        return {
            "type": "Nicht eindeutig bestimmbar",
            "message": (
                "Die Zahlungsart konnte aus den vorhandenen Daten nicht eindeutig "
                "bestimmt werden."
            ),
        }

    if parsed_amount_due > Decimal("0"):
        return {
            "type": "Nachzahlung",
            "message": (
                "Der Bescheid weist einen positiven Zahlbetrag aus. Das spricht "
                "für eine noch zu zahlende Nachzahlung."
            ),
        }

    if parsed_amount_due < Decimal("0"):
        return {
            "type": "Erstattung",
            "message": (
                "Der Bescheid weist einen negativen Betrag aus. Das spricht "
                "für eine Erstattung oder Verrechnung zugunsten des Unternehmens."
            ),
        }

    return {
        "type": "Keine Zahlung",
        "message": (
            "Der Bescheid weist einen Zahlbetrag von 0,00 aus. Daraus ergibt "
            "sich keine direkte Zahlungspflicht."
        ),
    }


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


def validate_xml_against_xsd(xml_data):
    validation_errors = []

    xml_parser = etree.XMLParser(
        resolve_entities=False,
        no_network=True,
        load_dtd=False,
        dtd_validation=False,
        huge_tree=False,
    )

    try:
        xml_document = etree.fromstring(xml_data, parser=xml_parser)
    except etree.XMLSyntaxError:
        return False, None, "Die XML-Datei ist nicht wohlgeformt."

    for schema_file_name in XSD_SCHEMA_FILES:
        schema_path = SCHEMA_DIR / schema_file_name

        if not schema_path.exists():
            validation_errors.append(f"{schema_file_name}: Schema-Datei wurde nicht gefunden.")
            continue

        try:
            schema_document = etree.parse(str(schema_path))
            schema = etree.XMLSchema(schema_document)
            schema.assertValid(xml_document)

            return True, schema_file_name, None

        except etree.DocumentInvalid as error:
            last_error = error.error_log.last_error

            if last_error is not None:
                validation_errors.append(f"{schema_file_name}: {last_error.message}")
            else:
                validation_errors.append(f"{schema_file_name}: XML passt nicht zum Schema.")

        except etree.XMLSchemaParseError:
            validation_errors.append(f"{schema_file_name}: Schema konnte nicht gelesen werden.")

        except OSError:
            validation_errors.append(f"{schema_file_name}: Schema-Datei konnte nicht geöffnet werden.")

    if validation_errors:
        return False, None, " | ".join(validation_errors)

    return False, None, "Es konnte keine passende XSD-Schema-Datei für die Validierung gefunden werden."


def xgewerbesteuer_default(request):
    context = {}

    if request.method == "POST":
        uploaded_file = request.FILES.get("bescheid")

        if not uploaded_file:
            context["upload_error"] = "Bitte wählen Sie eine XML-Datei aus."

        elif not uploaded_file.name.lower().endswith(".xml"):
            context["upload_error"] = "Die hochgeladene Datei muss eine XML-Datei sein."

        elif uploaded_file.size > MAX_UPLOAD_SIZE_BYTES:
            context["upload_error"] = "Die hochgeladene Datei ist zu groß."

        else:
            try:
                xml_data = uploaded_file.read()

                root = ElementTree.fromstring(xml_data)

                is_valid, schema_name, schema_error = validate_xml_against_xsd(xml_data)

                if not is_valid:
                    context["validation_error"] = (
                        "Die Datei konnte nicht vollständig validiert werden. "
                        "Bitte prüfen Sie, ob es sich um einen gültigen "
                        "XGewerbesteuer-Bescheid handelt."
                    )
                else:
                    municipality = extract_municipality(root)
                    tax_period = extract_tax_period(root)
                    amount_due = extract_amount_due(root)
                    trade_tax_assessment_amount = extract_trade_tax_assessment_amount(root)
                    assessment_rate = extract_assessment_rate(root)
                    due_dates = extract_due_dates(root)
                    advance_payments = extract_advance_payments(root)
                    payment_classification = classify_payment_type(amount_due, advance_payments)

                    summary_items = [
                        {"label": "Gemeinde / Kommune", "value": municipality},
                        {"label": "Steuerjahr / Erhebungszeitraum", "value": tax_period},
                        {"label": "Zahlbetrag", "value": amount_due},
                        {"label": "Zahlungsart", "value": payment_classification["type"]},
                        {"label": "Gewerbesteuermessbetrag", "value": trade_tax_assessment_amount},
                        {"label": "Hebesatz", "value": assessment_rate},
                        {"label": "Fälligkeiten", "value": due_dates},
                    ]

                    calculation_explanation = build_calculation_explanation(
                        trade_tax_assessment_amount,
                        assessment_rate,
                    )

                    context["uploaded_file_name"] = uploaded_file.name
                    context["uploaded_file_size"] = uploaded_file.size
                    context["summary_items"] = summary_items
                    context["calculation_explanation"] = calculation_explanation
                    context["advance_payments"] = advance_payments
                    context["payment_classification"] = payment_classification
                    context["validation_success"] = (
                        "Die Datei wurde erfolgreich geprüft und entspricht dem erwarteten "
                        f"XGewerbesteuer-Schema. Verwendetes Schema: {schema_name}"
                    )

            except (ParseError, DefusedXmlException):
                context["upload_error"] = (
                    "Die Datei ist nicht XML-konform oder enthält unsichere XML-Inhalte "
                    "und konnte nicht verarbeitet werden."
                )

            except Exception:
                context["upload_error"] = (
                    "Die Datei konnte nicht verarbeitet werden. "
                    "Bitte prüfen Sie die Datei und versuchen Sie es erneut."
                )

    return render(request, "xgewerbesteuer_default.html", context)
