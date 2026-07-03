"""Vorjahresvergleich, Mehrjahresvergleich und historische Entwicklung."""

import re
from decimal import Decimal

from .calculations import (
    format_decimal_value,
    format_signed_decimal_value,
    is_missing_value,
    normalize_comparison_value,
    parse_decimal_value,
    split_due_dates,
)


def build_period_comparison_notice(current_tax_period, previous_tax_period):
    if is_missing_value(current_tax_period) or is_missing_value(previous_tax_period):
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


def build_message_type_comparison_notice(current_bescheid, previous_bescheid):
    current_type = current_bescheid.get("message_type")
    previous_type = previous_bescheid.get("message_type")
    current_label = current_bescheid.get("message_type_label")
    previous_label = previous_bescheid.get("message_type_label")

    if current_type or previous_type:
        if current_type != previous_type:
            return (
                "Die hochgeladenen Dateien enthalten unterschiedliche Nachrichtentypen "
                f"({current_label} und {previous_label}). Ein direkter fachlicher "
                "Vergleich ist nur eingeschraenkt moeglich."
            )

        if current_bescheid.get("supports_comparison") is False:
            return (
                f"Der Nachrichtentyp {current_label} ist fachlich nicht fuer einen "
                "direkten Vorjahresvergleich vorgesehen."
            )

    return None


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
    if is_missing_value(current_value) or is_missing_value(previous_value):
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
    if build_message_type_comparison_notice(current_bescheid, previous_bescheid):
        return []

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
        current_value = current_bescheid.get(field["key"])
        previous_value = previous_bescheid.get(field["key"])

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


def extract_sort_year(tax_period):
    if is_missing_value(tax_period):
        return 9999

    match = re.search(r"\b(19|20)\d{2}\b", str(tax_period))

    if not match:
        return 9999

    return int(match.group(0))


def format_advance_payments_for_comparison(advance_payments):
    if not advance_payments:
        return None

    formatted_payments = []

    for payment in advance_payments:
        amount = normalize_comparison_value(payment.get("amount"))
        due_date = normalize_comparison_value(payment.get("due_date"))
        period = normalize_comparison_value(payment.get("period"))
        payment_type = normalize_comparison_value(payment.get("type"))
        formatted_payments.append(
            f"{amount} ({payment_type}, Fälligkeit: {due_date}, Zeitraum: {period})"
        )

    return "; ".join(formatted_payments)


def build_multi_bescheid_record(bescheid):
    """Build one normalized row for the multi-year comparison table."""
    payment_classification = bescheid.get("payment_classification", {})
    record = {
        "file_name": normalize_comparison_value(bescheid.get("file_name")),
        "message_type": normalize_comparison_value(bescheid.get("message_type")),
        "message_type_label": normalize_comparison_value(
            bescheid.get("message_type_label")
        ),
        "tax_period": normalize_comparison_value(bescheid.get("tax_period")),
        "municipality": normalize_comparison_value(bescheid.get("municipality")),
        "amount_due": normalize_comparison_value(bescheid.get("amount_due")),
        "payment_type": normalize_comparison_value(payment_classification.get("type")),
        "trade_tax_assessment_amount": normalize_comparison_value(
            bescheid.get("trade_tax_assessment_amount")
        ),
        "assessment_rate": normalize_comparison_value(bescheid.get("assessment_rate")),
        "due_dates": normalize_comparison_value(bescheid.get("due_dates")),
        "advance_payments": format_advance_payments_for_comparison(
            bescheid.get("advance_payments", [])
        ),
        "notes": [],
        "duplicate_tax_period": False,
        "css_class": "",
    }

    missing_fields = [
        label
        for label, value in [
            ("Steuerjahr / Zeitraum", record["tax_period"]),
            ("Gemeinde / Kommune", record["municipality"]),
            ("Zahlbetrag", record["amount_due"]),
            ("Gewerbesteuermessbetrag", record["trade_tax_assessment_amount"]),
            ("Hebesatz", record["assessment_rate"]),
        ]
        if is_missing_value(value)
    ]

    if missing_fields:
        record["notes"].append("Fehlende Werte: " + ", ".join(missing_fields))

    if record["payment_type"] == "Nicht eindeutig bestimmbar":
        record["notes"].append("Zahlungsart fachlich nicht eindeutig zuordenbar.")

    return record


def sort_bescheid_records_chronologically(records):
    return sorted(
        records,
        key=lambda record: (
            extract_sort_year(record.get("tax_period")),
            record.get("tax_period") or "",
            record.get("file_name") or "",
        ),
    )


def group_bescheide_by_tax_period(records):
    groups = {}

    for record in records:
        tax_period = record.get("tax_period")
        groups.setdefault(tax_period, []).append(record)

    return groups


def build_multi_bescheid_comparison(bescheide):
    records = [
        build_multi_bescheid_record(bescheid)
        for bescheid in bescheide
    ]
    records = sort_bescheid_records_chronologically(records)

    if len(records) < 2:
        return None

    grouped_records = group_bescheide_by_tax_period(records)
    duplicate_tax_periods = sorted(
        tax_period
        for tax_period, period_records in grouped_records.items()
        if not is_missing_value(tax_period) and len(period_records) > 1
    )

    for record in records:
        if record["tax_period"] in duplicate_tax_periods:
            record["duplicate_tax_period"] = True
            record["css_class"] = "multi-comparison-duplicate"
            record["notes"].append(
                "Mehrere Bescheide für denselben Zeitraum hochgeladen."
            )

    notices = []

    if duplicate_tax_periods:
        notices.append(
            "Mehrere Bescheide enthalten denselben Steuerzeitraum: "
            + ", ".join(duplicate_tax_periods)
            + "."
        )

    if any(record["notes"] for record in records):
        notices.append(
            "Einige Angaben fehlen oder konnten nicht eindeutig zugeordnet werden."
        )

    message_types = {
        record["message_type"]
        for record in records
        if not is_missing_value(record.get("message_type"))
    }

    if len(message_types) > 1:
        notices.append(
            "Die hochgeladenen Dateien enthalten unterschiedliche Nachrichtentypen. "
            "Ein direkter fachlicher Vergleich ist nur eingeschraenkt moeglich."
        )

    return {
        "valid_count": len(records),
        "records": records,
        "duplicate_tax_periods": duplicate_tax_periods,
        "notices": notices,
    }


