from decimal import Decimal, InvalidOperation, ROUND_HALF_UP
from io import BytesIO
from pathlib import Path
from xml.etree.ElementTree import ParseError

from defusedxml import ElementTree
from defusedxml.common import DefusedXmlException
from django.http import HttpResponse
from django.shortcuts import render
from lxml import etree
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table


SCHEMA_DIR = Path(__file__).resolve().parent / "schemas"

XSD_SCHEMA_FILES = [
    "xunternehmen-gewerbesteuer.xsd",
    "gewerbesteuer.xsd",
]

MAX_UPLOAD_SIZE_BYTES = 5 * 1024 * 1024
PDF_REPORT_SESSION_KEY = "xgewerbesteuer_pdf_report"


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


def get_upload_error(uploaded_file):
    if not uploaded_file.name.lower().endswith(".xml"):
        return "Die hochgeladene Datei muss eine XML-Datei sein."

    if uploaded_file.size > MAX_UPLOAD_SIZE_BYTES:
        return "Die hochgeladene Datei ist zu groß."

    return None


def build_bescheid_data(uploaded_file, root, schema_name):
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

    return {
        "file_name": uploaded_file.name,
        "file_size": uploaded_file.size,
        "schema_name": schema_name,
        "municipality": municipality,
        "tax_period": tax_period,
        "amount_due": amount_due,
        "trade_tax_assessment_amount": trade_tax_assessment_amount,
        "assessment_rate": assessment_rate,
        "due_dates": due_dates,
        "summary_items": summary_items,
        "calculation_explanation": calculation_explanation,
        "advance_payments": advance_payments,
        "payment_classification": payment_classification,
    }


def process_uploaded_bescheid(uploaded_file):
    upload_error = get_upload_error(uploaded_file)

    if upload_error:
        return {
            "is_valid": False,
            "error_type": "upload",
            "message": upload_error,
        }

    try:
        xml_data = uploaded_file.read()
        root = ElementTree.fromstring(xml_data)

        is_valid, schema_name, schema_error = validate_xml_against_xsd(xml_data)

        if not is_valid:
            return {
                "is_valid": False,
                "error_type": "validation",
                "message": (
                    "Die Datei konnte nicht vollständig validiert werden. "
                    "Bitte prüfen Sie, ob es sich um einen gültigen "
                    "XGewerbesteuer-Bescheid handelt."
                ),
            }

        return {
            "is_valid": True,
            "bescheid": build_bescheid_data(uploaded_file, root, schema_name),
        }

    except (ParseError, DefusedXmlException):
        return {
            "is_valid": False,
            "error_type": "upload",
            "message": (
                "Die Datei ist nicht XML-konform oder enthält unsichere XML-Inhalte "
                "und konnte nicht verarbeitet werden."
            ),
        }

    except Exception:
        return {
            "is_valid": False,
            "error_type": "upload",
            "message": (
                "Die Datei konnte nicht verarbeitet werden. "
                "Bitte prüfen Sie die Datei und versuchen Sie es erneut."
            ),
        }


def build_period_comparison_notice(current_tax_period, previous_tax_period):
    if current_tax_period == "Nicht gefunden" or previous_tax_period == "Nicht gefunden":
        return (
            "Die Steuerjahre konnten nicht vollständig verglichen werden. "
            "Bitte prüfen Sie die Bescheide manuell."
        )

    if current_tax_period == previous_tax_period:
        return (
            "Beide Bescheide enthalten denselben Steuerzeitraum. "
            "Bitte prüfen Sie, ob wirklich ein Vorjahresbescheid hochgeladen wurde."
        )

    return (
        "Die Bescheide haben unterschiedliche Steuerjahre. "
        "Der Vergleich kann für den Vorjahresbezug genutzt werden."
    )


def format_signed_decimal_value(value):
    if value > Decimal("0"):
        return f"+{format_decimal_value(value)}"

    return format_decimal_value(value)


