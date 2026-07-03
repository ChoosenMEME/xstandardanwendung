"""Orchestrierung der Bescheidverarbeitung."""

from datetime import date
from decimal import Decimal
from xml.etree.ElementTree import ParseError

from defusedxml import ElementTree
from defusedxml.common import DefusedXmlException
from django.db import DatabaseError

from ..calculations import (
    build_calculation_explanation,
    format_euro_value,
    format_german_date,
    is_missing_value,
    normalize_comparison_value,
    parse_date_value,
    parse_decimal_value,
    split_due_date_values,
    split_due_dates,
)
from ..extractors import (
    build_message_type_summary,
    detect_message_type,
    extract_advance_payments,
    extract_amount_due,
    extract_assessment_rate,
    extract_due_dates,
    extract_municipality,
    extract_tax_period,
    extract_trade_tax_assessment_amount,
    is_supported_message_type,
)
from ..models import SavedBescheidUpload
from ..validators import (
    build_validation_issue,
    get_upload_issue,
    validate_xml_against_xsd,
)
from .support_errors import generate_error_id, log_upload_issue


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


def adapt_payment_classification_for_message_type(
    payment_classification,
    message_type_summary,
):
    category = message_type_summary["message_type_category"]

    if category == "interest":
        return {
            "type": "Zinsbescheid",
            "message": (
                "Diese Datei ist ein Zinsbescheid. Eine normale "
                "Gewerbesteuer-Zahlungseinordnung ist nur eingeschraenkt moeglich."
            ),
        }

    if category == "calculation":
        return {
            "type": "Nicht pruefbar",
            "message": (
                "Diese Datei ist eine Gewerbesteuerberechnung. Zahlungs- oder "
                "Faelligkeitsangaben sind fachlich nicht zwingend enthalten."
            ),
        }

    if category == "advance_payment":
        return {
            "type": "Vorauszahlung",
            "message": (
                "Diese Datei ist ein Vorauszahlungsbescheid. Vorauszahlungen "
                "werden getrennt von endgueltigen Festsetzungen angezeigt."
            ),
        }

    return payment_classification


