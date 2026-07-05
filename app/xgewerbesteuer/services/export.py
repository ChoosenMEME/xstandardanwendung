"""PDF-, CSV- und ICS-Export fuer Bescheiddaten."""

import csv
import hashlib
from datetime import datetime, timezone
from io import BytesIO, StringIO
from xml.sax.saxutils import escape

from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table

from ..calculations import (
    format_german_date,
    parse_date_value,
    parse_decimal_value,
    split_due_dates,
)


PDF_REPORT_SESSION_KEY = "xgewerbesteuer_pdf_report"
# CSV-Export nutzt denselben Datensatz wie der PDF-Bericht. Ein gemeinsamer
# Session-Key vermeidet die doppelte Datenhaltung pro Session (#318).
CSV_EXPORT_SESSION_KEY = PDF_REPORT_SESSION_KEY
ICS_EXPORT_SESSION_KEY = "xgewerbesteuer_ics_export"

CSV_EXPORT_COLUMNS = [
    "Datensatztyp",
    "Nachrichtentyp",
    "Steuerjahr / Erhebungszeitraum",
    "Gemeinde / Kommune",
    "Zahlbetrag",
    "Gewerbesteuermessbetrag",
    "Hebesatz",
    "Fälligkeit",
    "Zahlungsart",
    "Hinweis / Status",
    "Beschreibung",
    "Betrag",
    "Zeitraum / Bezugsjahr",
    "Vergleichswert Vorjahr",
    "Differenz",
    "Prozentuale Änderung",
    "Einordnung",
]


# --- PDF ---