def compare_decimal_values(current_value, previous_value):
    current_decimal = parse_decimal_value(current_value)
    previous_decimal = parse_decimal_value(previous_value)

    if current_decimal is None or previous_decimal is None:
        return {
            "difference": "Nicht vergleichbar",
            "percentage": "Nicht vergleichbar",
            "change_type": "Nicht vergleichbar",
        }

    difference = current_decimal - previous_decimal

    if difference > Decimal("0"):
        change_type = "Erhöhung"
    elif difference < Decimal("0"):
        change_type = "Senkung"
    else:
        change_type = "Unverändert"

    if previous_decimal == Decimal("0"):
        percentage = "Nicht vergleichbar"
    else:
        percentage_difference = difference / previous_decimal * Decimal("100")
        percentage = f"{format_signed_decimal_value(percentage_difference)} %"

    return {
        "difference": format_signed_decimal_value(difference),
        "percentage": percentage,
        "change_type": change_type,
    }


def compare_text_values(current_value, previous_value):
    if current_value == "Nicht gefunden" or previous_value == "Nicht gefunden":
        return {
            "difference": "Nicht vergleichbar",
            "percentage": "Nicht vergleichbar",
            "change_type": "Nicht vergleichbar",
        }

    if current_value == previous_value:
        return {
            "difference": "Keine Änderung",
            "percentage": "Nicht vergleichbar",
            "change_type": "Unverändert",
        }

    return {
        "difference": "Geändert",
        "percentage": "Nicht vergleichbar",
        "change_type": "Geändert",
    }


def classify_change_importance(change_type):
    if change_type == "Erhöhung":
        return {
            "level": "important",
            "label": "Wichtige Änderung",
            "message": "Dieser Wert hat sich gegenüber dem Vorjahr erhöht.",
        }

    if change_type == "Senkung":
        return {
            "level": "notice",
            "label": "Änderung",
            "message": "Dieser Wert hat sich gegenüber dem Vorjahr verringert.",
        }

    if change_type == "Geändert":
        return {
            "level": "notice",
            "label": "Änderung",
            "message": "Dieser Wert hat sich gegenüber dem Vorjahr geändert.",
        }

    return {
        "level": "neutral",
        "label": "Keine wichtige Änderung",
        "message": "Für diesen Wert liegt keine hervorzuhebende Änderung vor.",
    }


def build_change_comparison(current_bescheid, previous_bescheid):
    comparison_fields = [
        {
            "label": "Zahlbetrag",
            "key": "amount_due",
            "type": "decimal",
        },
        {
            "label": "Gewerbesteuermessbetrag",
            "key": "trade_tax_assessment_amount",
            "type": "decimal",
        },
        {
            "label": "Hebesatz",
            "key": "assessment_rate",
            "type": "decimal",
        },
        {
            "label": "Fälligkeiten",
            "key": "due_dates",
            "type": "text",
        },
        {
            "label": "Steuerjahr / Erhebungszeitraum",
            "key": "tax_period",
            "type": "text",
        },
    ]

    comparison_items = []

    for field in comparison_fields:
        current_value = current_bescheid.get(field["key"], "Nicht gefunden")
        previous_value = previous_bescheid.get(field["key"], "Nicht gefunden")

        if field["type"] == "decimal":
            comparison_result = compare_decimal_values(current_value, previous_value)
        else:
            comparison_result = compare_text_values(current_value, previous_value)

        importance = classify_change_importance(comparison_result["change_type"])

        comparison_items.append(
            {
                "label": field["label"],
                "current_value": current_value,
                "previous_value": previous_value,
                "difference": comparison_result["difference"],
                "percentage": comparison_result["percentage"],
                "change_type": comparison_result["change_type"],
                "importance": importance["level"],
                "importance_label": importance["label"],
                "importance_message": importance["message"],
            }
        )

    return comparison_items


NOTICE_SEVERITY_ORDER = {
    "warning": 1,
    "info": 2,
    "neutral": 3,
}

NOTICE_SEVERITY_LABELS = {
    "warning": "Auffälligkeit",
    "info": "Hinweis",
    "neutral": "Neutral",
}


def build_notice(title, message, severity="info", recommendation=None, source_rule=""):
    return {
        "title": title,
        "message": message,
        "severity": severity,
        "severity_label": NOTICE_SEVERITY_LABELS.get(severity, "Hinweis"),
        "recommendation": recommendation,
        "source_rule": source_rule,
    }


def is_missing_value(value):
    return not value or value == "Nicht gefunden"


