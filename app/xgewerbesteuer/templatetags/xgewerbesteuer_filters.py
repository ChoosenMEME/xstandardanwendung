"""Template-Filter fuer Anzeigelogik."""

from django import template

from ..calculations import (
    format_euro_value,
    format_german_date,
    parse_decimal_value,
)
from ..services.glossary import get_glossary_definition

register = template.Library()


@register.filter
def default_display(value):
    """Zeigt 'Nicht gefunden' fuer fehlende Werte an."""
    if value is None or value == "":
        return "Nicht gefunden"

    return value


@register.filter
def format_currency(value):
    """Formatiert Dezimalwert als '1.234,56 EUR'."""
    return format_euro_value(value)


@register.filter
def format_date_de(value):
    """Formatiert Datum als 'TT.MM.JJJJ'."""
    return format_german_date(value)


@register.filter
def format_percent(value):
    """Formatiert Dezimalwert als '12,5 %'."""
    parsed = parse_decimal_value(str(value)) if not isinstance(value, type(None)) else None

    if parsed is None:
        return "Nicht verfügbar"

    formatted = str(parsed).replace(".", ",")

    return f"{formatted} %"


@register.inclusion_tag("xgewerbesteuer/partials/term_help.html")
def term_help(label):
    """Rendert eine zentrale Begriffserklaerung, falls das Label bekannt ist."""
    return {
        "definition": get_glossary_definition(label),
    }
