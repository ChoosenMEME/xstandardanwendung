"""Dezimalformatierung, Formeln und Plausibilitaetspruefung."""

from datetime import date, datetime
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP


# Kleine Rundungsdifferenzen zwischen Bescheid und eigener Nachrechnung sollen
# keine Warnung erzeugen, weil Beträge in Bescheiden auf Cent gerundet sind.
PLAUSIBILITY_TOLERANCE = Decimal("0.02")


def parse_decimal_value(value):
    if value is None or value == "":
        return None

    cleaned_value = (
        str(value).replace("EUR", "")
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


def parse_date_value(value):
    if isinstance(value, date):
        return value

    if value is None or value == "":
        return None

    cleaned_value = str(value).strip()

    for date_format in ["%Y-%m-%d", "%d.%m.%Y"]:
        try:
            return datetime.strptime(cleaned_value, date_format).date()
        except ValueError:
            continue

    return None


def format_german_date(value):
    parsed_date = parse_date_value(value)

    if parsed_date is None:
        return None

    return parsed_date.strftime("%d.%m.%Y")


def format_euro_value(value):
    parsed_value = value if isinstance(value, Decimal) else parse_decimal_value(value)

    if parsed_value is None:
        return "Betrag nicht gefunden"

    rounded_value = parsed_value.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
    formatted_value = f"{rounded_value:,.2f}"
    formatted_value = formatted_value.replace(",", "X").replace(".", ",").replace("X", ".")

    return f"{formatted_value} EUR"


def split_due_dates(due_dates):
    if due_dates is None or due_dates == "":
        return []

    return [
        due_date.strip()
        for due_date in str(due_dates).split(",")
        if due_date.strip()
    ]


def split_due_date_values(due_dates):
    return split_due_dates(due_dates)


def is_missing_value(value):
    return value is None or value == ""


def normalize_comparison_value(value):
    if is_missing_value(value):
        return None

    return value


def format_signed_decimal_value(value):
    if value > Decimal("0"):
        return f"+{format_decimal_value(value)}"

    return format_decimal_value(value)


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


def calculate_expected_trade_tax(trade_tax_assessment_amount, assessment_rate):
    parsed_trade_tax_assessment_amount = parse_decimal_value(trade_tax_assessment_amount)
    parsed_assessment_rate = parse_decimal_value(assessment_rate)

    if parsed_trade_tax_assessment_amount is None or parsed_assessment_rate is None:
        return None

    return parsed_trade_tax_assessment_amount * parsed_assessment_rate / Decimal("100")


def compare_plausibility_amounts(
    actual_amount,
    expected_amount,
    tolerance=PLAUSIBILITY_TOLERANCE,
):
    parsed_actual_amount = parse_decimal_value(actual_amount)

    if parsed_actual_amount is None or expected_amount is None:
        return {
            "status": "not_checkable",
            "label": "Nicht prüfbar",
            "difference": None,
        }

    difference = parsed_actual_amount - expected_amount

    if abs(difference) <= tolerance:
        return {
            "status": "plausible",
            "label": "Plausibel",
            "difference": difference,
        }

    return {
        "status": "warning",
        "label": "Warnung / Abweichung",
        "difference": difference,
    }


def build_plausibility_item(label, value):
    return {
        "label": label,
        "value": normalize_comparison_value(value),
    }


def build_plausibility_check(current_bescheid):
    actual_amount = current_bescheid.get("amount_due")
    trade_tax_assessment_amount = current_bescheid.get("trade_tax_assessment_amount")
    assessment_rate = current_bescheid.get("assessment_rate")
    expected_amount = calculate_expected_trade_tax(
        trade_tax_assessment_amount,
        assessment_rate,
    )
    parsed_actual_amount = parse_decimal_value(actual_amount)
    items = [
        build_plausibility_item("Ausgelesener Zahlbetrag", actual_amount),
        build_plausibility_item(
            "Gewerbesteuermessbetrag",
            trade_tax_assessment_amount,
        ),
        build_plausibility_item("Hebesatz", assessment_rate),
    ]
    formula = "Gewerbesteuer = Gewerbesteuermessbetrag × Hebesatz / 100"

    missing_labels = [
        item["label"]
        for item in items
        if is_missing_value(item["value"])
    ]

    if missing_labels:
        return {
            "status": "not_checkable",
            "css_class": "plausibility-status--not-checkable",
            "label": "Nicht prüfbar",
            "message": (
                "Die Plausibilitätsprüfung kann nicht durchgeführt werden, weil "
                + ", ".join(missing_labels)
                + " nicht vorliegt."
            ),
            "expected_amount": "Nicht berechenbar",
            "actual_amount": normalize_comparison_value(actual_amount),
            "difference": "Nicht berechenbar",
            "formula": formula,
            "items": items,
        }

    if parsed_actual_amount is None or expected_amount is None:
        return {
            "status": "not_checkable",
            "css_class": "plausibility-status--not-checkable",
            "label": "Nicht prüfbar",
            "message": (
                "Die Plausibilitätsprüfung kann nicht durchgeführt werden, weil "
                "mindestens ein Wert rechnerisch nicht verwertbar ist."
            ),
            "expected_amount": "Nicht berechenbar",
            "actual_amount": normalize_comparison_value(actual_amount),
            "difference": "Nicht berechenbar",
            "formula": formula,
            "items": items,
        }

    if (
        parsed_actual_amount is not None
        and (parsed_actual_amount < Decimal("0") or expected_amount < Decimal("0"))
    ):
        return {
            "status": "not_checkable",
            "css_class": "plausibility-status--not-checkable",
            "label": "Nicht prüfbar",
            "message": (
                "Negative Beträge werden neutral angezeigt. Eine rechnerische "
                "Formelwarnung wird dafür nicht automatisch erzeugt."
            ),
            "expected_amount": format_euro_value(expected_amount),
            "actual_amount": format_euro_value(parsed_actual_amount),
            "difference": "Nicht berechenbar",
            "formula": formula,
            "items": items,
        }

    comparison = compare_plausibility_amounts(actual_amount, expected_amount)
    difference = comparison["difference"]
    status = comparison["status"]

    if status == "plausible":
        message = (
            "Der ausgelesene Zahlbetrag passt innerhalb der Rundungstoleranz "
            "zur rechnerischen Grundformel."
        )
        css_class = "plausibility-status--plausible"
    elif status == "warning":
        message = (
            "Der ausgelesene Zahlbetrag weicht von der rechnerischen Grundformel ab. "
            "Bitte prüfen Sie die Angaben im Bescheid fachlich."
        )
        css_class = "plausibility-status--warning"
    else:
        message = "Die Werte konnten nicht rechnerisch geprüft werden."
        css_class = "plausibility-status--not-checkable"

    return {
        "status": status,
        "css_class": css_class,
        "label": comparison["label"],
        "message": message,
        "expected_amount": format_euro_value(expected_amount),
        "actual_amount": format_euro_value(parsed_actual_amount),
        "difference": (
            format_euro_value(difference)
            if difference is not None
            else "Nicht berechenbar"
        ),
        "formula": formula,
        "items": items,
    }