def build_missing_value_notices(current_bescheid):
    notices = []

    if is_missing_value(current_bescheid.get("amount_due")):
        notices.append(
            build_notice(
                title="Zahlbetrag nicht gefunden",
                message=(
                    "Der Zahlbetrag konnte aus dem Bescheid nicht sicher ausgelesen werden."
                ),
                severity="warning",
                recommendation="Bitte prüfen Sie den Bescheid an dieser Stelle manuell.",
                source_rule="missing-amount-due",
            )
        )

    if is_missing_value(current_bescheid.get("tax_period")):
        notices.append(
            build_notice(
                title="Steuerjahr nicht gefunden",
                message=(
                    "Das Steuerjahr oder der Erhebungszeitraum konnte nicht sicher erkannt werden."
                ),
                severity="warning",
                recommendation="Bitte prüfen Sie, ob der richtige Bescheid hochgeladen wurde.",
                source_rule="missing-tax-period",
            )
        )

    if is_missing_value(current_bescheid.get("municipality")):
        notices.append(
            build_notice(
                title="Gemeinde nicht gefunden",
                message=(
                    "Die Gemeinde oder Kommune konnte aus dem Bescheid nicht sicher ausgelesen werden."
                ),
                severity="info",
                recommendation="Bitte prüfen Sie die Angaben im Bescheid bei Bedarf manuell.",
                source_rule="missing-municipality",
            )
        )

    return notices


def build_payment_notices(current_bescheid):
    payment_classification = current_bescheid.get("payment_classification", {})
    payment_type = payment_classification.get("type")
    amount_due = current_bescheid.get("amount_due", "Nicht gefunden")

    if payment_type == "Nachzahlung":
        return [
            build_notice(
                title="Zahlbetrag beachten",
                message=(
                    f"Der Bescheid weist einen positiven Zahlbetrag von {amount_due} aus."
                ),
                severity="info",
                recommendation=(
                    "Bitte beachten Sie mögliche Zahlungsfristen im Bescheid."
                ),
                source_rule="payment-type-back-payment",
            )
        ]

    if payment_type == "Erstattung":
        return [
            build_notice(
                title="Erstattung oder Verrechnung erkannt",
                message=(
                    f"Der Bescheid weist einen negativen Betrag von {amount_due} aus."
                ),
                severity="info",
                recommendation=(
                    "Bitte prüfen Sie, ob der Betrag erstattet oder verrechnet wird."
                ),
                source_rule="payment-type-refund",
            )
        ]

    if payment_type == "Vorauszahlung":
        return [
            build_notice(
                title="Vorauszahlungen vorhanden",
                message=(
                    "Der Bescheid enthält Vorauszahlungen. Diese werden separat angezeigt."
                ),
                severity="info",
                recommendation=(
                    "Bitte beachten Sie die im Bescheid genannten Zeiträume und Zahlungstermine."
                ),
                source_rule="payment-type-advance-payment",
            )
        ]

    if payment_type == "Nicht eindeutig bestimmbar":
        return [
            build_notice(
                title="Zahlungsart nicht eindeutig",
                message=(
                    "Die Zahlungsart konnte aus den vorhandenen Daten nicht eindeutig bestimmt werden."
                ),
                severity="warning",
                recommendation="Bitte prüfen Sie den Bescheid manuell.",
                source_rule="payment-type-unknown",
            )
        ]

    return []


def build_comparison_notices(change_comparison_items):
    if not change_comparison_items:
        return []

    notices = []

    important_labels = [
        item["label"]
        for item in change_comparison_items
        if item.get("importance") == "important"
    ]

    changed_labels = [
        item["label"]
        for item in change_comparison_items
        if item.get("importance") == "notice"
    ]

    if important_labels:
        notices.append(
            build_notice(
                title="Wichtige Änderung zum Vorjahr",
                message=(
                    "Folgende Werte haben sich gegenüber dem Vorjahresbescheid deutlich verändert: "
                    + ", ".join(important_labels)
                    + "."
                ),
                severity="warning",
                recommendation=(
                    "Bitte prüfen Sie diese Werte besonders aufmerksam."
                ),
                source_rule="comparison-important-change",
            )
        )

    if changed_labels:
        notices.append(
            build_notice(
                title="Weitere Änderung zum Vorjahr",
                message=(
                    "Folgende Werte unterscheiden sich vom Vorjahresbescheid: "
                    + ", ".join(changed_labels)
                    + "."
                ),
                severity="info",
                recommendation=(
                    "Bitte prüfen Sie bei Bedarf, ob die Änderung erwartbar ist."
                ),
                source_rule="comparison-notice-change",
            )
        )

    return notices


