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

    return render(request, "xgewerbesteuer_default.html", context)