def build_bescheid_data(uploaded_file, root, schema_name):
    message_type = detect_message_type(root)
    message_type_summary = build_message_type_summary(message_type)
    municipality = extract_municipality(root)
    tax_period = extract_tax_period(root)
    amount_due = extract_amount_due(root)
    trade_tax_assessment_amount = extract_trade_tax_assessment_amount(root)
    assessment_rate = extract_assessment_rate(root)
    due_dates = extract_due_dates(root)
    advance_payments = extract_advance_payments(root)
    payment_classification = classify_payment_type(amount_due, advance_payments)
    payment_classification = adapt_payment_classification_for_message_type(
        payment_classification,
        message_type_summary,
    )

    summary_items = [
        {"label": "Nachrichtentyp", "value": message_type_summary["message_type_label"]},
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
        **message_type_summary,
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


def build_invalid_upload_result(
    issue,
    error_type="upload",
    log_level=None,
    exception=None,
):
    """Erzeugt eine einheitliche Fehlerantwort ohne sensible Detaildaten."""
    error_id = generate_error_id()
    detail = issue.as_dict()
    detail["error_id"] = error_id

    if log_level:
        log_upload_issue(error_id, issue.code, level=log_level, exception=exception)

    return {
        "is_valid": False,
        "error_type": error_type,
        "message": issue.message,
        "error_id": error_id,
        "details": [detail],
    }


def process_uploaded_bescheid(uploaded_file):
    upload_issue = get_upload_issue(uploaded_file)

    if upload_issue:
        return build_invalid_upload_result(upload_issue)

    try:
        xml_data = uploaded_file.read()
        root = ElementTree.fromstring(xml_data)

        is_valid, schema_name, schema_error = validate_xml_against_xsd(xml_data)

        if not is_valid:
            issue = build_validation_issue(
                "xsd_validation_error",
                detail=schema_error or "",
            )
            return build_invalid_upload_result(issue, error_type="validation")

        message_type = detect_message_type(root)

        if not is_supported_message_type(message_type):
            issue = build_validation_issue("unsupported_message_type")
            return build_invalid_upload_result(
                issue,
                error_type="unsupported_message_type",
            )

        return {
            "is_valid": True,
            "bescheid": build_bescheid_data(uploaded_file, root, schema_name),
        }

    except DefusedXmlException:
        issue = build_validation_issue("unsafe_xml")
        return build_invalid_upload_result(issue)

    except ParseError:
        issue = build_validation_issue("malformed_xml")
        return build_invalid_upload_result(issue)

    except Exception as error:
        issue = build_validation_issue("read_error")
        return build_invalid_upload_result(
            issue,
            error_type="read_error",
            log_level="error",
            exception=error,
        )


def build_unexpected_import_error_result(exception):
    issue = build_validation_issue("unexpected_import_error")
    return build_invalid_upload_result(
        issue,
        error_type="unexpected_import_error",
        log_level="error",
        exception=exception,
    )


# --- Liquiditaets-Funktionen ---


LIQUIDITY_PERIODS = [
    {"key": "due_now", "label": "Sofort/fällig"},
    {"key": "within_30_days", "label": "Innerhalb von 30 Tagen"},
    {"key": "within_90_days", "label": "Innerhalb von 90 Tagen"},
    {"key": "later", "label": "Später"},
    {"key": "without_date", "label": "Ohne Datumsangabe"},
]

LIQUIDITY_PERIOD_BY_KEY = {period["key"]: period for period in LIQUIDITY_PERIODS}


def classify_liquidity_period(due_date, reference_date):
    parsed_due_date = parse_date_value(due_date)

    if parsed_due_date is None:
        return LIQUIDITY_PERIOD_BY_KEY["without_date"]

    days_until_due = (parsed_due_date - reference_date).days

    if days_until_due <= 0:
        return LIQUIDITY_PERIOD_BY_KEY["due_now"]

    if days_until_due <= 30:
        return LIQUIDITY_PERIOD_BY_KEY["within_30_days"]

    if days_until_due <= 90:
        return LIQUIDITY_PERIOD_BY_KEY["within_90_days"]

    return LIQUIDITY_PERIOD_BY_KEY["later"]


def build_liquidity_payment_item(amount, due_date, payment_type, reference_date):
    parsed_amount = parse_decimal_value(amount)
    parsed_due_date = parse_date_value(due_date)
    period = classify_liquidity_period(parsed_due_date, reference_date)
    notice = None

    if parsed_amount is None:
        impact = "neutral"
        notice = "Der Betrag konnte nicht sicher ausgelesen werden."
    elif parsed_due_date is None and parsed_amount > Decimal("0"):
        impact = "neutral"
        notice = "Es liegt keine verwertbare Fälligkeit vor."
    elif parsed_amount > Decimal("0"):
        impact = "burden"
    elif parsed_amount < Decimal("0"):
        impact = "relief"
        notice = "Dieser Betrag wird als Erstattung oder Entlastung eingeordnet."
    else:
        impact = "neutral"
        notice = "Ein Nullbetrag wird nicht als Liquiditätsbelastung gezählt."

    if parsed_due_date is None and "Fälligkeit" not in (notice or ""):
        date_notice = "Es liegt keine verwertbare Fälligkeit vor."
        notice = f"{notice} {date_notice}" if notice else date_notice

    return {
        "amount": parsed_amount,
        "amount_display": (
            format_euro_value(parsed_amount)
            if parsed_amount is not None
            else None
        ),
        "due_date": parsed_due_date,
        "due_date_display": format_german_date(parsed_due_date),
        "payment_type": payment_type,
        "period_key": period["key"],
        "period_label": period["label"],
        "impact": impact,
        "notice": notice,
    }


def build_liquidity_payment_items(current_bescheid, reference_date):
    items = []
    amount_due = current_bescheid.get("amount_due")
    due_dates = split_due_dates(current_bescheid.get("due_dates"))
    payment_classification = current_bescheid.get("payment_classification", {})
    payment_type = payment_classification.get("type", "Zahlung")

    if not is_missing_value(amount_due):
        if due_dates:
            for due_date in due_dates:
                items.append(
                    build_liquidity_payment_item(
                        amount_due, due_date, payment_type, reference_date,
                    )
                )
        else:
            items.append(
                build_liquidity_payment_item(
                    amount_due, None, payment_type, reference_date,
                )
            )
    elif due_dates:
        for due_date in due_dates:
            items.append(
                build_liquidity_payment_item(
                    None, due_date, payment_type, reference_date,
                )
            )

    for payment in current_bescheid.get("advance_payments", []):
        items.append(
            build_liquidity_payment_item(
                payment.get("amount"),
                payment.get("due_date"),
                payment.get("type", "Vorauszahlung"),
                reference_date,
            )
        )

    return items


def build_liquidity_impact(current_bescheid, reference_date=None):
    if reference_date is None:
        reference_date = date.today()

    items = build_liquidity_payment_items(current_bescheid, reference_date)
    grouped_items = {period["key"]: [] for period in LIQUIDITY_PERIODS}

    for item in items:
        grouped_items[item["period_key"]].append(item)

    groups = []

    for period in LIQUIDITY_PERIODS:
        period_items = grouped_items[period["key"]]
        total_burden = sum(
            (
                item["amount"]
                for item in period_items
                if item["impact"] == "burden" and item["amount"] is not None
            ),
            Decimal("0"),
        )

        groups.append({
            "key": period["key"],
            "label": period["label"],
            "total_burden": format_euro_value(total_burden),
            "items": period_items,
        })

    burden_total = sum(
        (
            item["amount"]
            for item in items
            if item["impact"] == "burden" and item["amount"] is not None
        ),
        Decimal("0"),
    )

    return {
        "reference_date": format_german_date(reference_date),
        "groups": groups,
        "summary": (
            "Summe der möglichen Liquiditätsbelastung aus ausgelesenen positiven Beträgen: "
            f"{format_euro_value(burden_total)}."
        ),
        "has_liquidity_relevant_payments": bool(items),
        "notice": (
            "Diese Übersicht dient der Orientierung und ersetzt "
            "keine Finanz- oder Steuerberatung."
        ),
    }


# --- Kalender-Funktionen ---


def build_calendar_entry(amount, due_date, payment_type):
    parsed_date = parse_date_value(due_date)
    notes = []

    if parsed_date is None:
        notes.append("Fälligkeitstermin nicht verwertbar")
        return {
            "date": None,
            "display_date": None,
            "amount": format_euro_value(amount),
            "payment_type": payment_type or "Zahlungsart nicht eindeutig bestimmbar",
            "label": "Fälligkeit ohne verwertbares Datum",
            "notes": notes,
        }

    if parse_decimal_value(amount) is None:
        notes.append("Betrag nicht gefunden")

    if not payment_type:
        notes.append("Zahlungsart nicht eindeutig bestimmbar")

    display_date = format_german_date(parsed_date)
    display_payment_type = payment_type or "Zahlungsart nicht eindeutig bestimmbar"

    return {
        "date": parsed_date.isoformat(),
        "display_date": display_date,
        "amount": format_euro_value(amount),
        "payment_type": display_payment_type,
        "label": f"{display_payment_type} am {display_date}",
        "notes": notes,
    }


def build_due_date_calendar_entries(current_bescheid):
    entries = []
    due_dates = split_due_date_values(current_bescheid.get("due_dates"))
    payment_classification = current_bescheid.get("payment_classification", {})
    payment_type = payment_classification.get("type")

    for due_date in due_dates:
        entries.append(
            build_calendar_entry(
                current_bescheid.get("amount_due"),
                due_date,
                payment_type,
            )
        )

    for payment in current_bescheid.get("advance_payments", []):
        entries.append(
            build_calendar_entry(
                payment.get("amount"),
                payment.get("due_date"),
                payment.get("type"),
            )
        )

    return entries


def get_calendar_month_label(value):
    parsed_date = parse_date_value(value)

    if parsed_date is None:
        return "Ohne Monat"

    month_names = [
        "Januar",
        "Februar",
        "März",
        "April",
        "Mai",
        "Juni",
        "Juli",
        "August",
        "September",
        "Oktober",
        "November",
        "Dezember",
    ]

    return f"{month_names[parsed_date.month - 1]} {parsed_date.year}"


def group_calendar_entries_by_month(calendar_entries):
    dated_entries = [
        entry
        for entry in calendar_entries
        if entry.get("date")
    ]
    sorted_entries = sorted(
        dated_entries,
        key=lambda entry: entry["date"],
    )
    month_groups = []

    for entry in sorted_entries:
        month_key = entry["date"][:7]

        if not month_groups or month_groups[-1]["key"] != month_key:
            month_groups.append(
                {
                    "key": month_key,
                    "label": get_calendar_month_label(entry["date"]),
                    "entries": [],
                }
            )

        month_groups[-1]["entries"].append(entry)

    return month_groups


def build_due_date_calendar(current_bescheid):
    calendar_entries = build_due_date_calendar_entries(current_bescheid)
    dated_entries = [
        entry
        for entry in calendar_entries
        if entry.get("date")
    ]
    undated_items = [
        entry
        for entry in calendar_entries
        if not entry.get("date")
    ]

    return {
        "has_entries": bool(dated_entries),
        "months": group_calendar_entries_by_month(calendar_entries),
        "undated_items": undated_items,
        "empty_message": (
            ""
            if dated_entries
            else "Für diesen Bescheid wurden keine verwertbaren Fälligkeitstermine gefunden."
        ),
    }


# --- Notice-Funktionen ---


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
    amount_due = current_bescheid.get("amount_due")

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


# --- Status-Funktionen ---


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
    due_dates = current_bescheid.get("due_dates")

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


# --- Saved-Upload-Funktionen ---


def ensure_session_key(request):
    if not request.session.session_key:
        request.session.save()

    return request.session.session_key


def get_saved_uploads_for_request(request):
    if not request.user.is_authenticated:
        return SavedBescheidUpload.objects.none()

    return SavedBescheidUpload.objects.filter(user=request.user)


def build_saved_upload_payload(bescheid, context_data):
    result_keys = [
        "current_bescheid",
        "message_type",
        "message_type_label",
        "message_type_summary",
        "uploaded_file_name",
        "uploaded_file_size",
        "summary_items",
        "calculation_explanation",
        "advance_payments",
        "payment_classification",
        "due_date_calendar",
        "plausibility_check",
        "notice_items",
        "status_indicator",
    ]

    def db_text_value(value):
        normalized_value = normalize_comparison_value(value)
        return normalized_value or ""

    return {
        "file_name": bescheid.get("file_name", ""),
        "file_size": bescheid.get("file_size") or 0,
        "municipality": db_text_value(bescheid.get("municipality")),
        "tax_period": db_text_value(bescheid.get("tax_period")),
        "amount_due": db_text_value(bescheid.get("amount_due")),
        "payment_type": db_text_value(
            bescheid.get("payment_classification", {}).get("type")
        ),
        "trade_tax_assessment_amount": db_text_value(
            bescheid.get("trade_tax_assessment_amount")
        ),
        "assessment_rate": db_text_value(bescheid.get("assessment_rate")),
        "due_dates": db_text_value(bescheid.get("due_dates")),
        "advance_payments": bescheid.get("advance_payments", []),
        "summary_items": context_data.get("summary_items", []),
        "result_data": {
            key: context_data.get(key)
            for key in result_keys
            if key in context_data
        },
    }


def create_saved_upload(request, bescheid, context_data):
    session_key = ensure_session_key(request)
    payload = build_saved_upload_payload(bescheid, context_data)

    return SavedBescheidUpload.objects.create(
        session_key=session_key,
        user=request.user,
        **payload,
    )


def prepare_download_sessions(request, context):
    from .export import (
        ICS_EXPORT_SESSION_KEY,
        PDF_REPORT_SESSION_KEY,
        build_pdf_report_data,
        create_ics_export,
    )

    # PDF und CSV teilen sich denselben Session-Datensatz (siehe export.py).
    report_data = build_pdf_report_data(context)
    request.session[PDF_REPORT_SESSION_KEY] = report_data
    request.session.pop(ICS_EXPORT_SESSION_KEY, None)

    due_date_calendar = context.get("due_date_calendar")

    if due_date_calendar:
        ics_content = create_ics_export(due_date_calendar)

        if ics_content:
            request.session[ICS_EXPORT_SESSION_KEY] = ics_content
            context["has_ics_export"] = True
        else:
            context.pop("has_ics_export", None)