def sort_notice_items(notices):
    return sorted(
        notices,
        key=lambda notice: NOTICE_SEVERITY_ORDER.get(notice["severity"], 99),
    )


def build_notice_area(current_bescheid, change_comparison_items=None):
    notices = []

    notices.extend(build_missing_value_notices(current_bescheid))
    notices.extend(build_payment_notices(current_bescheid))
    notices.extend(build_comparison_notices(change_comparison_items or []))

    if not notices:
        return [
            build_notice(
                title="Keine Auffälligkeiten erkannt",
                message=(
                    "Aus den automatisch ausgewerteten Daten ergeben sich aktuell keine besonderen Hinweise."
                ),
                severity="neutral",
                recommendation=None,
                source_rule="no-notice",
            )
        ]

    return sort_notice_items(notices)


STATUS_PRIORITY = {
    "warning": 1,
    "deadline": 2,
    "change": 3,
    "incomplete": 4,
    "ok": 5,
}

STATUS_DEFINITIONS = {
    "warning": {
        "label": "Warnung / Auffälligkeit",
        "message": (
            "Der Bescheid enthält Auffälligkeiten, die besonders geprüft werden sollten."
        ),
        "css_class": "status-warning",
    },
    "deadline": {
        "label": "Frist beachten",
        "message": (
            "Der Bescheid enthält einen Zahlbetrag oder Vorauszahlungen. Bitte beachten Sie mögliche Fristen."
        ),
        "css_class": "status-deadline",
    },
    "change": {
        "label": "Änderung beachten",
        "message": (
            "Im Vergleich zum Vorjahresbescheid wurden Änderungen erkannt."
        ),
        "css_class": "status-change",
    },
    "incomplete": {
        "label": "Daten unvollständig",
        "message": (
            "Einige Angaben konnten nicht vollständig oder nicht eindeutig ausgelesen werden."
        ),
        "css_class": "status-incomplete",
    },
    "ok": {
        "label": "Unauffällig",
        "message": (
            "Aus den automatisch ausgewerteten Daten ergibt sich aktuell kein auffälliger Status."
        ),
        "css_class": "status-ok",
    },
}


def build_status_indicator(current_bescheid, notice_items=None, change_comparison_items=None):
    status_candidates = []
    notice_items = notice_items or []
    change_comparison_items = change_comparison_items or []

    has_missing_core_data = any(
        is_missing_value(current_bescheid.get(key))
        for key in ["amount_due", "tax_period", "municipality"]
    )

    payment_classification = current_bescheid.get("payment_classification", {})
    payment_type = payment_classification.get("type")
    due_dates = current_bescheid.get("due_dates", "Nicht gefunden")

    if has_missing_core_data or payment_type == "Nicht eindeutig bestimmbar":
        status_candidates.append("incomplete")

    has_warning_notice = any(
        notice.get("severity") == "warning"
        and notice.get("source_rule") not in [
            "missing-amount-due",
            "missing-tax-period",
            "payment-type-unknown",
        ]
        for notice in notice_items
    )

    has_important_change = any(
        item.get("importance") == "important"
        for item in change_comparison_items
    )

    has_notice_change = any(
        item.get("importance") == "notice"
        for item in change_comparison_items
    )

    if has_warning_notice or has_important_change:
        status_candidates.append("warning")

    if payment_type in ["Nachzahlung", "Vorauszahlung"] or not is_missing_value(due_dates):
        status_candidates.append("deadline")

    if has_notice_change:
        status_candidates.append("change")

    if not status_candidates:
        status_candidates.append("ok")

    selected_status = min(
        status_candidates,
        key=lambda status: STATUS_PRIORITY.get(status, 99),
    )

    status_definition = STATUS_DEFINITIONS[selected_status].copy()
    status_definition["status"] = selected_status
    status_definition["priority"] = STATUS_PRIORITY[selected_status]

    return status_definition


def build_pdf_report_data(context):
    return {
        "uploaded_file_name": context.get("uploaded_file_name"),
        "summary_items": context.get("summary_items", []),
        "status_indicator": context.get("status_indicator"),
        "notice_items": context.get("notice_items", []),
        "payment_classification": context.get("payment_classification"),
        "calculation_explanation": context.get("calculation_explanation"),
        "advance_payments": context.get("advance_payments", []),
        "previous_bescheid": context.get("previous_bescheid"),
        "period_comparison_notice": context.get("period_comparison_notice"),
        "change_comparison_items": context.get("change_comparison_items", []),
    }