def build_pdf_report_data(context):
    return {
        "uploaded_file_name": context.get("uploaded_file_name"),
        "message_type": context.get("message_type"),
        "message_type_label": context.get("message_type_label"),
        "message_type_summary": context.get("message_type_summary"),
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
    # Paragraph interpretiert seinen Text als Markup. Dateinamen und aus dem
    # XML ausgelesene Werte sind nutzerkontrolliert; ohne Escaping fuehrt ein
    # "<" im Dateinamen zu einem Absturz und Tags wie <b> zu Markup-Injection.
    if text:
        elements.append(Paragraph(escape(str(text)), styles["BodyText"]))
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


# --- CSV ---


def normalize_csv_value(value):
    if value is None:
        return ""

    text = str(value)

    # Werte aus dem hochgeladenen XML koennen mit Formelzeichen beginnen und
    # wuerden in Tabellenkalkulationen als Formel ausgefuehrt (CSV-Injection).
    # Echte Zahlen mit Vorzeichen ("-25,00", "+430") bleiben unveraendert;
    # nur nicht als Zahl lesbare Werte werden mit einem Apostroph
    # neutralisiert.
    if text[:1] in ("=", "@", "\t") or (
        text[:1] in ("-", "+") and parse_decimal_value(text) is None
    ):
        return f"'{text}"

    return text


def get_summary_value(report_data, label):
    for item in report_data.get("summary_items", []):
        if item.get("label") == label:
            return item.get("value", "")

    return ""


def build_base_csv_row(report_data):
    return {
        "Nachrichtentyp": get_summary_value(report_data, "Nachrichtentyp"),
        "Steuerjahr / Erhebungszeitraum": get_summary_value(
            report_data,
            "Steuerjahr / Erhebungszeitraum",
        ),
        "Gemeinde / Kommune": get_summary_value(report_data, "Gemeinde / Kommune"),
        "Zahlbetrag": get_summary_value(report_data, "Zahlbetrag"),
        "Gewerbesteuermessbetrag": get_summary_value(
            report_data,
            "Gewerbesteuermessbetrag",
        ),
        "Hebesatz": get_summary_value(report_data, "Hebesatz"),
        "Fälligkeit": get_summary_value(report_data, "Fälligkeiten"),
        "Zahlungsart": get_summary_value(report_data, "Zahlungsart"),
    }


def build_csv_export_rows(report_data):
    rows = []
    base_row = build_base_csv_row(report_data)

    summary_row = base_row.copy()
    summary_row["Datensatztyp"] = "Zusammenfassung"

    status_indicator = report_data.get("status_indicator")
    if status_indicator:
        summary_row["Hinweis / Status"] = status_indicator.get("label", "")
        summary_row["Beschreibung"] = status_indicator.get("message", "")

    rows.append(summary_row)

    if status_indicator:
        status_row = base_row.copy()
        status_row["Datensatztyp"] = "Status"
        status_row["Hinweis / Status"] = status_indicator.get("label", "")
        status_row["Beschreibung"] = status_indicator.get("message", "")
        rows.append(status_row)

    for due_date in split_due_dates(base_row.get("Fälligkeit")):
        due_date_row = base_row.copy()
        due_date_row["Datensatztyp"] = "Fälligkeit"
        due_date_row["Fälligkeit"] = due_date
        rows.append(due_date_row)

    for notice in report_data.get("notice_items", []):
        notice_row = base_row.copy()
        notice_row["Datensatztyp"] = "Hinweis"
        notice_row["Hinweis / Status"] = (
            f"{notice.get('severity_label', '')}: {notice.get('title', '')}"
        ).strip()
        description = notice.get("message", "")

        if notice.get("recommendation"):
            description = f"{description} Empfehlung: {notice['recommendation']}"

        notice_row["Beschreibung"] = description
        rows.append(notice_row)

    for payment in report_data.get("advance_payments", []):
        payment_row = base_row.copy()
        payment_row["Datensatztyp"] = "Vorauszahlung"
        payment_row["Betrag"] = payment.get("amount", "")
        payment_row["Fälligkeit"] = payment.get("due_date", "")
        payment_row["Zeitraum / Bezugsjahr"] = payment.get("period", "")
        payment_row["Zahlungsart"] = payment.get("type", "")
        rows.append(payment_row)

    for item in report_data.get("change_comparison_items", []):
        comparison_row = base_row.copy()
        comparison_row["Datensatztyp"] = "Vorjahresvergleich"
        comparison_row["Beschreibung"] = item.get("label", "")
        comparison_row["Betrag"] = item.get("current_value", "")
        comparison_row["Vergleichswert Vorjahr"] = item.get("previous_value", "")
        comparison_row["Differenz"] = item.get("difference", "")
        comparison_row["Prozentuale Änderung"] = item.get("percentage", "")
        comparison_row["Einordnung"] = item.get("change_type", "")
        comparison_row["Hinweis / Status"] = item.get("importance_label", "")
        rows.append(comparison_row)

    return rows


def create_csv_export(report_data):
    output = StringIO()
    writer = csv.DictWriter(
        output,
        fieldnames=CSV_EXPORT_COLUMNS,
        delimiter=";",
        lineterminator="\n",
    )

    writer.writeheader()

    for row in build_csv_export_rows(report_data):
        writer.writerow(
            {
                column: normalize_csv_value(row.get(column, ""))
                for column in CSV_EXPORT_COLUMNS
            }
        )

    return output.getvalue()


# --- ICS ---


def escape_ics_text(value):
    """Escape text according to RFC 5545 for safe use in ICS fields."""
    if value is None:
        return ""

    text = str(value).replace("\\", "\\\\")
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    text = text.replace("\n", "\\n")
    text = text.replace(";", "\\;").replace(",", "\\,")

    return text


def format_ics_date(value):
    parsed_date = parse_date_value(value)

    if parsed_date is None:
        return None

    return parsed_date.strftime("%Y%m%d")


def format_ics_timestamp(value):
    return value.strftime("%Y%m%dT%H%M%SZ")


def fold_ics_line(line, limit=75):
    """Faltet lange Zeilen gemaess RFC 5545 (max. 75 Oktette pro Zeile).

    Folgezeilen beginnen mit einem Leerzeichen. Gefaltet wird auf Basis der
    UTF-8-Oktettlaenge, ohne Mehrbyte-Zeichen zu zerschneiden.
    """
    encoded = line.encode("utf-8")

    if len(encoded) <= limit:
        return [line]

    folded_lines = []
    current_chars = []
    current_length = 0
    # Folgezeilen verlieren ein Oktett an das fuehrende Leerzeichen.
    current_limit = limit

    for character in line:
        character_length = len(character.encode("utf-8"))

        if current_length + character_length > current_limit:
            folded_lines.append("".join(current_chars))
            current_chars = [" "]
            current_length = 1
            current_limit = limit

        current_chars.append(character)
        current_length += character_length

    folded_lines.append("".join(current_chars))

    return folded_lines


def build_ics_event(entry, index, timestamp):
    ics_date = format_ics_date(entry.get("date"))

    if ics_date is None:
        return None

    payment_type = entry.get("payment_type") or "Zahlungstermin"
    amount = entry.get("amount") or "Betrag nicht gefunden"
    display_date = entry.get("display_date") or format_german_date(entry.get("date"))
    uid_source = "|".join([ics_date, str(index), payment_type, amount])
    uid_hash = hashlib.sha256(uid_source.encode("utf-8")).hexdigest()[:16]
    summary = f"Gewerbesteuer: {payment_type}"
    description = "\n".join(
        [
            f"Fälligkeit: {display_date}",
            f"Betrag: {amount}",
            f"Zahlungsart: {payment_type}",
            "Diese Frist wurde aus den validierten Bescheiddaten ermittelt.",
        ]
    )

    return [
        "BEGIN:VEVENT",
        (
            f"UID:xgewerbesteuer-frist-{ics_date}-{index}-{uid_hash}"
            "@xgewerbesteuer-assistent.local"
        ),
        # DTSTAMP ist laut RFC 5545 der Erstellungszeitpunkt der Datei,
        # nicht das Datum des Termins.
        f"DTSTAMP:{format_ics_timestamp(timestamp)}",
        f"DTSTART;VALUE=DATE:{ics_date}",
        f"SUMMARY:{escape_ics_text(summary)}",
        f"DESCRIPTION:{escape_ics_text(description)}",
        "END:VEVENT",
    ]


def create_ics_export(due_date_calendar):
    """Create an ICS calendar from validated due-date calendar entries."""
    events = []
    timestamp = datetime.now(timezone.utc)

    for month in due_date_calendar.get("months", []):
        for entry in month.get("entries", []):
            event = build_ics_event(entry, len(events) + 1, timestamp)

            if event:
                events.append(event)

    if not events:
        return None

    lines = [
        "BEGIN:VCALENDAR",
        "VERSION:2.0",
        "PRODID:-//XGewerbesteuer Assistent//Fristenexport//DE",
        "CALSCALE:GREGORIAN",
        "METHOD:PUBLISH",
    ]

    for event in events:
        lines.extend(event)

    lines.append("END:VCALENDAR")

    folded_lines = []

    for line in lines:
        folded_lines.extend(fold_ics_line(line))

    return "\r\n".join(folded_lines) + "\r\n"