def calculate_historical_change(current_value, previous_value):
    current_decimal = parse_decimal_value(current_value)
    previous_decimal = parse_decimal_value(previous_value)

    if current_decimal is None or previous_decimal is None:
        return "Nicht berechenbar"

    return format_signed_decimal_value(current_decimal - previous_decimal)


def get_main_due_date(due_dates):
    parsed_due_dates = split_due_dates(due_dates)

    if not parsed_due_dates:
        return None

    return parsed_due_dates[0]


def build_historical_development_row(record, previous_record=None):
    notes = list(record.get("notes", []))

    if previous_record is None:
        amount_due_change = "Nicht berechenbar"
        trade_tax_assessment_amount_change = "Nicht berechenbar"
        assessment_rate_change = "Nicht berechenbar"
    else:
        amount_due_change = calculate_historical_change(
            record.get("amount_due"),
            previous_record.get("amount_due"),
        )
        trade_tax_assessment_amount_change = calculate_historical_change(
            record.get("trade_tax_assessment_amount"),
            previous_record.get("trade_tax_assessment_amount"),
        )
        assessment_rate_change = calculate_historical_change(
            record.get("assessment_rate"),
            previous_record.get("assessment_rate"),
        )

    main_due_date = get_main_due_date(record.get("due_dates"))

    if is_missing_value(main_due_date):
        notes.append("Wichtigste Fälligkeit nicht gefunden.")

    return {
        "tax_period": record.get("tax_period"),
        "amount_due": record.get("amount_due"),
        "amount_due_change": amount_due_change,
        "trade_tax_assessment_amount": record.get(
            "trade_tax_assessment_amount",
        ),
        "trade_tax_assessment_amount_change": trade_tax_assessment_amount_change,
        "assessment_rate": record.get("assessment_rate"),
        "assessment_rate_change": assessment_rate_change,
        "main_due_date": main_due_date,
        "notes": notes,
    }


def _compute_bar_widths(rows, key):
    parsed = []

    for row in rows:
        value = parse_decimal_value(row.get(key))
        parsed.append((row, abs(value) if value is not None else None))

    max_value = max(
        (v for _, v in parsed if v is not None),
        default=Decimal("0"),
    )

    if max_value == Decimal("0"):
        max_value = Decimal("1")

    return [
        max(int((v / max_value * Decimal("100")).to_integral_value()), 1)
        if v is not None else 0
        for _, v in parsed
    ]


def build_historical_chart_data(rows):
    numeric_rows = []

    for row in rows:
        parsed_amount = parse_decimal_value(row.get("amount_due"))

        if parsed_amount is not None:
            numeric_rows.append((row, abs(parsed_amount)))

    if not numeric_rows:
        return []

    max_amount = max(amount for row, amount in numeric_rows)

    if max_amount == Decimal("0"):
        max_amount = Decimal("1")

    chart_data = []

    for row, amount in numeric_rows:
        width_percent = int((amount / max_amount * Decimal("100")).to_integral_value())
        chart_data.append(
            {
                "tax_period": row["tax_period"],
                "amount_due": row["amount_due"],
                "width_percent": max(width_percent, 1),
            }
        )

    return chart_data


def build_multi_metric_chart_data(rows):
    if len(rows) < 2:
        return None

    amount_widths = _compute_bar_widths(rows, "amount_due")
    messbetrag_widths = _compute_bar_widths(rows, "trade_tax_assessment_amount")
    rate_widths = _compute_bar_widths(rows, "assessment_rate")

    chart_rows = []

    for index, row in enumerate(rows):
        chart_rows.append({
            "tax_period": row.get("tax_period", ""),
            "amount_due": row.get("amount_due"),
            "amount_due_width": amount_widths[index],
            "trade_tax_assessment_amount": row.get(
                "trade_tax_assessment_amount",
            ),
            "messbetrag_width": messbetrag_widths[index],
            "assessment_rate": row.get("assessment_rate"),
            "rate_width": rate_widths[index],
        })

    return chart_rows


def build_historical_development(records):
    sorted_records = sort_bescheid_records_chronologically(records)

    if len(sorted_records) < 2:
        return None

    rows = []

    for index, record in enumerate(sorted_records):
        previous_record = sorted_records[index - 1] if index > 0 else None
        rows.append(build_historical_development_row(record, previous_record))

    return {
        "has_history": True,
        "year_count": len(rows),
        "rows": rows,
        "chart_data": build_historical_chart_data(rows),
        "multi_metric_chart": build_multi_metric_chart_data(rows),
        "notice": (
            "Diese Übersicht zeigt die Entwicklung der ausgelesenen Werte über "
            "mehrere Jahre. Sie dient der Orientierung und ersetzt keine steuerliche "
            "Beratung."
        ),
    }