def add_pdf_heading(elements, styles, text):
    elements.append(Paragraph(text, styles["Heading2"]))
    elements.append(Spacer(1, 8))


def add_pdf_paragraph(elements, styles, text):
    if text:
        elements.append(Paragraph(str(text), styles["BodyText"]))
        elements.append(Spacer(1, 6))


def build_pdf_table(rows):
    return Table(rows, hAlign="LEFT")


def create_pdf_report(report_data):
    buffer = BytesIO()
    document = SimpleDocTemplate(buffer, pagesize=A4)
    styles = getSampleStyleSheet()
    elements = []

    elements.append(Paragraph("Gewerbesteuerbescheid-Bericht", styles["Title"]))
    elements.append(Spacer(1, 12))

    add_pdf_paragraph(
        elements,
        styles,
        "Dieser Bericht fasst die automatisch ausgelesenen Bescheiddaten verständlich zusammen.",
    )
    add_pdf_paragraph(
        elements,
        styles,
        "Hinweis: Der Bericht ersetzt keine steuerliche Beratung.",
    )

    if report_data.get("uploaded_file_name"):
        add_pdf_heading(elements, styles, "Datei")
        add_pdf_paragraph(elements, styles, f"Dateiname: {report_data['uploaded_file_name']}")

    if report_data.get("status_indicator"):
        status_indicator = report_data["status_indicator"]
        add_pdf_heading(elements, styles, "Statusanzeige")
        add_pdf_paragraph(elements, styles, f"Status: {status_indicator['label']}")
        add_pdf_paragraph(elements, styles, status_indicator["message"])

    if report_data.get("summary_items"):
        add_pdf_heading(elements, styles, "Zusammenfassung des Bescheids")
        table_rows = [["Information", "Wert"]]
        for item in report_data["summary_items"]:
            table_rows.append([item["label"], item["value"]])
        elements.append(build_pdf_table(table_rows))
        elements.append(Spacer(1, 12))

    if report_data.get("notice_items"):
        add_pdf_heading(elements, styles, "Hinweise")
        for notice in report_data["notice_items"]:
            add_pdf_paragraph(
                elements,
                styles,
                f"{notice['severity_label']}: {notice['title']}",
            )
            add_pdf_paragraph(elements, styles, notice["message"])
            if notice.get("recommendation"):
                add_pdf_paragraph(
                    elements,
                    styles,
                    f"Empfehlung: {notice['recommendation']}",
                )

    if report_data.get("payment_classification"):
        payment_classification = report_data["payment_classification"]
        add_pdf_heading(elements, styles, "Einordnung der Zahlung")
        add_pdf_paragraph(elements, styles, f"Zahlungsart: {payment_classification['type']}")
        add_pdf_paragraph(elements, styles, payment_classification["message"])

    if report_data.get("calculation_explanation"):
        calculation_explanation = report_data["calculation_explanation"]
        add_pdf_heading(elements, styles, "Erklärung der Berechnungslogik")
        if calculation_explanation.get("can_calculate"):
            add_pdf_paragraph(elements, styles, calculation_explanation.get("formula"))
            add_pdf_paragraph(elements, styles, calculation_explanation.get("example"))
        add_pdf_paragraph(elements, styles, calculation_explanation.get("message"))

    if report_data.get("advance_payments"):
        add_pdf_heading(elements, styles, "Vorauszahlungen")
        table_rows = [["Betrag", "Fälligkeit / Zahlungstermin", "Zeitraum / Bezugsjahr", "Art"]]
        for payment in report_data["advance_payments"]:
            table_rows.append(
                [
                    payment["amount"],
                    payment["due_date"],
                    payment["period"],
                    payment["type"],
                ]
            )
        elements.append(build_pdf_table(table_rows))
        elements.append(Spacer(1, 12))

    if report_data.get("previous_bescheid"):
        previous_bescheid = report_data["previous_bescheid"]
        add_pdf_heading(elements, styles, "Vergleich mit Vorjahresbescheid")
        add_pdf_paragraph(
            elements,
            styles,
            f"Vorjahreszeitraum: {previous_bescheid['tax_period']}",
        )
        add_pdf_paragraph(elements, styles, report_data.get("period_comparison_notice"))

    if report_data.get("change_comparison_items"):
        add_pdf_heading(elements, styles, "Änderungsvergleich zum Vorjahr")
        table_rows = [["Wert", "Aktuell", "Vorjahr", "Differenz", "Änderung", "Einordnung"]]
        for item in report_data["change_comparison_items"]:
            table_rows.append(
                [
                    item["label"],
                    item["current_value"],
                    item["previous_value"],
                    item["difference"],
                    item["percentage"],
                    item["change_type"],
                ]
            )
        elements.append(build_pdf_table(table_rows))
        elements.append(Spacer(1, 12))

    add_pdf_heading(elements, styles, "Abschließender Hinweis")
    add_pdf_paragraph(
        elements,
        styles,
        "Dieser PDF-Bericht dient nur der verständlichen Darstellung der ausgelesenen Daten und ersetzt keine steuerliche Beratung.",
    )

    document.build(elements)

    pdf_content = buffer.getvalue()
    buffer.close()

    return pdf_content


def xgewerbesteuer_pdf_report(request):
    report_data = request.session.get(PDF_REPORT_SESSION_KEY)

    if not report_data:
        return HttpResponse(
            "Es liegen keine Daten für einen PDF-Bericht vor. Bitte laden Sie zuerst einen gültigen Bescheid hoch.",
            status=404,
            content_type="text/plain; charset=utf-8",
        )

    pdf_content = create_pdf_report(report_data)

    response = HttpResponse(pdf_content, content_type="application/pdf")
    response["Content-Disposition"] = 'attachment; filename="gewerbesteuerbescheid-bericht.pdf"'

    return response


def xgewerbesteuer_default(request):
    context = {}

    if request.method == "POST":
        uploaded_file = request.FILES.get("bescheid")
        previous_uploaded_file = request.FILES.get("vorjahresbescheid")

        if not uploaded_file:
            context["upload_error"] = "Bitte wählen Sie eine XML-Datei aus."

        else:
            current_result = process_uploaded_bescheid(uploaded_file)

            if not current_result["is_valid"]:
                if current_result["error_type"] == "validation":
                    context["validation_error"] = current_result["message"]
                else:
                    context["upload_error"] = current_result["message"]

            else:
                current_bescheid = current_result["bescheid"]

                context["current_bescheid"] = current_bescheid
                context["uploaded_file_name"] = current_bescheid["file_name"]
                context["uploaded_file_size"] = current_bescheid["file_size"]
                context["summary_items"] = current_bescheid["summary_items"]
                context["calculation_explanation"] = current_bescheid["calculation_explanation"]
                context["advance_payments"] = current_bescheid["advance_payments"]
                context["payment_classification"] = current_bescheid["payment_classification"]
                context["validation_success"] = (
                    "Die Datei wurde erfolgreich geprüft und entspricht dem erwarteten "
                    f"XGewerbesteuer-Schema. Verwendetes Schema: {current_bescheid['schema_name']}"
                )

                if previous_uploaded_file:
                    previous_result = process_uploaded_bescheid(previous_uploaded_file)

                    if not previous_result["is_valid"]:
                        if previous_result["error_type"] == "validation":
                            context["previous_validation_error"] = (
                                f"Vorjahresbescheid: {previous_result['message']}"
                            )
                        else:
                            context["previous_upload_error"] = (
                                f"Vorjahresbescheid: {previous_result['message']}"
                            )

                    else:
                        previous_bescheid = previous_result["bescheid"]

                        context["previous_bescheid"] = previous_bescheid
                        context["period_comparison_notice"] = build_period_comparison_notice(
                            current_bescheid["tax_period"],
                            previous_bescheid["tax_period"],
                        )
                        context["change_comparison_items"] = build_change_comparison(
                            current_bescheid,
                            previous_bescheid,
                        )

                context["notice_items"] = build_notice_area(
                    current_bescheid,
                    context.get("change_comparison_items"),
                )
                context["status_indicator"] = build_status_indicator(
                    current_bescheid,
                    context.get("notice_items"),
                    context.get("change_comparison_items"),
                )
                request.session[PDF_REPORT_SESSION_KEY] = build_pdf_report_data(context)

    return render(request, "xgewerbesteuer_default.html", context)
