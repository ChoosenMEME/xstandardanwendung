"""Regressionstests fuer XML-Upload, Extraktion und Validierung."""

import csv
from decimal import Decimal
from io import StringIO
from pathlib import Path
from unittest.mock import patch

from defusedxml import ElementTree
from django.core.files.uploadedfile import SimpleUploadedFile
from django.db import DatabaseError
from django.template.loader import render_to_string
from django.test import SimpleTestCase, TestCase
from django.urls import reverse

from xgewerbesteuer.models import SavedBescheidUpload
from xgewerbesteuer.calculations import (
    PLAUSIBILITY_TOLERANCE,
    build_plausibility_check,
    calculate_expected_trade_tax,
    compare_plausibility_amounts,
    split_due_date_values,
)
from xgewerbesteuer.comparisons import (
    build_change_comparison,
    build_historical_chart_data,
    build_historical_development,
    build_historical_development_row,
    build_message_type_comparison_notice,
    build_multi_bescheid_comparison,
    build_multi_bescheid_record,
    build_multi_bescheid_upload_errors,
    build_period_comparison_notice,
    calculate_historical_change,
    classify_change_importance,
    compare_decimal_values,
    compare_text_values,
    group_bescheide_by_tax_period,
    sort_bescheid_records_chronologically,
)
from xgewerbesteuer.extractors import (
    clean_text,
    detect_message_type,
    extract_amount_due,
    extract_assessment_rate,
    extract_advance_payments,
    extract_due_dates,
    extract_municipality,
    extract_tax_period,
    extract_trade_tax_assessment_amount,
    get_local_name,
)
from xgewerbesteuer.calculations import (
    format_euro_value,
    parse_decimal_value,
)
from xgewerbesteuer.services.bescheid import (
    build_bescheid_data,
    build_due_date_calendar,
    build_due_date_calendar_entries,
    build_liquidity_impact,
    build_notice_area,
    build_status_indicator,
    classify_liquidity_period,
    classify_payment_type,
    group_calendar_entries_by_month,
    process_uploaded_bescheid,
)
from xgewerbesteuer.services.support_errors import generate_error_id
from xgewerbesteuer.services.export import (
    CSV_EXPORT_COLUMNS,
    CSV_EXPORT_SESSION_KEY,
    ICS_EXPORT_SESSION_KEY,
    PDF_REPORT_SESSION_KEY,
    build_ics_event,
    create_csv_export,
    create_ics_export,
    escape_ics_text,
    format_ics_date,
)
from xgewerbesteuer.services.privacy import (
    anonymize_result_context,
    anonymize_value,
    is_sensitive_label,
)
from xgewerbesteuer.validators import (
    MAX_UPLOAD_SIZE_BYTES,
    UploadValidationIssue,
    get_upload_issue,
    validate_xml_against_xsd,
)


FIXTURES_DIR = Path(__file__).resolve().parent / "fixtures"
VALID_BESCHEID_FIXTURE = (
    FIXTURES_DIR
    / "GEWST-0010-12345678-1234567890000-2023-01-15_"
    "00000000-0000-0000-0000-000000000103.xml"
)
PREVIOUS_BESCHEID_FIXTURE = (
    FIXTURES_DIR
    / "GEWST-0010-12345678-1234567890000-2022-01-15_"
    "00000000-0000-0000-0000-000000000102.xml"
)
ADVANCE_PAYMENT_FIXTURE = (
    FIXTURES_DIR
    / "GEWST-0003-12345678-1234567890000-2023-01-15_"
    "00000000-0000-0000-0000-000000000033.xml"
)
ASSESSMENT_FIXTURE = (
    FIXTURES_DIR
    / "GEWST-0001-12345678-1234567890000-2023-01-15_"
    "00000000-0000-0000-0000-000000000013.xml"
)
INTEREST_FIXTURE = (
    FIXTURES_DIR
    / "GEWST-0002-12345678-1234567890000-2023-01-15_"
    "00000000-0000-0000-0000-000000000023.xml"
)
CALCULATION_FIXTURE = (
    FIXTURES_DIR
    / "GEWST-0021-12345678-1234567890000-2023-01-15_"
    "00000000-0000-0000-0000-000000000213.xml"
)
MULTI_YEAR_FIXTURES = [
    FIXTURES_DIR
    / "GEWST-0010-12345678-1234567890000-2021-01-15_"
    "00000000-0000-0000-0000-000000000101.xml",
    FIXTURES_DIR
    / "GEWST-0010-12345678-1234567890000-2022-01-15_"
    "00000000-0000-0000-0000-000000000102.xml",
    FIXTURES_DIR
    / "GEWST-0010-12345678-1234567890000-2023-01-15_"
    "00000000-0000-0000-0000-000000000103.xml",
]
APP_CSS_FILE = (
    Path(__file__).resolve().parents[1]
    / "static"
    / "xgewerbesteuer"
    / "app.css"
)


def uploaded_xml(name, content):
    return SimpleUploadedFile(name, content, content_type="application/xml")


def processed_bescheid_with_due_date():
    summary_items = [
        {"label": "Gemeinde / Kommune", "value": "Stadt Musterhausen"},
        {"label": "Steuerjahr / Erhebungszeitraum", "value": "2025"},
        {"label": "Zahlbetrag", "value": "630.00"},
        {"label": "Zahlungsart", "value": "Nachzahlung"},
        {"label": "Gewerbesteuermessbetrag", "value": "150.00"},
        {"label": "Hebesatz", "value": "420"},
        {"label": "Fälligkeiten", "value": "2025-02-15"},
    ]

    return {
        "is_valid": True,
        "bescheid": {
            "file_name": "bescheid.xml",
            "file_size": 128,
            "schema_name": "gewerbesteuer.xsd",
            "municipality": "Stadt Musterhausen",
            "tax_period": "2025",
            "amount_due": "630.00",
            "trade_tax_assessment_amount": "150.00",
            "assessment_rate": "420",
            "due_dates": "2025-02-15",
            "summary_items": summary_items,
            "calculation_explanation": {
                "can_calculate": False,
                "message": "Testdaten.",
            },
            "advance_payments": [],
            "payment_classification": {
                "type": "Nachzahlung",
                "message": "Testeinordnung.",
            },
        },
    }


def processed_bescheid_with_plausibility_values(
    amount_due="630.00",
    trade_tax_assessment_amount="150.00",
    assessment_rate="420",
):
    result = processed_bescheid_with_due_date()
    bescheid = result["bescheid"]

    bescheid["amount_due"] = amount_due
    bescheid["trade_tax_assessment_amount"] = trade_tax_assessment_amount
    bescheid["assessment_rate"] = assessment_rate
    bescheid["summary_items"] = [
        {"label": "Gemeinde / Kommune", "value": "Stadt Musterhausen"},
        {"label": "Steuerjahr / Erhebungszeitraum", "value": "2025"},
        {"label": "Zahlbetrag", "value": amount_due},
        {"label": "Zahlungsart", "value": "Nachzahlung"},
        {"label": "Gewerbesteuermessbetrag", "value": trade_tax_assessment_amount},
        {"label": "Hebesatz", "value": assessment_rate},
        {"label": "Fälligkeiten", "value": "2025-02-15"},
    ]

    return result


def comparison_bescheid(
    tax_period,
    amount_due="100.00",
    municipality="Stadt Musterhausen",
    advance_payments=None,
    file_name=None,
):
    return {
        "file_name": file_name or f"bescheid-{tax_period}.xml",
        "municipality": municipality,
        "tax_period": tax_period,
        "amount_due": amount_due,
        "trade_tax_assessment_amount": "25.00",
        "assessment_rate": "420",
        "due_dates": "2025-02-15",
        "advance_payments": advance_payments or [],
        "payment_classification": {"type": "Nachzahlung"},
    }


class XGewerbesteuerExtractionTests(SimpleTestCase):
    def parse(self, xml_text):
        return ElementTree.fromstring(xml_text.encode("utf-8"))

    def test_responsive_css_file_contains_mobile_rules(self):
        css_content = APP_CSS_FILE.read_text(encoding="utf-8")

        self.assertIn("@media (max-width: 768px)", css_content)
        self.assertIn(".table-wrapper", css_content)
        self.assertIn(".download-bar", css_content)

    def test_responsive_css_contains_kern_layout_rules(self):
        css_content = APP_CSS_FILE.read_text(encoding="utf-8")

        self.assertIn(".card", css_content)
        self.assertIn(".alert--error", css_content)
        self.assertIn(".alert--success", css_content)
        self.assertIn(".status-banner--deadline", css_content)
        self.assertIn(".download-bar", css_content)
        self.assertIn(".row--highlight-warning", css_content)
        self.assertIn(".calendar-grid", css_content)
        self.assertIn(".calendar-month", css_content)
        self.assertIn(".calendar-entry", css_content)
        self.assertIn(".historical-chart", css_content)
        self.assertIn(".historical-chart__bar", css_content)
        self.assertIn(".plausibility-status", css_content)
        self.assertIn(".plausibility-status--plausible", css_content)
        self.assertIn(".plausibility-status--warning", css_content)
        self.assertIn(".plausibility-status--not-checkable", css_content)
        self.assertIn(".saved-upload-actions", css_content)

    def test_responsive_css_contains_print_media_block(self):
        css_content = APP_CSS_FILE.read_text(encoding="utf-8")

        self.assertIn("@media print", css_content)
        self.assertIn("@page", css_content)
        self.assertIn("margin: 1.5cm", css_content)

    def test_print_css_hides_interactive_elements(self):
        css_content = APP_CSS_FILE.read_text(encoding="utf-8")

        self.assertIn(".no-print", css_content)
        self.assertIn(".download-bar", css_content)
        self.assertIn(".btn", css_content)
        self.assertIn("display: none !important", css_content)

    def test_print_css_keeps_tables_readable(self):
        css_content = APP_CSS_FILE.read_text(encoding="utf-8")

        self.assertIn(".table-wrapper", css_content)
        self.assertIn("overflow: visible", css_content)
        self.assertIn("white-space: normal", css_content)

    def test_print_css_contains_page_break_rules(self):
        css_content = APP_CSS_FILE.read_text(encoding="utf-8")

        self.assertIn("break-inside", css_content)
        self.assertIn("page-break-inside", css_content)

    def test_clean_text_normalizes_whitespace_and_empty_values(self):
        self.assertEqual(clean_text("  Stadt   Musterhausen\nNord  "), "Stadt Musterhausen Nord")
        self.assertIsNone(clean_text("   \n  "))
        self.assertIsNone(clean_text(None))

    def test_get_local_name_removes_xml_namespace(self):
        self.assertEqual(
            get_local_name("{urn:xoev-de:xunternehmen:standard:gewerbesteuer_1.4}kommune"),
            "kommune",
        )
        self.assertEqual(get_local_name("kommune"), "kommune")

    def test_detect_message_type_recognizes_supported_fixture_roots(self):
        fixtures_by_type = {
            ASSESSMENT_FIXTURE: "bescheide.gewerbesteuer.0001",
            INTEREST_FIXTURE: "bescheide.zinsen.0002",
            ADVANCE_PAYMENT_FIXTURE: "bescheide.vorauszahlung.0003",
            VALID_BESCHEID_FIXTURE: "bescheide.gewerbesteuer.generisch.0010",
            CALCULATION_FIXTURE: "berechnung.gewerbesteuer.0021",
        }

        for fixture_path, expected_message_type in fixtures_by_type.items():
            with self.subTest(filename=fixture_path.name):
                root = ElementTree.parse(fixture_path).getroot()

                self.assertEqual(detect_message_type(root), expected_message_type)

    def test_unknown_message_type_is_rejected_after_validation(self):
        with patch(
            "xgewerbesteuer.services.bescheid.validate_xml_against_xsd",
            return_value=(True, "gewerbesteuer.xsd", None),
        ):
            result = process_uploaded_bescheid(
                uploaded_xml("unbekannt.xml", b"<unbekannte.nachricht />")
            )

        self.assertFalse(result["is_valid"])
        self.assertEqual(result["error_type"], "unsupported_message_type")
        self.assertEqual(
            result["message"],
            "Der Nachrichtentyp der XML-Datei wird derzeit nicht unterstuetzt.",
        )

    def test_build_bescheid_data_carries_message_type_in_summary(self):
        content = VALID_BESCHEID_FIXTURE.read_bytes()
        bescheid = build_bescheid_data(
            uploaded_xml(VALID_BESCHEID_FIXTURE.name, content),
            ElementTree.fromstring(content),
            "gewerbesteuer.xsd",
        )
        summary_items = {item["label"]: item["value"] for item in bescheid["summary_items"]}

        self.assertEqual(
            bescheid["message_type"],
            "bescheide.gewerbesteuer.generisch.0010",
        )
        self.assertEqual(
            bescheid["message_type_label"],
            "Generische Gewerbesteuernachricht",
        )
        self.assertEqual(bescheid["message_type_category"], "generic")
        self.assertEqual(
            summary_items["Nachrichtentyp"],
            "Generische Gewerbesteuernachricht",
        )

    def test_message_type_specific_payment_classification_uses_domain_labels(self):
        fixtures_by_expectation = [
            (INTEREST_FIXTURE, "Zinsbescheid", "interest"),
            (ADVANCE_PAYMENT_FIXTURE, "Vorauszahlung", "advance_payment"),
            (CALCULATION_FIXTURE, "Nicht pruefbar", "calculation"),
        ]

        for fixture_path, expected_payment_type, expected_category in fixtures_by_expectation:
            with self.subTest(filename=fixture_path.name):
                content = fixture_path.read_bytes()
                bescheid = build_bescheid_data(
                    uploaded_xml(fixture_path.name, content),
                    ElementTree.fromstring(content),
                    "gewerbesteuer.xsd",
                )

                self.assertEqual(bescheid["message_type_category"], expected_category)
                self.assertEqual(
                    bescheid["payment_classification"]["type"],
                    expected_payment_type,
                )

    def test_different_message_types_create_neutral_comparison_notice(self):
        current_content = VALID_BESCHEID_FIXTURE.read_bytes()
        previous_content = INTEREST_FIXTURE.read_bytes()
        current_bescheid = build_bescheid_data(
            uploaded_xml(VALID_BESCHEID_FIXTURE.name, current_content),
            ElementTree.fromstring(current_content),
            "gewerbesteuer.xsd",
        )
        previous_bescheid = build_bescheid_data(
            uploaded_xml(INTEREST_FIXTURE.name, previous_content),
            ElementTree.fromstring(previous_content),
            "gewerbesteuer.xsd",
        )

        notice = build_message_type_comparison_notice(current_bescheid, previous_bescheid)

        self.assertIn("unterschiedliche Nachrichtentypen", notice)
        self.assertEqual(build_change_comparison(current_bescheid, previous_bescheid), [])

    def test_extracts_core_values_from_fixture(self):
        root = ElementTree.parse(VALID_BESCHEID_FIXTURE).getroot()

        self.assertEqual(extract_municipality(root), "Stadt Musterhausen")
        self.assertEqual(extract_tax_period(root), "2023")
        self.assertEqual(extract_amount_due(root), "630.00")
        self.assertEqual(extract_trade_tax_assessment_amount(root), "150.00")
        self.assertEqual(extract_assessment_rate(root), "420")

    def test_exact_tag_matching_does_not_use_parent_container_text(self):
        root = self.parse(
            """
            <nachricht>
              <zahlbetragContainer>999.00</zahlbetragContainer>
              <festsetzungAktuell>123.45</festsetzungAktuell>
              <messbetragHistorie>777.00</messbetragHistorie>
              <messbetrag>42.00</messbetrag>
            </nachricht>
            """
        )

        self.assertEqual(extract_amount_due(root), "123.45")
        self.assertEqual(extract_trade_tax_assessment_amount(root), "42.00")

    def test_extract_tax_period_formats_range_and_quarter_variants(self):
        range_root = self.parse(
            """
            <nachricht>
              <zeitraum>
                <beginn>2025-01-01</beginn>
                <ende>2025-12-31</ende>
              </zeitraum>
            </nachricht>
            """
        )
        quarter_root = self.parse(
            """
            <nachricht>
              <erhebungszeitraum>
                <steuerjahr>2025</steuerjahr>
                <quartal>2</quartal>
              </erhebungszeitraum>
            </nachricht>
            """
        )

        self.assertEqual(extract_tax_period(range_root), "2025-01-01 bis 2025-12-31")
        self.assertEqual(extract_tax_period(quarter_root), "2025, Quartal 2")

    def test_extract_due_dates_deduplicates_known_due_date_tags(self):
        root = self.parse(
            """
            <nachricht>
              <faelligkeitsdatum>2025-02-15</faelligkeitsdatum>
              <zahlungstermin>2025-03-15</zahlungstermin>
              <fälligkeitsdatum>2025-02-15</fälligkeitsdatum>
            </nachricht>
            """
        )

        self.assertEqual(extract_due_dates(root), "2025-02-15, 2025-03-15")

    def test_extract_helpers_return_not_found_for_missing_optional_values(self):
        root = self.parse("<nachricht />")

        self.assertIsNone(extract_amount_due(root))
        self.assertIsNone(extract_assessment_rate(root))
        self.assertIsNone(extract_due_dates(root))

    def test_extract_advance_payments_from_fixture(self):
        root = ElementTree.parse(ADVANCE_PAYMENT_FIXTURE).getroot()

        advance_payments = extract_advance_payments(root)

        self.assertEqual(len(advance_payments), 1)
        self.assertEqual(advance_payments[0]["amount"], "147.00")
        self.assertIsNone(advance_payments[0]["due_date"])
        self.assertEqual(advance_payments[0]["period"], "2023")
        self.assertEqual(advance_payments[0]["type"], "Vorauszahlung")

    def test_extract_advance_payments_returns_empty_list_when_missing(self):
        root = self.parse("<nachricht />")

        self.assertEqual(extract_advance_payments(root), [])

    def test_extract_advance_payments_sorts_with_missing_values(self):
        root = self.parse(
            """
            <nachricht>
              <vorauszahlung>
                <vorauszahlungsbetrag>200.00</vorauszahlungsbetrag>
              </vorauszahlung>
              <vorauszahlung>
                <vorauszahlungsbetrag>100.00</vorauszahlungsbetrag>
                <faelligkeitsdatum>2025-02-15</faelligkeitsdatum>
                <bezugsjahr>2025</bezugsjahr>
              </vorauszahlung>
            </nachricht>
            """
        )

        advance_payments = extract_advance_payments(root)

        self.assertIsNone(advance_payments[0]["due_date"])
        self.assertEqual(advance_payments[1]["due_date"], "2025-02-15")

    def test_classifies_advance_payment_when_advance_payments_exist(self):
        classification = classify_payment_type(
            "147.00",
            [
                {
                    "amount": "147.00",
                    "due_date": None,
                    "period": "2023",
                    "type": "Vorauszahlung",
                }
            ],
        )

        self.assertEqual(classification["type"], "Vorauszahlung")

    def test_classifies_positive_amount_as_back_payment(self):
        classification = classify_payment_type("630.00", [])

        self.assertEqual(classification["type"], "Nachzahlung")

    def test_classifies_negative_amount_as_refund(self):
        classification = classify_payment_type("-25.00", [])

        self.assertEqual(classification["type"], "Erstattung")

    def test_classifies_zero_amount_as_no_payment(self):
        classification = classify_payment_type("0.00", [])

        self.assertEqual(classification["type"], "Keine Zahlung")

    def test_classifies_missing_amount_as_not_determinable(self):
        classification = classify_payment_type(None, [])

        self.assertEqual(classification["type"], "Nicht eindeutig bestimmbar")

    def test_parse_decimal_value_returns_none_for_none(self):
        self.assertIsNone(parse_decimal_value(None))

    def test_period_comparison_notice_handles_different_same_and_missing_years(self):
        self.assertIn(
            "unterschiedliche Steuerjahre",
            build_period_comparison_notice("2023", "2022"),
        )
        self.assertIn(
            "denselben Steuerzeitraum",
            build_period_comparison_notice("2023", "2023"),
        )
        self.assertIn(
            "nicht vollständig",
            build_period_comparison_notice(None, "2022"),
        )

    def test_comparison_helpers_treat_none_as_not_comparable(self):
        decimal_result = compare_decimal_values(None, "100.00")
        text_result = compare_text_values(None, "2022")

        self.assertEqual(decimal_result["change_type"], "Nicht vergleichbar")
        self.assertEqual(text_result["change_type"], "Nicht vergleichbar")

    def test_classify_change_importance_marks_relevant_changes(self):
        increase = classify_change_importance("Erhöhung")
        decrease = classify_change_importance("Senkung")
        changed = classify_change_importance("Geändert")
        unchanged = classify_change_importance("Unverändert")

        self.assertEqual(increase["level"], "important")
        self.assertEqual(increase["label"], "Wichtige Änderung")
        self.assertEqual(
            increase["message"],
            "Dieser Wert hat sich gegenüber dem Vorjahr erhöht.",
        )

        self.assertEqual(decrease["level"], "notice")
        self.assertEqual(decrease["label"], "Änderung")

        self.assertEqual(changed["level"], "notice")
        self.assertEqual(changed["label"], "Änderung")

        self.assertEqual(unchanged["level"], "neutral")
        self.assertEqual(unchanged["label"], "Keine wichtige Änderung")

    def test_build_notice_area_prioritizes_warning_before_info(self):
        current_bescheid = {
            "municipality": "Stadt Musterhausen",
            "tax_period": None,
            "amount_due": None,
            "payment_classification": {
                "type": "Nicht eindeutig bestimmbar",
            },
        }
        change_comparison_items = [
            {
                "label": "Zahlbetrag",
                "importance": "important",
            }
        ]

        notice_items = build_notice_area(current_bescheid, change_comparison_items)

        self.assertGreaterEqual(len(notice_items), 2)
        self.assertEqual(notice_items[0]["severity"], "warning")
        self.assertIn("nicht gefunden", notice_items[0]["title"].lower())
        self.assertTrue(
            any(
                notice["title"] == "Wichtige Änderung zum Vorjahr"
                for notice in notice_items
            )
        )

    def test_build_notice_area_returns_neutral_notice_without_findings(self):
        current_bescheid = {
            "municipality": "Stadt Musterhausen",
            "tax_period": "2023",
            "amount_due": "0.00",
            "payment_classification": {
                "type": "Keine Zahlung",
            },
        }

        notice_items = build_notice_area(current_bescheid)

        self.assertEqual(len(notice_items), 1)
        self.assertEqual(notice_items[0]["severity"], "neutral")
        self.assertEqual(notice_items[0]["title"], "Keine Auffälligkeiten erkannt")

    def test_build_status_indicator_prioritizes_warning_before_deadline(self):
        current_bescheid = {
            "municipality": "Stadt Musterhausen",
            "tax_period": "2023",
            "amount_due": "630.00",
            "due_dates": "2025-02-15",
            "payment_classification": {
                "type": "Nachzahlung",
            },
        }
        notice_items = [
            {
                "severity": "warning",
                "source_rule": "comparison-important-change",
            }
        ]
        change_comparison_items = [
            {
                "importance": "important",
            }
        ]

        status_indicator = build_status_indicator(
            current_bescheid,
            notice_items,
            change_comparison_items,
        )

        self.assertEqual(status_indicator["status"], "warning")
        self.assertEqual(status_indicator["label"], "Warnung / Auffälligkeit")

    def test_build_status_indicator_marks_deadline_for_back_payment(self):
        current_bescheid = {
            "municipality": "Stadt Musterhausen",
            "tax_period": "2023",
            "amount_due": "630.00",
            "due_dates": None,
            "payment_classification": {
                "type": "Nachzahlung",
            },
        }

        status_indicator = build_status_indicator(current_bescheid)

        self.assertEqual(status_indicator["status"], "deadline")
        self.assertEqual(status_indicator["label"], "Frist beachten")

    def test_build_status_indicator_marks_change_without_warning(self):
        current_bescheid = {
            "municipality": "Stadt Musterhausen",
            "tax_period": "2023",
            "amount_due": "0.00",
            "due_dates": None,
            "payment_classification": {
                "type": "Keine Zahlung",
            },
        }
        change_comparison_items = [
            {
                "importance": "notice",
            }
        ]

        status_indicator = build_status_indicator(
            current_bescheid,
            change_comparison_items=change_comparison_items,
        )

        self.assertEqual(status_indicator["status"], "change")
        self.assertEqual(status_indicator["label"], "Änderung beachten")

    def test_build_status_indicator_marks_incomplete_data_neutrally(self):
        current_bescheid = {
            "municipality": None,
            "tax_period": None,
            "amount_due": None,
            "due_dates": None,
            "payment_classification": {
                "type": "Nicht eindeutig bestimmbar",
            },
        }

        status_indicator = build_status_indicator(current_bescheid)

        self.assertEqual(status_indicator["status"], "incomplete")
        self.assertEqual(status_indicator["label"], "Daten unvollständig")

    def test_build_status_indicator_marks_ok_without_findings(self):
        current_bescheid = {
            "municipality": "Stadt Musterhausen",
            "tax_period": "2023",
            "amount_due": "0.00",
            "due_dates": None,
            "payment_classification": {
                "type": "Keine Zahlung",
            },
        }

        status_indicator = build_status_indicator(current_bescheid)

        self.assertEqual(status_indicator["status"], "ok")
        self.assertEqual(status_indicator["label"], "Unauffällig")

    def test_build_change_comparison_calculates_differences(self):
        current_bescheid = {
            "amount_due": "630.00",
            "trade_tax_assessment_amount": "150.00",
            "assessment_rate": "420",
            "due_dates": None,
            "tax_period": "2023",
        }
        previous_bescheid = {
            "amount_due": "512.50",
            "trade_tax_assessment_amount": "125.00",
            "assessment_rate": "420",
            "due_dates": None,
            "tax_period": "2022",
        }

        comparison_items = build_change_comparison(current_bescheid, previous_bescheid)
        comparison_by_label = {item["label"]: item for item in comparison_items}

        self.assertEqual(comparison_by_label["Zahlbetrag"]["difference"], "+117.50")
        self.assertEqual(comparison_by_label["Zahlbetrag"]["percentage"], "+22.93 %")
        self.assertEqual(comparison_by_label["Zahlbetrag"]["change_type"], "Erhöhung")
        self.assertEqual(comparison_by_label["Zahlbetrag"]["importance"], "important")
        self.assertEqual(
            comparison_by_label["Zahlbetrag"]["importance_label"],
            "Wichtige Änderung",
        )
        self.assertEqual(
            comparison_by_label["Zahlbetrag"]["importance_message"],
            "Dieser Wert hat sich gegenüber dem Vorjahr erhöht.",
        )

        self.assertEqual(
            comparison_by_label["Gewerbesteuermessbetrag"]["difference"],
            "+25.00",
        )
        self.assertEqual(
            comparison_by_label["Gewerbesteuermessbetrag"]["percentage"],
            "+20.00 %",
        )
        self.assertEqual(
            comparison_by_label["Gewerbesteuermessbetrag"]["change_type"],
            "Erhöhung",
        )

        self.assertEqual(comparison_by_label["Hebesatz"]["difference"], "0.00")
        self.assertEqual(comparison_by_label["Hebesatz"]["percentage"], "0.00 %")
        self.assertEqual(comparison_by_label["Hebesatz"]["change_type"], "Unverändert")
        self.assertEqual(comparison_by_label["Hebesatz"]["importance"], "neutral")

        self.assertEqual(
            comparison_by_label["Fälligkeiten"]["change_type"],
            "Nicht vergleichbar",
        )
        self.assertEqual(comparison_by_label["Fälligkeiten"]["importance"], "neutral")
        self.assertEqual(
            comparison_by_label["Steuerjahr / Erhebungszeitraum"]["change_type"],
            "Geändert",
        )
        self.assertEqual(
            comparison_by_label["Steuerjahr / Erhebungszeitraum"]["importance"],
            "notice",
        )

    def test_build_change_comparison_does_not_divide_by_zero(self):
        current_bescheid = {
            "amount_due": "100.00",
            "trade_tax_assessment_amount": "50.00",
            "assessment_rate": "420",
            "due_dates": "2025-02-15",
            "tax_period": "2025",
        }
        previous_bescheid = {
            "amount_due": "0.00",
            "trade_tax_assessment_amount": "50.00",
            "assessment_rate": "420",
            "due_dates": "2025-02-15",
            "tax_period": "2025",
        }

        comparison_items = build_change_comparison(current_bescheid, previous_bescheid)
        comparison_by_label = {item["label"]: item for item in comparison_items}

        self.assertEqual(
            comparison_by_label["Zahlbetrag"]["percentage"],
            "Nicht vergleichbar",
        )
        self.assertEqual(
            comparison_by_label["Zahlbetrag"]["change_type"],
            "Erhöhung",
        )

    def test_plausible_values_create_no_warning(self):
        plausibility = build_plausibility_check(
            comparison_bescheid("2025", amount_due="105.00")
        )

        self.assertEqual(plausibility["status"], "plausible")
        self.assertEqual(plausibility["label"], "Plausibel")

    def test_unplausible_values_create_warning(self):
        plausibility = build_plausibility_check(
            comparison_bescheid("2025", amount_due="120.00")
        )

        self.assertEqual(plausibility["status"], "warning")
        self.assertEqual(plausibility["label"], "Warnung / Abweichung")
        self.assertIn("weicht", plausibility["message"])

    def test_rounding_difference_within_tolerance_is_accepted(self):
        comparison = compare_plausibility_amounts(
            "105.01",
            calculate_expected_trade_tax("25.00", "420"),
        )

        self.assertEqual(PLAUSIBILITY_TOLERANCE, Decimal("0.02"))
        self.assertEqual(comparison["status"], "plausible")

    def test_missing_amount_due_is_not_checkable(self):
        plausibility = build_plausibility_check(
            comparison_bescheid("2025", amount_due=None)
        )

        self.assertEqual(plausibility["status"], "not_checkable")
        self.assertIn("Ausgelesener Zahlbetrag", plausibility["message"])

    def test_missing_trade_tax_assessment_amount_is_not_checkable(self):
        bescheid = comparison_bescheid("2025", amount_due="105.00")
        bescheid["trade_tax_assessment_amount"] = None

        plausibility = build_plausibility_check(bescheid)

        self.assertEqual(plausibility["status"], "not_checkable")
        self.assertIn("Gewerbesteuermessbetrag", plausibility["message"])

    def test_missing_assessment_rate_is_not_checkable(self):
        bescheid = comparison_bescheid("2025", amount_due="105.00")
        bescheid["assessment_rate"] = None

        plausibility = build_plausibility_check(bescheid)

        self.assertEqual(plausibility["status"], "not_checkable")
        self.assertIn("Hebesatz", plausibility["message"])

    def test_zero_values_are_handled_explicitly(self):
        plausible_zero = build_plausibility_check(
            {
                **comparison_bescheid("2025", amount_due="0.00"),
                "trade_tax_assessment_amount": "0.00",
            }
        )
        warning_zero = build_plausibility_check(
            comparison_bescheid("2025", amount_due="0.00")
        )

        self.assertEqual(plausible_zero["status"], "plausible")
        self.assertEqual(warning_zero["status"], "warning")

    def test_negative_values_are_explained_neutrally(self):
        plausibility = build_plausibility_check(
            comparison_bescheid("2025", amount_due="-105.00")
        )

        self.assertEqual(plausibility["status"], "not_checkable")
        self.assertIn("Negative Beträge", plausibility["message"])

    def test_expected_trade_tax_uses_assessment_amount_times_rate(self):
        expected_amount = calculate_expected_trade_tax("150.00", "420")

        self.assertEqual(expected_amount, Decimal("630.00"))

    def test_plausibility_messages_contain_no_raw_xml_or_parser_details(self):
        plausibility = build_plausibility_check(
            comparison_bescheid("2025", amount_due="120.00")
        )
        content = " ".join(
            [
                plausibility["message"],
                plausibility["expected_amount"],
                plausibility["actual_amount"],
                plausibility["difference"],
            ]
        )

        self.assertNotIn("<nachricht", content)
        self.assertNotIn("XMLParser", content)
        self.assertNotIn("Traceback", content)
        self.assertNotIn("DEBUG", content)

    def test_sort_bescheid_records_chronologically_orders_multiple_years(self):
        records = [
            build_multi_bescheid_record(comparison_bescheid("2023")),
            build_multi_bescheid_record(comparison_bescheid("2021")),
            build_multi_bescheid_record(comparison_bescheid("2022")),
        ]

        sorted_records = sort_bescheid_records_chronologically(records)

        self.assertEqual(
            [record["tax_period"] for record in sorted_records],
            ["2021", "2022", "2023"],
        )

    def test_build_multi_bescheid_comparison_structures_multiple_years(self):
        comparison = build_multi_bescheid_comparison(
            [
                comparison_bescheid("2022", amount_due="200.00"),
                comparison_bescheid("2021", amount_due="100.00"),
            ]
        )

        self.assertEqual(comparison["valid_count"], 2)
        self.assertEqual(comparison["records"][0]["tax_period"], "2021")
        self.assertEqual(comparison["records"][0]["amount_due"], "100.00")
        self.assertEqual(comparison["records"][1]["amount_due"], "200.00")

    def test_build_multi_bescheid_comparison_keeps_missing_values(self):
        comparison = build_multi_bescheid_comparison(
            [
                comparison_bescheid(None, amount_due=None),
                comparison_bescheid("2023"),
            ]
        )

        missing_record = comparison["records"][1]

        self.assertIsNone(missing_record["tax_period"])
        self.assertIsNone(missing_record["amount_due"])
        self.assertTrue(missing_record["notes"])

    def test_group_bescheide_by_tax_period_detects_duplicate_years(self):
        comparison = build_multi_bescheid_comparison(
            [
                comparison_bescheid("2023", file_name="erstbescheid.xml"),
                comparison_bescheid("2023", file_name="aenderungsbescheid.xml"),
            ]
        )
        grouped_records = group_bescheide_by_tax_period(comparison["records"])

        self.assertEqual(len(grouped_records["2023"]), 2)
        self.assertEqual(comparison["duplicate_tax_periods"], ["2023"])
        self.assertTrue(
            all(record["duplicate_tax_period"] for record in comparison["records"])
        )

    def test_build_multi_bescheid_record_marks_missing_municipality_neutrally(self):
        record = build_multi_bescheid_record(
            comparison_bescheid("2023", municipality=None)
        )

        self.assertIsNone(record["municipality"])
        self.assertIn("Gemeinde / Kommune", record["notes"][0])

    def test_build_multi_bescheid_record_includes_advance_payments(self):
        record = build_multi_bescheid_record(
            comparison_bescheid(
                "2023",
                advance_payments=[
                    {
                        "amount": "147.00",
                        "due_date": "2025-03-15",
                        "period": "2025",
                        "type": "Vorauszahlung",
                    }
                ],
            )
        )

        self.assertIn("147.00", record["advance_payments"])
        self.assertIn("Vorauszahlung", record["advance_payments"])

    def test_build_multi_bescheid_upload_errors_keeps_valid_results(self):
        errors = build_multi_bescheid_upload_errors(
            [
                {
                    "file_name": "gueltig.xml",
                    "result": {
                        "is_valid": True,
                        "bescheid": comparison_bescheid("2023"),
                    },
                },
                {
                    "file_name": "ungueltig.txt",
                    "result": {
                        "is_valid": False,
                        "error_type": "upload",
                        "message": "Die hochgeladene Datei muss eine XML-Datei sein.",
                    },
                },
            ]
        )

        self.assertEqual(len(errors), 1)
        self.assertEqual(errors[0]["file_name"], "ungueltig.txt")
        self.assertIn("XML-Datei", errors[0]["message"])

    def test_single_valid_bescheid_does_not_create_multi_comparison(self):
        comparison = build_multi_bescheid_comparison([comparison_bescheid("2023")])

        self.assertIsNone(comparison)

    def test_build_historical_development_from_three_years(self):
        comparison = build_multi_bescheid_comparison(
            [
                comparison_bescheid("2021", amount_due="400.00"),
                comparison_bescheid("2022", amount_due="512.50"),
                comparison_bescheid("2023", amount_due="630.00"),
            ]
        )

        history = build_historical_development(comparison["records"])

        self.assertTrue(history["has_history"])
        self.assertEqual(history["year_count"], 3)
        self.assertEqual(len(history["rows"]), 3)

    def test_build_historical_development_sorts_rows_chronologically(self):
        records = [
            build_multi_bescheid_record(comparison_bescheid("2023")),
            build_multi_bescheid_record(comparison_bescheid("2021")),
            build_multi_bescheid_record(comparison_bescheid("2022")),
        ]

        history = build_historical_development(records)

        self.assertEqual(
            [row["tax_period"] for row in history["rows"]],
            ["2021", "2022", "2023"],
        )

    def test_calculate_historical_change_for_amount_due(self):
        self.assertEqual(calculate_historical_change("512.50", "400.00"), "+112.50")
        self.assertEqual(calculate_historical_change("630.00", "512.50"), "+117.50")

    def test_historical_row_calculates_trade_tax_assessment_change(self):
        previous_record = build_multi_bescheid_record(
            comparison_bescheid("2021", amount_due="400.00")
        )
        current_record = build_multi_bescheid_record(
            {
                **comparison_bescheid("2022", amount_due="512.50"),
                "trade_tax_assessment_amount": "125.00",
            }
        )
        previous_record["trade_tax_assessment_amount"] = "100.00"

        row = build_historical_development_row(current_record, previous_record)

        self.assertEqual(row["trade_tax_assessment_amount_change"], "+25.00")

    def test_historical_row_calculates_assessment_rate_change(self):
        previous_record = build_multi_bescheid_record(
            {**comparison_bescheid("2021"), "assessment_rate": "400"}
        )
        current_record = build_multi_bescheid_record(
            {**comparison_bescheid("2022"), "assessment_rate": "410"}
        )

        row = build_historical_development_row(current_record, previous_record)

        self.assertEqual(row["assessment_rate_change"], "+10.00")

    def test_historical_development_marks_missing_values_neutrally(self):
        row = build_historical_development_row(
            build_multi_bescheid_record(
                comparison_bescheid("2022", amount_due=None)
            ),
            build_multi_bescheid_record(comparison_bescheid("2021")),
        )

        self.assertIsNone(row["amount_due"])
        self.assertEqual(row["amount_due_change"], "Nicht berechenbar")

    def test_missing_historical_value_does_not_affect_other_years(self):
        history = build_historical_development(
            [
                build_multi_bescheid_record(
                    comparison_bescheid("2021", amount_due=None)
                ),
                build_multi_bescheid_record(comparison_bescheid("2022", "512.50")),
                build_multi_bescheid_record(comparison_bescheid("2023", "630.00")),
            ]
        )

        self.assertEqual(history["rows"][1]["amount_due_change"], "Nicht berechenbar")
        self.assertEqual(history["rows"][2]["amount_due_change"], "+117.50")

    def test_single_record_does_not_create_historical_development(self):
        records = [build_multi_bescheid_record(comparison_bescheid("2023"))]

        self.assertIsNone(build_historical_development(records))

    def test_build_historical_chart_data_returns_view_model(self):
        rows = [
            build_historical_development_row(
                build_multi_bescheid_record(comparison_bescheid("2021", "400.00"))
            ),
            build_historical_development_row(
                build_multi_bescheid_record(comparison_bescheid("2022", "800.00"))
            ),
        ]

        chart_data = build_historical_chart_data(rows)

        self.assertEqual(chart_data[0]["tax_period"], "2021")
        self.assertEqual(chart_data[1]["width_percent"], 100)

    def test_historical_development_notice_contains_no_trend_claim(self):
        history = build_historical_development(
            [
                build_multi_bescheid_record(comparison_bescheid("2021")),
                build_multi_bescheid_record(comparison_bescheid("2022")),
            ]
        )

        self.assertNotIn("Trend", history["notice"])
        self.assertNotIn("Prognose", history["notice"])

    def test_build_due_date_calendar_entries_from_due_dates(self):
        current_bescheid = {
            "amount_due": "630.00",
            "due_dates": "2025-02-15",
            "payment_classification": {"type": "Nachzahlung"},
            "advance_payments": [],
        }

        entries = build_due_date_calendar_entries(current_bescheid)

        self.assertEqual(len(entries), 1)
        self.assertEqual(entries[0]["date"], "2025-02-15")
        self.assertEqual(entries[0]["display_date"], "15.02.2025")
        self.assertEqual(entries[0]["amount"], "630,00 EUR")
        self.assertEqual(entries[0]["payment_type"], "Nachzahlung")
        self.assertEqual(entries[0]["label"], "Nachzahlung am 15.02.2025")

    def test_split_due_date_values_removes_empty_parts(self):
        self.assertEqual(
            split_due_date_values("2025-02-15, , 2025-03-15"),
            ["2025-02-15", "2025-03-15"],
        )

    def test_build_due_date_calendar_uses_advance_payment_due_dates(self):
        current_bescheid = {
            "amount_due": None,
            "due_dates": None,
            "payment_classification": {"type": "Vorauszahlung"},
            "advance_payments": [
                {
                    "amount": "147.00",
                    "due_date": "2025-03-15",
                    "period": "2025",
                    "type": "Vorauszahlung",
                }
            ],
        }

        calendar = build_due_date_calendar(current_bescheid)

        self.assertTrue(calendar["has_entries"])
        self.assertEqual(calendar["months"][0]["label"], "März 2025")
        self.assertEqual(calendar["months"][0]["entries"][0]["amount"], "147,00 EUR")

    def test_build_due_date_calendar_keeps_unparseable_advance_payment_undated(self):
        current_bescheid = {
            "amount_due": None,
            "due_dates": None,
            "payment_classification": {"type": "Vorauszahlung"},
            "advance_payments": [
                {
                    "amount": "147.00",
                    "due_date": None,
                    "period": "2025",
                    "type": "Vorauszahlung",
                }
            ],
        }

        calendar = build_due_date_calendar(current_bescheid)

        self.assertFalse(calendar["has_entries"])
        self.assertEqual(len(calendar["undated_items"]), 1)
        self.assertEqual(calendar["undated_items"][0]["payment_type"], "Vorauszahlung")

    def test_build_due_date_calendar_sorts_entries_chronologically(self):
        current_bescheid = {
            "amount_due": "630.00",
            "due_dates": "2025-03-15, 2025-02-15",
            "payment_classification": {"type": "Nachzahlung"},
            "advance_payments": [],
        }

        calendar = build_due_date_calendar(current_bescheid)
        entries = [
            entry
            for month in calendar["months"]
            for entry in month["entries"]
        ]

        self.assertEqual([entry["date"] for entry in entries], ["2025-02-15", "2025-03-15"])

    def test_group_calendar_entries_by_month_uses_german_month_labels(self):
        entries = [
            {
                "date": "2025-02-15",
                "display_date": "15.02.2025",
                "amount": "100,00 EUR",
                "payment_type": "Nachzahlung",
                "label": "Nachzahlung am 15.02.2025",
                "notes": [],
            },
            {
                "date": "2025-03-15",
                "display_date": "15.03.2025",
                "amount": "100,00 EUR",
                "payment_type": "Nachzahlung",
                "label": "Nachzahlung am 15.03.2025",
                "notes": [],
            },
        ]

        groups = group_calendar_entries_by_month(entries)

        self.assertEqual([group["label"] for group in groups], ["Februar 2025", "März 2025"])

    def test_build_due_date_calendar_keeps_multiple_entries_on_same_day(self):
        current_bescheid = {
            "amount_due": "630.00",
            "due_dates": "2025-02-15",
            "payment_classification": {"type": "Nachzahlung"},
            "advance_payments": [
                {
                    "amount": "147.00",
                    "due_date": "2025-02-15",
                    "period": "2025",
                    "type": "Vorauszahlung",
                }
            ],
        }

        calendar = build_due_date_calendar(current_bescheid)
        february_entries = calendar["months"][0]["entries"]

        self.assertEqual(len(february_entries), 2)
        self.assertEqual([entry["date"] for entry in february_entries], ["2025-02-15", "2025-02-15"])

    def test_build_due_date_calendar_marks_missing_amount_neutrally(self):
        current_bescheid = {
            "amount_due": None,
            "due_dates": "2025-02-15",
            "payment_classification": {"type": "Nachzahlung"},
            "advance_payments": [],
        }

        calendar = build_due_date_calendar(current_bescheid)
        entry = calendar["months"][0]["entries"][0]

        self.assertEqual(entry["amount"], "Betrag nicht gefunden")
        self.assertIn("Betrag nicht gefunden", entry["notes"])

    def test_build_due_date_calendar_marks_missing_payment_type_neutrally(self):
        current_bescheid = {
            "amount_due": "630.00",
            "due_dates": "2025-02-15",
            "payment_classification": {},
            "advance_payments": [],
        }

        calendar = build_due_date_calendar(current_bescheid)
        entry = calendar["months"][0]["entries"][0]

        self.assertEqual(entry["payment_type"], "Zahlungsart nicht eindeutig bestimmbar")
        self.assertIn("Zahlungsart nicht eindeutig bestimmbar", entry["notes"])

    def test_build_due_date_calendar_returns_empty_state_without_due_dates(self):
        current_bescheid = {
            "amount_due": "630.00",
            "due_dates": None,
            "payment_classification": {"type": "Nachzahlung"},
            "advance_payments": [],
        }

        calendar = build_due_date_calendar(current_bescheid)

        self.assertFalse(calendar["has_entries"])
        self.assertEqual(calendar["months"], [])
        self.assertEqual(calendar["undated_items"], [])
        self.assertIn("keine verwertbaren Fälligkeitstermine", calendar["empty_message"])

    def test_build_due_date_calendar_keeps_unparseable_dates_out_of_month_entries(self):
        current_bescheid = {
            "amount_due": "630.00",
            "due_dates": "kein-datum",
            "payment_classification": {"type": "Nachzahlung"},
            "advance_payments": [],
        }

        calendar = build_due_date_calendar(current_bescheid)

        self.assertFalse(calendar["has_entries"])
        self.assertEqual(calendar["months"], [])
        self.assertEqual(len(calendar["undated_items"]), 1)
        self.assertIn("Fälligkeitstermin nicht verwertbar", calendar["undated_items"][0]["notes"])

    def test_create_ics_export_contains_calendar_boundaries(self):
        calendar = build_due_date_calendar(
            {
                "amount_due": "630.00",
                "due_dates": "2025-02-15",
                "payment_classification": {"type": "Nachzahlung"},
                "advance_payments": [],
            }
        )

        ics_content = create_ics_export(calendar)

        self.assertTrue(ics_content.startswith("BEGIN:VCALENDAR\r\n"))
        self.assertIn("END:VCALENDAR\r\n", ics_content)
        self.assertIn("VERSION:2.0\r\n", ics_content)

    def test_create_ics_export_writes_one_event_for_one_due_date(self):
        calendar = build_due_date_calendar(
            {
                "amount_due": "630.00",
                "due_dates": "2025-02-15",
                "payment_classification": {"type": "Nachzahlung"},
                "advance_payments": [],
            }
        )

        ics_content = create_ics_export(calendar)

        self.assertEqual(ics_content.count("BEGIN:VEVENT"), 1)
        self.assertEqual(ics_content.count("END:VEVENT"), 1)

    def test_create_ics_export_writes_multiple_events_for_multiple_due_dates(self):
        calendar = build_due_date_calendar(
            {
                "amount_due": "630.00",
                "due_dates": "2025-02-15, 2025-03-15",
                "payment_classification": {"type": "Nachzahlung"},
                "advance_payments": [],
            }
        )

        ics_content = create_ics_export(calendar)

        self.assertEqual(ics_content.count("BEGIN:VEVENT"), 2)
        self.assertIn("DTSTART;VALUE=DATE:20250215", ics_content)
        self.assertIn("DTSTART;VALUE=DATE:20250315", ics_content)

    def test_build_ics_event_contains_required_lines(self):
        event = build_ics_event(
            {
                "date": "2025-02-15",
                "display_date": "15.02.2025",
                "amount": "630,00 EUR",
                "payment_type": "Nachzahlung",
            },
            1,
        )
        event_content = "\r\n".join(event)

        self.assertIn("BEGIN:VEVENT", event)
        self.assertIn("DTSTART;VALUE=DATE:20250215", event)
        self.assertIn("SUMMARY:Gewerbesteuer: Nachzahlung", event)
        self.assertIn("DESCRIPTION:", event_content)
        self.assertIn("UID:", event_content)
        self.assertIn("END:VEVENT", event)

    def test_format_ics_date_uses_yyyymmdd_format(self):
        self.assertEqual(format_ics_date("2025-02-15"), "20250215")
        self.assertEqual(format_ics_date("15.02.2025"), "20250215")
        self.assertIsNone(format_ics_date("kein-datum"))

    def test_escape_ics_text_escapes_special_characters(self):
        self.assertEqual(
            escape_ics_text("A,B;C\\D\nE"),
            "A\\,B\\;C\\\\D\\nE",
        )

    def test_create_ics_export_handles_missing_optional_values(self):
        calendar = {
            "has_entries": True,
            "months": [
                {
                    "key": "2025-02",
                    "label": "Februar 2025",
                    "entries": [{"date": "2025-02-15"}],
                }
            ],
            "undated_items": [],
            "empty_message": "",
        }

        ics_content = create_ics_export(calendar)

        self.assertIn("BEGIN:VEVENT", ics_content)
        self.assertIn("DTSTART;VALUE=DATE:20250215", ics_content)
        self.assertIn("Betrag nicht gefunden", ics_content)

    def test_create_ics_export_contains_no_raw_xml_debug_or_parser_details(self):
        calendar = build_due_date_calendar(
            {
                "amount_due": "630.00",
                "due_dates": "2025-02-15",
                "payment_classification": {"type": "Nachzahlung"},
                "advance_payments": [],
            }
        )

        ics_content = create_ics_export(calendar)

        self.assertNotIn("<nachricht", ics_content)
        self.assertNotIn("Traceback", ics_content)
        self.assertNotIn("DEBUG", ics_content)
        self.assertNotIn("XMLParser", ics_content)

    def test_create_ics_export_returns_none_without_usable_due_dates(self):
        calendar = build_due_date_calendar(
            {
                "amount_due": "630.00",
                "due_dates": None,
                "payment_classification": {"type": "Nachzahlung"},
                "advance_payments": [],
            }
        )

        self.assertIsNone(create_ics_export(calendar))

    def test_classify_liquidity_period_uses_fixed_thresholds(self):
        from datetime import date
        reference_date = date(2025, 1, 15)

        self.assertEqual(
            classify_liquidity_period("2025-01-15", reference_date)["key"],
            "due_now",
        )
        self.assertEqual(
            classify_liquidity_period("2025-02-14", reference_date)["key"],
            "within_30_days",
        )
        self.assertEqual(
            classify_liquidity_period("2025-03-16", reference_date)["key"],
            "within_90_days",
        )
        self.assertEqual(
            classify_liquidity_period("2025-05-01", reference_date)["key"],
            "later",
        )
        self.assertEqual(
            classify_liquidity_period(None, reference_date)["key"],
            "without_date",
        )

    def test_build_liquidity_impact_groups_payments_by_period(self):
        from datetime import date
        reference_date = date(2025, 1, 15)
        current_bescheid = {
            "amount_due": "630.00",
            "due_dates": "2025-01-15, 2025-02-14, 2025-03-16, 2025-05-01",
            "payment_classification": {"type": "Nachzahlung"},
            "advance_payments": [],
        }

        liquidity_impact = build_liquidity_impact(current_bescheid, reference_date)
        groups_by_key = {
            group["key"]: group
            for group in liquidity_impact["groups"]
        }

        self.assertEqual(len(groups_by_key["due_now"]["items"]), 1)
        self.assertEqual(len(groups_by_key["within_30_days"]["items"]), 1)
        self.assertEqual(len(groups_by_key["within_90_days"]["items"]), 1)
        self.assertEqual(len(groups_by_key["later"]["items"]), 1)
        self.assertEqual(liquidity_impact["reference_date"], "15.01.2025")

    def test_build_liquidity_impact_sums_only_positive_amounts(self):
        from datetime import date
        reference_date = date(2025, 1, 15)
        current_bescheid = {
            "amount_due": "100.00",
            "due_dates": "2025-02-14",
            "payment_classification": {"type": "Nachzahlung"},
            "advance_payments": [
                {
                    "amount": "200.00",
                    "due_date": "2025-02-14",
                    "period": "2025",
                    "type": "Vorauszahlung",
                }
            ],
        }

        liquidity_impact = build_liquidity_impact(current_bescheid, reference_date)
        within_30_days = next(
            group
            for group in liquidity_impact["groups"]
            if group["key"] == "within_30_days"
        )

        self.assertEqual(within_30_days["total_burden"], "300,00 EUR")

    def test_build_liquidity_impact_does_not_count_refunds_as_burden(self):
        from datetime import date
        reference_date = date(2025, 1, 15)
        current_bescheid = {
            "amount_due": "-50.00",
            "due_dates": "2025-02-14",
            "payment_classification": {"type": "Erstattung"},
            "advance_payments": [],
        }

        liquidity_impact = build_liquidity_impact(current_bescheid, reference_date)
        within_30_days = next(
            group
            for group in liquidity_impact["groups"]
            if group["key"] == "within_30_days"
        )

        self.assertEqual(within_30_days["total_burden"], "0,00 EUR")
        self.assertEqual(within_30_days["items"][0]["impact"], "relief")

    def test_build_liquidity_impact_does_not_count_zero_amount_as_burden(self):
        from datetime import date
        reference_date = date(2025, 1, 15)
        current_bescheid = {
            "amount_due": "0.00",
            "due_dates": "2025-02-14",
            "payment_classification": {"type": "Keine Zahlung"},
            "advance_payments": [],
        }

        liquidity_impact = build_liquidity_impact(current_bescheid, reference_date)
        within_30_days = next(
            group
            for group in liquidity_impact["groups"]
            if group["key"] == "within_30_days"
        )

        self.assertEqual(within_30_days["total_burden"], "0,00 EUR")
        self.assertEqual(within_30_days["items"][0]["impact"], "neutral")

    def test_build_liquidity_impact_marks_missing_date_or_amount_neutrally(self):
        from datetime import date
        reference_date = date(2025, 1, 15)
        current_bescheid = {
            "amount_due": None,
            "due_dates": "2025-02-14",
            "payment_classification": {"type": "Nicht eindeutig bestimmbar"},
            "advance_payments": [
                {
                    "amount": "147.00",
                    "due_date": None,
                    "period": "2025",
                    "type": "Vorauszahlung",
                }
            ],
        }

        liquidity_impact = build_liquidity_impact(current_bescheid, reference_date)
        groups_by_key = {
            group["key"]: group
            for group in liquidity_impact["groups"]
        }

        missing_amount_item = groups_by_key["within_30_days"]["items"][0]
        missing_date_item = groups_by_key["without_date"]["items"][0]

        self.assertEqual(missing_amount_item["impact"], "neutral")
        self.assertIn("Betrag", missing_amount_item["notice"])
        self.assertEqual(missing_date_item["impact"], "neutral")
        self.assertIn("Fälligkeit", missing_date_item["notice"])

    def test_format_euro_value_uses_german_currency_format(self):
        self.assertEqual(format_euro_value(Decimal("630")), "630,00 EUR")
        self.assertEqual(format_euro_value(Decimal("1234.5")), "1.234,50 EUR")

    def test_create_csv_export_contains_stable_columns_and_summary_values(self):
        report_data = {
            "summary_items": [
                {"label": "Nachrichtentyp", "value": "Generische Gewerbesteuernachricht"},
                {"label": "Gemeinde / Kommune", "value": "Stadt Musterhausen"},
                {"label": "Steuerjahr / Erhebungszeitraum", "value": "2023"},
                {"label": "Zahlbetrag", "value": "630.00"},
                {"label": "Zahlungsart", "value": "Nachzahlung"},
                {"label": "Gewerbesteuermessbetrag", "value": "150.00"},
                {"label": "Hebesatz", "value": "420"},
                {"label": "Fälligkeiten", "value": "2025-02-15"},
            ],
            "status_indicator": {
                "label": "Frist beachten",
                "message": "Bitte beachten Sie mögliche Fristen.",
            },
            "notice_items": [],
            "advance_payments": [],
            "change_comparison_items": [],
        }

        csv_content = create_csv_export(report_data)
        reader = csv.DictReader(StringIO(csv_content), delimiter=";")
        rows = list(reader)

        self.assertEqual(reader.fieldnames, CSV_EXPORT_COLUMNS)
        self.assertEqual(rows[0]["Datensatztyp"], "Zusammenfassung")
        self.assertEqual(rows[0]["Nachrichtentyp"], "Generische Gewerbesteuernachricht")
        self.assertEqual(rows[0]["Gemeinde / Kommune"], "Stadt Musterhausen")
        self.assertEqual(rows[0]["Steuerjahr / Erhebungszeitraum"], "2023")
        self.assertEqual(rows[0]["Zahlbetrag"], "630.00")
        self.assertEqual(rows[0]["Hinweis / Status"], "Frist beachten")
        self.assertNotIn("None", csv_content)

    def test_create_csv_export_writes_multiple_due_dates_and_advance_payments_as_rows(self):
        report_data = {
            "summary_items": [
                {"label": "Gemeinde / Kommune", "value": "Stadt Musterhausen"},
                {"label": "Steuerjahr / Erhebungszeitraum", "value": "2023"},
                {"label": "Zahlbetrag", "value": "630.00"},
                {"label": "Zahlungsart", "value": "Vorauszahlung"},
                {"label": "Gewerbesteuermessbetrag", "value": "150.00"},
                {"label": "Hebesatz", "value": "420"},
                {"label": "Fälligkeiten", "value": "2025-02-15, 2025-03-15"},
            ],
            "status_indicator": None,
            "notice_items": [],
            "advance_payments": [
                {
                    "amount": "147.00",
                    "due_date": "2025-04-15",
                    "period": "2023",
                    "type": "Vorauszahlung",
                },
                {
                    "amount": "148.00",
                    "due_date": "2025-05-15",
                    "period": "2023",
                    "type": "Vorauszahlung",
                },
            ],
            "change_comparison_items": [],
        }

        csv_content = create_csv_export(report_data)
        reader = csv.DictReader(StringIO(csv_content), delimiter=";")
        rows = list(reader)

        record_types = [row["Datensatztyp"] for row in rows]

        self.assertEqual(record_types.count("Fälligkeit"), 2)
        self.assertEqual(record_types.count("Vorauszahlung"), 2)
        self.assertTrue(any(row["Fälligkeit"] == "2025-02-15" for row in rows))
        self.assertTrue(any(row["Betrag"] == "147.00" for row in rows))

    def test_create_csv_export_keeps_utf8_special_characters(self):
        report_data = {
            "summary_items": [
                {"label": "Gemeinde / Kommune", "value": "Stadt München"},
                {"label": "Steuerjahr / Erhebungszeitraum", "value": "2023"},
                {"label": "Zahlbetrag", "value": "100.00"},
                {"label": "Zahlungsart", "value": "Nachzahlung"},
                {"label": "Gewerbesteuermessbetrag", "value": "25.00"},
                {"label": "Hebesatz", "value": "490"},
                {"label": "Fälligkeiten", "value": "2025-02-15"},
            ],
            "status_indicator": {
                "label": "Warnung / Auffälligkeit",
                "message": "Der Bescheid enthält Auffälligkeiten.",
            },
            "notice_items": [],
            "advance_payments": [],
            "change_comparison_items": [],
        }

        csv_content = create_csv_export(report_data)

        self.assertIn("Stadt München", csv_content)
        self.assertIn("Fälligkeit", csv_content)
        self.assertIn("Warnung / Auffälligkeit", csv_content)


class XGewerbesteuerPrivacyModeTests(SimpleTestCase):
    def test_anonymize_value_keeps_empty_and_missing_values_readable(self):
        self.assertEqual(anonymize_value(""), "")
        self.assertEqual(anonymize_value(None), None)
        self.assertEqual(anonymize_value("Nicht gefunden"), "Nicht gefunden")

    def test_anonymize_value_handles_short_and_already_masked_values(self):
        self.assertEqual(anonymize_value("AB"), "••")
        self.assertEqual(anonymize_value("••••1234"), "••••1234")

    def test_anonymize_value_keeps_last_four_characters_for_long_values(self):
        self.assertEqual(anonymize_value("1234567890000"), "••••0000")
        self.assertEqual(anonymize_value("Stadt Musterhausen"), "••••usen")

    def test_sensitive_labels_are_defined_centrally(self):
        self.assertTrue(is_sensitive_label("Gemeinde / Kommune"))
        self.assertTrue(is_sensitive_label("Steuernummer"))
        self.assertTrue(is_sensitive_label("Nachrichten-ID"))
        self.assertFalse(is_sensitive_label("Zahlbetrag"))
        self.assertFalse(is_sensitive_label("Hebesatz"))

    def test_anonymize_result_context_masks_display_values_without_changing_source(self):
        context = {
            "uploaded_file_name": "GEWST-0010-12345678-1234567890000.xml",
            "current_bescheid": {
                "file_name": "GEWST-0010-12345678-1234567890000.xml",
                "municipality": "Stadt Musterhausen",
                "tax_period": "2025",
                "amount_due": "630.00",
            },
            "summary_items": [
                {"label": "Gemeinde / Kommune", "value": "Stadt Musterhausen"},
                {"label": "Steuerjahr / Erhebungszeitraum", "value": "2025"},
                {"label": "Zahlbetrag", "value": "630.00"},
            ],
        }

        anonymized = anonymize_result_context(context)

        self.assertEqual(
            context["current_bescheid"]["municipality"],
            "Stadt Musterhausen",
        )
        self.assertEqual(
            anonymized["current_bescheid"]["municipality"],
            "••••usen",
        )
        self.assertEqual(anonymized["summary_items"][1]["value"], "2025")
        self.assertEqual(anonymized["summary_items"][2]["value"], "630.00")
        self.assertTrue(anonymized["privacy_mode_enabled"])


class XGewerbesteuerXsdValidationTests(SimpleTestCase):
    def test_generate_error_id_uses_short_neutral_format(self):
        error_id = generate_error_id()

        self.assertRegex(error_id, r"^XGST-[A-Z0-9]{8}$")
        self.assertNotIn("1234567890000", error_id)
        self.assertNotIn("bescheid", error_id.lower())
        self.assertNotIn("<", error_id)

    def test_generate_error_id_creates_distinguishable_values(self):
        error_ids = {generate_error_id() for _ in range(20)}

        self.assertGreater(len(error_ids), 1)

    def test_upload_issue_for_wrong_file_extension_is_structured(self):
        issue = get_upload_issue(uploaded_xml("bescheid.pdf", b"<nachricht/>"))

        self.assertIsInstance(issue, UploadValidationIssue)
        self.assertEqual(issue.code, "invalid_file_type")
        self.assertEqual(issue.group, "Falscher Dateityp")
        self.assertIn("XML-Datei", issue.message)
        self.assertIn("XML-Datei", issue.next_action)

    def test_upload_issue_for_oversized_file_is_structured(self):
        issue = get_upload_issue(
            uploaded_xml("bescheid.xml", b"x" * (MAX_UPLOAD_SIZE_BYTES + 1))
        )

        self.assertIsInstance(issue, UploadValidationIssue)
        self.assertEqual(issue.code, "file_too_large")
        self.assertIn("Datei zu", issue.group)
        self.assertIn("5 MB", issue.detail)
        self.assertIn("kleinere XML-Datei", issue.next_action)

    def test_valid_fixture_matches_an_xgewerbesteuer_schema(self):
        is_valid, schema_name, schema_error = validate_xml_against_xsd(
            VALID_BESCHEID_FIXTURE.read_bytes()
        )

        self.assertTrue(is_valid)
        self.assertIn(
            schema_name,
            ["xunternehmen-gewerbesteuer.xsd", "gewerbesteuer.xsd"],
        )
        self.assertIsNone(schema_error)

    def test_malformed_xml_returns_user_safe_error(self):
        is_valid, schema_name, schema_error = validate_xml_against_xsd(b"<nachricht>")

        self.assertFalse(is_valid)
        self.assertIsNone(schema_name)
        self.assertEqual(schema_error, "Die XML-Datei ist nicht wohlgeformt.")

    def test_well_formed_but_schema_invalid_xml_reports_xsd_error(self):
        is_valid, schema_name, schema_error = validate_xml_against_xsd(b"<nachricht/>")

        self.assertFalse(is_valid)
        self.assertIsNone(schema_name)
        self.assertIn("gewerbesteuer.xsd", schema_error)
        self.assertNotIn("<nachricht", schema_error)
        self.assertNotIn(str(FIXTURES_DIR), schema_error)
        self.assertNotIn("Traceback", schema_error)


class SavedBescheidUploadTests(TestCase):
    def create_session(self):
        session = self.client.session
        session.save()
        return session.session_key

    def create_saved_upload(self, session_key=None, **overrides):
        defaults = {
            "session_key": session_key or self.create_session(),
            "file_name": "bescheid.xml",
            "file_size": 128,
            "municipality": "Stadt Musterhausen",
            "tax_period": "2025",
            "amount_due": "630.00",
            "payment_type": "Nachzahlung",
            "trade_tax_assessment_amount": "150.00",
            "assessment_rate": "420",
            "due_dates": "2025-02-15",
            "advance_payments": [],
            "summary_items": [
                {"label": "Zahlbetrag", "value": "630.00"},
            ],
            "result_data": processed_bescheid_with_due_date()["bescheid"],
        }
        defaults.update(overrides)

        return SavedBescheidUpload.objects.create(**defaults)

    def test_model_can_store_structured_saved_upload(self):
        saved_upload = self.create_saved_upload(
            advance_payments=[
                {
                    "amount": "147.00",
                    "due_date": "2025-03-15",
                    "period": "2025",
                    "type": "Vorauszahlung",
                }
            ],
            summary_items=[{"label": "Gemeinde / Kommune", "value": "Stadt Musterhausen"}],
        )

        self.assertEqual(SavedBescheidUpload.objects.count(), 1)
        self.assertEqual(saved_upload.advance_payments[0]["amount"], "147.00")
        self.assertEqual(saved_upload.summary_items[0]["label"], "Gemeinde / Kommune")

    def test_model_string_is_readable(self):
        saved_upload = self.create_saved_upload(file_name="muster.xml", tax_period="2025")

        self.assertEqual(str(saved_upload), "2025 - muster.xml")

    def test_upload_is_saved_only_when_checkbox_enabled(self):
        response = self.client.post(
            reverse("xgewerbesteuer_upload"),
            data={
                "bescheide": uploaded_xml(
                    VALID_BESCHEID_FIXTURE.name,
                    VALID_BESCHEID_FIXTURE.read_bytes(),
                ),
                "save_upload": "on",
            },
            follow=True,
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(SavedBescheidUpload.objects.count(), 1)
        self.assertContains(response, "Die Auswertung wurde gespeichert")

    def test_upload_without_checkbox_is_not_persisted(self):
        response = self.client.post(
            reverse("xgewerbesteuer_upload"),
            data={
                "bescheide": uploaded_xml(
                    VALID_BESCHEID_FIXTURE.name,
                    VALID_BESCHEID_FIXTURE.read_bytes(),
                ),
            },
            follow=True,
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(SavedBescheidUpload.objects.count(), 0)

    def test_saved_upload_does_not_store_original_xml(self):
        self.client.post(
            reverse("xgewerbesteuer_upload"),
            data={
                "bescheide": uploaded_xml(
                    VALID_BESCHEID_FIXTURE.name,
                    VALID_BESCHEID_FIXTURE.read_bytes(),
                ),
                "save_upload": "on",
            },
            follow=True,
        )

        saved_upload = SavedBescheidUpload.objects.get()
        stored_content = str(saved_upload.result_data)

        self.assertNotIn("<nachricht", stored_content)
        self.assertNotIn("XMLParser", stored_content)
        self.assertNotIn("Traceback", stored_content)

    def test_saved_uploads_are_listed_for_current_session(self):
        session_key = self.create_session()
        saved_upload = self.create_saved_upload(session_key=session_key)

        response = self.client.get(reverse("xgewerbesteuer_dashboard"))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Gespeicherte Auswertungen")
        self.assertContains(response, saved_upload.file_name)

    def test_saved_uploads_from_other_session_are_hidden(self):
        self.create_session()
        self.create_saved_upload(session_key="other-session", file_name="fremd.xml")

        response = self.client.get(reverse("xgewerbesteuer_dashboard"))

        self.assertEqual(response.status_code, 200)
        self.assertNotContains(response, "fremd.xml")
        self.assertContains(
            response,
            "Keine gespeicherten Auswertungen",
        )

    def test_saved_upload_can_be_loaded(self):
        session_key = self.create_session()
        saved_upload = self.create_saved_upload(session_key=session_key)

        response = self.client.post(
            reverse("xgewerbesteuer_load_saved"),
            data={
                "saved_upload_id": str(saved_upload.id),
            },
            follow=True,
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Die gespeicherte Auswertung wurde erneut geöffnet.")
        self.assertContains(response, "Zusammenfassung")
        self.assertContains(response, "Plausibilitätsprüfung")

    def test_saved_upload_from_other_session_cannot_be_loaded(self):
        self.create_session()
        saved_upload = self.create_saved_upload(session_key="other-session")

        response = self.client.post(
            reverse("xgewerbesteuer_load_saved"),
            data={
                "saved_upload_id": str(saved_upload.id),
            },
            follow=True,
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "konnte nicht gefunden werden")
        self.assertNotContains(response, "Zusammenfassung")

    def test_saved_upload_can_be_deleted(self):
        session_key = self.create_session()
        saved_upload = self.create_saved_upload(session_key=session_key)

        response = self.client.post(
            reverse("xgewerbesteuer_delete_saved"),
            data={
                "saved_upload_id": str(saved_upload.id),
            },
            follow=True,
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(SavedBescheidUpload.objects.count(), 0)
        self.assertContains(response, "Die gespeicherte Auswertung wurde gelöscht.")

    def test_saved_upload_from_other_session_cannot_be_deleted(self):
        self.create_session()
        saved_upload = self.create_saved_upload(session_key="other-session")

        response = self.client.post(
            reverse("xgewerbesteuer_delete_saved"),
            data={
                "saved_upload_id": str(saved_upload.id),
            },
            follow=True,
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(SavedBescheidUpload.objects.count(), 1)
        self.assertContains(response, "konnte nicht gefunden werden")

    def test_failed_save_shows_user_safe_error(self):
        with patch(
            "xgewerbesteuer.services.bescheid.SavedBescheidUpload.objects.create",
            side_effect=DatabaseError,
        ):
            response = self.client.post(
                reverse("xgewerbesteuer_upload"),
                data={
                    "bescheide": uploaded_xml(
                        VALID_BESCHEID_FIXTURE.name,
                        VALID_BESCHEID_FIXTURE.read_bytes(),
                    ),
                    "save_upload": "on",
                },
                follow=True,
            )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Die Auswertung konnte nicht gespeichert werden.")
        self.assertNotContains(response, "Traceback")

    def test_saved_upload_list_contains_expected_columns(self):
        self.create_saved_upload(session_key=self.create_session())

        response = self.client.get(reverse("xgewerbesteuer_dashboard"))

        self.assertContains(response, "Gespeichert am")
        self.assertContains(response, "Dateiname")
        self.assertContains(response, "Steuerjahr")
        self.assertContains(response, "Gemeinde")
        self.assertContains(response, "Zahlbetrag")

    def test_saved_upload_list_contains_open_and_delete_actions(self):
        self.create_saved_upload(session_key=self.create_session())

        response = self.client.get(reverse("xgewerbesteuer_dashboard"))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Öffnen")
        self.assertContains(response, "Löschen")
        self.assertContains(response, 'name="saved_upload_id"')

    def test_empty_saved_upload_state_is_visible(self):
        response = self.client.get(reverse("xgewerbesteuer_dashboard"))

        self.assertEqual(response.status_code, 200)
        self.assertContains(
            response,
            "Keine gespeicherten Auswertungen",
        )

    def test_saved_upload_load_keeps_downloads_working_when_data_is_available(self):
        self.client.post(
            reverse("xgewerbesteuer_upload"),
            data={
                "bescheide": uploaded_xml("bescheid.xml", b"<nachricht/>"),
                "save_upload": "on",
            },
        )

        with patch(
            "xgewerbesteuer.views.process_uploaded_bescheid",
            return_value=processed_bescheid_with_due_date(),
        ):
            self.client.post(
                reverse("xgewerbesteuer_upload"),
                data={
                    "bescheide": uploaded_xml("bescheid.xml", b"<nachricht/>"),
                    "save_upload": "on",
                },
                follow=True,
            )

        saved_upload = SavedBescheidUpload.objects.last()
        self.client.post(
            reverse("xgewerbesteuer_load_saved"),
            data={
                "saved_upload_id": str(saved_upload.id),
            },
            follow=True,
        )

        self.assertEqual(self.client.get(reverse("xgewerbesteuer_pdf_report")).status_code, 200)
        self.assertEqual(self.client.get(reverse("xgewerbesteuer_csv_export")).status_code, 200)
        self.assertEqual(self.client.get(reverse("xgewerbesteuer_ics_export")).status_code, 200)

    def test_saved_upload_keeps_message_type_after_reopening(self):
        response = self.client.post(
            reverse("xgewerbesteuer_upload"),
            data={
                "bescheide": uploaded_xml(
                    VALID_BESCHEID_FIXTURE.name,
                    VALID_BESCHEID_FIXTURE.read_bytes(),
                ),
                "save_upload": "on",
            },
            follow=True,
        )

        self.assertEqual(response.status_code, 200)
        saved_upload = SavedBescheidUpload.objects.last()
        self.assertEqual(
            saved_upload.result_data["current_bescheid"]["message_type_label"],
            "Generische Gewerbesteuernachricht",
        )

        reopened_response = self.client.post(
            reverse("xgewerbesteuer_load_saved"),
            data={"saved_upload_id": str(saved_upload.id)},
            follow=True,
        )

        self.assertEqual(reopened_response.status_code, 200)
        self.assertEqual(
            reopened_response.context["current_bescheid"]["message_type_label"],
            "Generische Gewerbesteuernachricht",
        )
        self.assertContains(reopened_response, "Generische Gewerbesteuernachricht")


class XGewerbesteuerUploadViewTests(SimpleTestCase):
    databases = {"default"}

    def test_start_page_renders_upload_form_and_expected_summary_scope(self):
        response = self.client.get(reverse("xgewerbesteuer_upload"))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Gewerbesteuer-Assistent")
        self.assertContains(response, 'name="bescheide"')
        self.assertContains(response, 'name="save_upload"')
        self.assertContains(response, 'multiple')
        self.assertContains(response, 'accept=".xml"')
        self.assertContains(response, "Browser-Session speichern")
        self.assertContains(response, "Original-XML-Dateien")
        self.assertContains(response, 'name="viewport"')
        self.assertContains(response, "app.css")
        self.assertContains(response, "@kern-ux/native")
        self.assertContains(response, "page-header")
        self.assertContains(response, "card")
        self.assertContains(response, "form-group")
        self.assertContains(response, "btn btn--primary")

    def test_upload_form_contains_required_elements(self):
        response = self.client.get(reverse("xgewerbesteuer_upload"))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'type="file"')
        self.assertContains(response, 'type="submit"')
        self.assertContains(response, reverse("xgewerbesteuer_demo"))
        self.assertContains(response, "Demo-Beispielfall")

    def test_demo_entry_loads_fixture_result_with_demo_notice(self):
        response = self.client.get(reverse("xgewerbesteuer_demo"), follow=True)

        summary_items = {
            item["label"]: item["value"] for item in response.context["summary_items"]
        }

        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "xgewerbesteuer/results.html")
        self.assertTrue(response.context["is_demo"])
        self.assertIn("Demo-Beispielfall", response.context["demo_notice"])
        self.assertEqual(summary_items["Gemeinde / Kommune"], "Stadt Musterhausen")
        self.assertEqual(summary_items["Steuerjahr / Erhebungszeitraum"], "2023")
        self.assertEqual(summary_items["Zahlbetrag"], "630.00")
        self.assertIn("previous_bescheid", response.context)
        self.assertContains(response, "Demo-Beispielfall")
        self.assertContains(response, "fiktiven")
        self.assertContains(response, "keine echten Bescheiddaten")
        self.assertContains(response, "Zusammenfassung")

    def test_demo_entry_uses_fictional_fixture_files(self):
        response = self.client.get(reverse("xgewerbesteuer_demo"), follow=True)

        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.context["is_demo"])
        self.assertEqual(response.context["all_bescheide_count"], 2)
        self.assertTrue(
            response.context["uploaded_file_name"].startswith("GEWST-0010-12345678")
        )
        self.assertIn("1234567890000", response.context["uploaded_file_name"])

    def test_demo_entry_shows_understandable_error_when_fixture_processing_fails(self):
        with patch(
            "xgewerbesteuer.views.process_uploaded_bescheid",
            return_value={
                "is_valid": False,
                "message": "Die Demo-Datei konnte nicht verarbeitet werden.",
                "details": [],
            },
        ):
            response = self.client.get(reverse("xgewerbesteuer_demo"))

        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "xgewerbesteuer/upload.html")
        self.assertContains(response, "Demo-Beispielfall konnte nicht geladen werden")
        self.assertContains(response, 'name="bescheide"')

    def test_post_without_file_shows_missing_file_error(self):
        response = self.client.post(reverse("xgewerbesteuer_upload"), data={})

        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            response.context["upload_error"],
            "Bitte wählen Sie mindestens eine XML-Datei aus.",
        )
        self.assertNotIn("uploaded_file_name", response.context)
        self.assertNotIn("status_indicator", response.context)

    def test_post_without_file_clears_stale_export_sessions(self):
        session = self.client.session
        session[PDF_REPORT_SESSION_KEY] = {"stale": True}
        session[CSV_EXPORT_SESSION_KEY] = {"stale": True}
        session[ICS_EXPORT_SESSION_KEY] = "stale calendar"
        session.save()

        self.client.post(reverse("xgewerbesteuer_upload"), data={})

        self.assertNotIn(PDF_REPORT_SESSION_KEY, self.client.session)
        self.assertNotIn(CSV_EXPORT_SESSION_KEY, self.client.session)
        self.assertNotIn(ICS_EXPORT_SESSION_KEY, self.client.session)

    def test_post_rejects_non_xml_filename_before_parsing(self):
        response = self.client.post(
            reverse("xgewerbesteuer_upload"),
            data={"bescheide": uploaded_xml("bescheid.txt", b"<nachricht/>")},
        )

        self.assertEqual(response.status_code, 200)
        self.assertIn("upload_error", response.context)
        self.assertEqual(len(response.context["upload_errors"]), 1)
        self.assertEqual(
            response.context["upload_errors"][0]["message"],
            "Die hochgeladene Datei muss eine XML-Datei sein.",
        )
        self.assertEqual(
            response.context["upload_errors"][0]["details"][0]["code"],
            "invalid_file_type",
        )
        self.assertContains(response, "Falscher Dateityp")
        self.assertContains(response, "Nächster Schritt")
        self.assertNotIn("uploaded_file_name", response.context)

    def test_known_upload_error_keeps_concrete_message_and_adds_error_id(self):
        response = self.client.post(
            reverse("xgewerbesteuer_upload"),
            data={"bescheide": uploaded_xml("bescheid.txt", b"<nachricht/>")},
        )

        detail = response.context["upload_errors"][0]["details"][0]

        self.assertEqual(detail["code"], "invalid_file_type")
        self.assertEqual(
            detail["message"],
            "Die hochgeladene Datei muss eine XML-Datei sein.",
        )
        self.assertRegex(detail["error_id"], r"^XGST-[A-Z0-9]{8}$")
        self.assertContains(response, "Die hochgeladene Datei muss eine XML-Datei sein.")
        self.assertContains(response, detail["error_id"])

    def test_post_rejects_oversized_xml_before_parsing(self):
        response = self.client.post(
            reverse("xgewerbesteuer_upload"),
            data={
                "bescheide": uploaded_xml(
                    "bescheid.xml",
                    b"x" * (MAX_UPLOAD_SIZE_BYTES + 1),
                )
            },
        )

        self.assertEqual(response.status_code, 200)
        self.assertIn("upload_error", response.context)
        self.assertEqual(len(response.context["upload_errors"]), 1)
        self.assertEqual(
            response.context["upload_errors"][0]["message"],
            "Die hochgeladene Datei ist zu groß.",
        )
        self.assertEqual(
            response.context["upload_errors"][0]["details"][0]["code"],
            "file_too_large",
        )
        self.assertContains(response, "Datei zu groß")
        self.assertContains(response, "kleinere XML-Datei")
        self.assertNotIn("uploaded_file_name", response.context)

    def test_post_rejects_malformed_xml_with_user_safe_message(self):
        response = self.client.post(
            reverse("xgewerbesteuer_upload"),
            data={"bescheide": uploaded_xml("bescheid.xml", b"<nachricht>")},
        )

        self.assertEqual(response.status_code, 200)
        self.assertIn("upload_error", response.context)
        self.assertEqual(len(response.context["upload_errors"]), 1)
        self.assertEqual(
            response.context["upload_errors"][0]["message"],
            "Die XML-Datei ist nicht wohlgeformt.",
        )
        self.assertEqual(
            response.context["upload_errors"][0]["details"][0]["code"],
            "malformed_xml",
        )
        self.assertContains(response, "Nicht wohlgeformtes XML")
        self.assertContains(response, "erneut aus dem Fachverfahren")
        self.assertNotIn("uploaded_file_name", response.context)

    def test_post_schema_invalid_xml_shows_validation_error_not_success(self):
        session = self.client.session
        session[PDF_REPORT_SESSION_KEY] = {"stale": True}
        session[CSV_EXPORT_SESSION_KEY] = {"stale": True}
        session[ICS_EXPORT_SESSION_KEY] = "stale calendar"
        session.save()

        response = self.client.post(
            reverse("xgewerbesteuer_upload"),
            data={"bescheide": uploaded_xml("bescheid.xml", b"<nachricht/>")},
        )

        self.assertEqual(response.status_code, 200)
        self.assertNotIn("uploaded_file_name", response.context)
        self.assertNotIn("summary_items", response.context)
        self.assertNotIn("calculation_explanation", response.context)
        self.assertNotIn("validation_success", response.context)
        self.assertIn("upload_error", response.context)
        self.assertIn("upload_errors", response.context)
        self.assertEqual(
            response.context["upload_errors"][0]["details"][0]["code"],
            "xsd_validation_error",
        )
        self.assertContains(response, "XSD-Validierungsfehler")
        self.assertContains(response, "XGewerbesteuer-1.4-Datei")
        self.assertNotContains(response, "<nachricht")
        self.assertNotContains(response, "Traceback")
        self.assertNotContains(response, str(FIXTURES_DIR))
        self.assertNotIn(PDF_REPORT_SESSION_KEY, self.client.session)
        self.assertNotIn(CSV_EXPORT_SESSION_KEY, self.client.session)
        self.assertNotIn(ICS_EXPORT_SESSION_KEY, self.client.session)

    def test_post_rejects_xml_with_unsafe_entity_declaration(self):
        response = self.client.post(
            reverse("xgewerbesteuer_upload"),
            data={
                "bescheide": uploaded_xml(
                    "bescheid.xml",
                    b"""<?xml version="1.0"?>
                    <!DOCTYPE nachricht [
                      <!ENTITY xxe SYSTEM "file:///etc/passwd">
                    ]>
                    <nachricht>&xxe;</nachricht>""",
                )
            },
        )

        self.assertEqual(response.status_code, 200)
        self.assertIn("upload_error", response.context)
        self.assertEqual(len(response.context["upload_errors"]), 1)
        self.assertEqual(
            response.context["upload_errors"][0]["message"],
            "Die XML-Datei enthält aus Sicherheitsgründen nicht erlaubte XML-Inhalte.",
        )
        self.assertEqual(
            response.context["upload_errors"][0]["details"][0]["code"],
            "unsafe_xml",
        )
        self.assertContains(response, "Unsichere XML-Inhalte")
        self.assertContains(response, "ohne DOCTYPE")
        self.assertNotContains(response, "file:///etc/passwd")
        self.assertNotContains(response, "ENTITY xxe")

    def test_invalid_upload_details_are_semantically_findable_and_form_remains_usable(self):
        response = self.client.post(
            reverse("xgewerbesteuer_upload"),
            data={"bescheide": uploaded_xml("bescheid.xml", b"<nachricht>")},
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'role="alert"')
        self.assertContains(response, 'aria-labelledby="validation-details-heading"')
        self.assertContains(response, 'id="validation-details-heading"')
        self.assertContains(response, 'name="bescheide"')
        self.assertContains(response, 'type="submit"')
        self.assertNotContains(response, "Traceback")
        self.assertNotContains(response, "<nachricht>")

    def test_unexpected_upload_error_shows_support_id_without_raw_data(self):
        raw_xml = b"<nachricht><steuernummer>1234567890000</steuernummer></nachricht>"

        with patch(
            "xgewerbesteuer.views.process_uploaded_bescheid",
            side_effect=RuntimeError("Parser failed with C:\\temp\\bescheid.xml"),
        ):
            response = self.client.post(
                reverse("xgewerbesteuer_upload"),
                data={"bescheide": uploaded_xml("bescheid.xml", raw_xml)},
            )

        detail = response.context["upload_errors"][0]["details"][0]

        self.assertEqual(response.status_code, 200)
        self.assertEqual(detail["code"], "unexpected_import_error")
        self.assertRegex(detail["error_id"], r"^XGST-[A-Z0-9]{8}$")
        self.assertContains(response, detail["error_id"])
        self.assertContains(response, "Support")
        self.assertNotContains(response, "<steuernummer>")
        self.assertNotContains(response, "1234567890000")
        self.assertNotContains(response, "C:\\temp\\bescheid.xml")
        self.assertNotContains(response, "Traceback")

    def test_unexpected_upload_error_logs_support_id_without_sensitive_values(self):
        raw_xml = b"<nachricht><steuernummer>1234567890000</steuernummer></nachricht>"

        with patch(
            "xgewerbesteuer.views.process_uploaded_bescheid",
            side_effect=RuntimeError("Parser failed with C:\\temp\\bescheid.xml"),
        ):
            with self.assertLogs("xgewerbesteuer.services.support_errors", level="ERROR") as logs:
                response = self.client.post(
                    reverse("xgewerbesteuer_upload"),
                    data={"bescheide": uploaded_xml("bescheid.xml", raw_xml)},
                )

        detail = response.context["upload_errors"][0]["details"][0]
        log_output = "\n".join(logs.output)

        self.assertIn(detail["error_id"], log_output)
        self.assertIn("unexpected_import_error", log_output)
        self.assertNotIn("<steuernummer>", log_output)
        self.assertNotIn("1234567890000", log_output)
        self.assertNotIn("C:\\temp\\bescheid.xml", log_output)
        self.assertNotIn("Traceback", log_output)

    def test_post_valid_fixture_displays_summary_with_core_values(self):
        content = VALID_BESCHEID_FIXTURE.read_bytes()

        response = self.client.post(
            reverse("xgewerbesteuer_upload"),
            data={"bescheide": uploaded_xml(VALID_BESCHEID_FIXTURE.name, content)},
            follow=True,
        )

        summary_items = {
            item["label"]: item["value"] for item in response.context["summary_items"]
        }

        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            response.context["uploaded_file_name"],
            VALID_BESCHEID_FIXTURE.name,
        )
        self.assertEqual(summary_items["Nachrichtentyp"], "Generische Gewerbesteuernachricht")
        self.assertEqual(summary_items["Gemeinde / Kommune"], "Stadt Musterhausen")
        self.assertEqual(summary_items["Steuerjahr / Erhebungszeitraum"], "2023")
        self.assertEqual(summary_items["Zahlbetrag"], "630.00")
        self.assertEqual(summary_items["Zahlungsart"], "Nachzahlung")
        self.assertEqual(summary_items["Gewerbesteuermessbetrag"], "150.00")
        self.assertEqual(summary_items["Hebesatz"], "420")
        self.assertNotIn("validation_success", response.context)
        self.assertNotContains(response, "Validierungsdetails")
        self.assertNotContains(response, "XSD-Validierungsfehler")
        self.assertNotContains(response, "Die Datei wurde erfolgreich geprüft")
        self.assertEqual(response.context["message_type_label"], "Generische Gewerbesteuernachricht")
        self.assertContains(response, "Zusammenfassung")
        self.assertContains(response, "Nachrichtentyp")
        self.assertContains(response, "Generische Gewerbesteuernachricht")
        self.assertContains(response, "bescheide.gewerbesteuer.generisch.0010")
        self.assertContains(response, "Einordnung der Zahlung")
        self.assertContains(response, "Nachzahlung")
        self.assertIn("notice_items", response.context)
        self.assertContains(response, "Hinweise")
        self.assertContains(response, "Zahlbetrag beachten")
        self.assertContains(
            response,
            "Der Bescheid weist einen positiven Zahlbetrag von 630.00 aus.",
        )
        self.assertIn("status_indicator", response.context)
        self.assertEqual(response.context["status_indicator"]["status"], "deadline")
        self.assertContains(response, "Frist beachten")
        self.assertIn(PDF_REPORT_SESSION_KEY, self.client.session)
        self.assertContains(response, "PDF-Bericht")
        self.assertIn(CSV_EXPORT_SESSION_KEY, self.client.session)
        self.assertContains(response, "CSV-Export")

    def test_privacy_mode_masks_sensitive_values_in_html_and_keeps_core_values(self):
        content = VALID_BESCHEID_FIXTURE.read_bytes()

        self.client.post(
            reverse("xgewerbesteuer_upload"),
            data={"bescheide": uploaded_xml(VALID_BESCHEID_FIXTURE.name, content)},
            follow=True,
        )
        response = self.client.get(reverse("xgewerbesteuer_results") + "?privacy=1")

        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.context["privacy_mode_enabled"])
        self.assertContains(response, "Datenschutzmodus aktiv")
        self.assertContains(response, "••••")
        self.assertContains(response, "630.00")
        self.assertContains(response, "420")
        self.assertContains(response, "2023")
        self.assertNotContains(response, "Stadt Musterhausen")
        self.assertNotContains(response, VALID_BESCHEID_FIXTURE.name)

    def test_privacy_mode_masks_sensitive_values_in_csv_and_pdf_export_data(self):
        content = VALID_BESCHEID_FIXTURE.read_bytes()

        self.client.post(
            reverse("xgewerbesteuer_upload"),
            data={"bescheide": uploaded_xml(VALID_BESCHEID_FIXTURE.name, content)},
            follow=True,
        )
        self.client.get(reverse("xgewerbesteuer_results") + "?privacy=1")

        csv_response = self.client.get(reverse("xgewerbesteuer_csv_export"))
        csv_content = csv_response.content.decode("utf-8")
        pdf_report_data = self.client.session[PDF_REPORT_SESSION_KEY]

        self.assertEqual(csv_response.status_code, 200)
        self.assertIn("••••usen", csv_content)
        self.assertIn("630.00", csv_content)
        self.assertNotIn("Stadt Musterhausen", csv_content)
        self.assertNotIn(VALID_BESCHEID_FIXTURE.name, csv_content)
        self.assertEqual(pdf_report_data["uploaded_file_name"][-4:], ".xml")
        self.assertNotEqual(
            pdf_report_data["uploaded_file_name"],
            VALID_BESCHEID_FIXTURE.name,
        )
        self.assertNotIn(
            "Stadt Musterhausen",
            str(pdf_report_data.get("summary_items")),
        )

    def test_privacy_mode_does_not_change_plausibility_or_comparison_results(self):
        upload_response = self.client.post(
            reverse("xgewerbesteuer_upload"),
            data={
                "bescheide": [
                    uploaded_xml(
                        PREVIOUS_BESCHEID_FIXTURE.name,
                        PREVIOUS_BESCHEID_FIXTURE.read_bytes(),
                    ),
                    uploaded_xml(
                        VALID_BESCHEID_FIXTURE.name,
                        VALID_BESCHEID_FIXTURE.read_bytes(),
                    ),
                ],
            },
            follow=True,
        )
        original_plausibility = upload_response.context["plausibility_check"]
        original_changes = upload_response.context["change_comparison_items"]

        privacy_response = self.client.get(reverse("xgewerbesteuer_results") + "?privacy=1")

        self.assertEqual(
            privacy_response.context["plausibility_check"],
            original_plausibility,
        )
        self.assertEqual(
            privacy_response.context["change_comparison_items"],
            original_changes,
        )

    def test_valid_upload_uses_responsive_result_layout(self):
        content = VALID_BESCHEID_FIXTURE.read_bytes()

        response = self.client.post(
            reverse("xgewerbesteuer_upload"),
            data={"bescheide": uploaded_xml(VALID_BESCHEID_FIXTURE.name, content)},
            follow=True,
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "table-wrapper")
        self.assertContains(response, "table")
        self.assertContains(response, "download-bar")
        self.assertContains(response, "status-banner")

    def test_valid_upload_uses_kern_result_components(self):
        content = VALID_BESCHEID_FIXTURE.read_bytes()

        response = self.client.post(
            reverse("xgewerbesteuer_upload"),
            data={"bescheide": uploaded_xml(VALID_BESCHEID_FIXTURE.name, content)},
            follow=True,
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "card")
        self.assertContains(response, "download-bar")
        self.assertContains(response, "btn btn--secondary")
        self.assertContains(response, "status-banner--deadline")

    def test_result_template_displays_none_values_as_not_found(self):
        rendered = render_to_string(
            "xgewerbesteuer/results.html",
            {
                "uploaded_file_name": "fiktiver-bescheid.xml",
                "uploaded_file_size": 123,
                "summary_items": [
                    {"label": "Gemeinde / Kommune", "value": None},
                    {"label": "Zahlbetrag", "value": ""},
                ],
                "change_comparison_items": [
                    {
                        "label": "Zahlbetrag",
                        "previous_value": None,
                        "current_value": "512.50",
                        "difference": "Nicht vergleichbar",
                        "percentage": "Nicht vergleichbar",
                        "change_type": "Nicht vergleichbar",
                    }
                ],
            },
        )

        self.assertIn("Nicht gefunden", rendered)
        self.assertNotIn(">None<", rendered)

    def test_download_area_is_marked_as_no_print_after_valid_upload(self):
        content = VALID_BESCHEID_FIXTURE.read_bytes()

        response = self.client.post(
            reverse("xgewerbesteuer_upload"),
            data={"bescheide": uploaded_xml(VALID_BESCHEID_FIXTURE.name, content)},
            follow=True,
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "download-bar")
        self.assertContains(response, "no-print")

    def test_result_sections_remain_marked_for_print_after_valid_upload(self):
        content = VALID_BESCHEID_FIXTURE.read_bytes()

        response = self.client.post(
            reverse("xgewerbesteuer_upload"),
            data={"bescheide": uploaded_xml(VALID_BESCHEID_FIXTURE.name, content)},
            follow=True,
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "card")
        self.assertContains(response, "Zusammenfassung")
        self.assertContains(response, "Plausibilitätsprüfung")
        self.assertContains(response, "Fälligkeiten")
        self.assertContains(response, "Hinweise")

    def test_valid_upload_displays_due_date_calendar(self):
        content = VALID_BESCHEID_FIXTURE.read_bytes()

        response = self.client.post(
            reverse("xgewerbesteuer_upload"),
            data={"bescheide": uploaded_xml(VALID_BESCHEID_FIXTURE.name, content)},
            follow=True,
        )

        self.assertEqual(response.status_code, 200)
        self.assertIn("due_date_calendar", response.context)
        self.assertContains(response, "Fälligkeiten")
        self.assertContains(
            response,
            "Für diesen Bescheid wurden keine verwertbaren Fälligkeitstermine gefunden.",
        )

    def test_due_date_calendar_keeps_existing_table_view_visible(self):
        content = VALID_BESCHEID_FIXTURE.read_bytes()

        response = self.client.post(
            reverse("xgewerbesteuer_upload"),
            data={"bescheide": uploaded_xml(VALID_BESCHEID_FIXTURE.name, content)},
            follow=True,
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "table-wrapper")
        self.assertContains(response, "Fälligkeiten")

    def test_due_date_calendar_mentions_no_external_calendar_services(self):
        content = VALID_BESCHEID_FIXTURE.read_bytes()

        response = self.client.post(
            reverse("xgewerbesteuer_upload"),
            data={"bescheide": uploaded_xml(VALID_BESCHEID_FIXTURE.name, content)},
            follow=True,
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "keine steuerliche Beratung")

    def test_due_date_calendar_template_renders_visible_entries(self):
        due_date_calendar = build_due_date_calendar(
            {
                "amount_due": "630.00",
                "due_dates": "2025-02-15",
                "payment_classification": {"type": "Nachzahlung"},
                "advance_payments": [],
            }
        )

        rendered = render_to_string(
            "xgewerbesteuer/results.html",
            {
                "summary_items": [
                    {"label": "Fälligkeiten", "value": "2025-02-15"},
                ],
                "due_date_calendar": due_date_calendar,
            },
        )

        self.assertIn("Februar 2025", rendered)
        self.assertIn("15.02.2025", rendered)
        self.assertIn("630,00 EUR", rendered)
        self.assertIn("Nachzahlung am 15.02.2025", rendered)
        self.assertIn("calendar-entry", rendered)

    def test_advance_payment_upload_displays_due_date_calendar_empty_state(self):
        content = ADVANCE_PAYMENT_FIXTURE.read_bytes()

        response = self.client.post(
            reverse("xgewerbesteuer_upload"),
            data={"bescheide": uploaded_xml(ADVANCE_PAYMENT_FIXTURE.name, content)},
            follow=True,
        )

        self.assertEqual(response.status_code, 200)
        self.assertIn("due_date_calendar", response.context)
        self.assertContains(response, "Fälligkeiten")
        self.assertContains(
            response,
            "Für diesen Bescheid wurden keine verwertbaren Fälligkeitstermine gefunden.",
        )

    def test_valid_upload_displays_liquidity_impact(self):
        content = VALID_BESCHEID_FIXTURE.read_bytes()

        response = self.client.post(
            reverse("xgewerbesteuer_upload"),
            data={"bescheide": uploaded_xml(VALID_BESCHEID_FIXTURE.name, content)},
            follow=True,
        )

        self.assertEqual(response.status_code, 200)
        self.assertIn("liquidity_impact", response.context)
        self.assertContains(response, "Liquiditätsauswirkung")
        self.assertContains(response, "Sofort/fällig")
        self.assertContains(response, "keine Finanz- oder Steuerberatung")

    def test_advance_payment_upload_displays_liquidity_impact(self):
        content = ADVANCE_PAYMENT_FIXTURE.read_bytes()

        response = self.client.post(
            reverse("xgewerbesteuer_upload"),
            data={"bescheide": uploaded_xml(ADVANCE_PAYMENT_FIXTURE.name, content)},
            follow=True,
        )

        self.assertEqual(response.status_code, 200)
        self.assertIn("liquidity_impact", response.context)
        self.assertContains(response, "Liquiditätsauswirkung")
        self.assertContains(response, "Vorauszahlung")

    def test_invalid_upload_uses_kern_error_component(self):
        response = self.client.post(reverse("xgewerbesteuer_upload"), data={})

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'role="alert"')
        self.assertContains(response, "alert--error")

    def test_post_valid_current_without_previous_hides_change_comparison(self):
        content = VALID_BESCHEID_FIXTURE.read_bytes()

        response = self.client.post(
            reverse("xgewerbesteuer_upload"),
            data={"bescheide": uploaded_xml(VALID_BESCHEID_FIXTURE.name, content)},
            follow=True,
        )

        self.assertEqual(response.status_code, 200)
        self.assertNotIn("change_comparison_items", response.context)
        self.assertNotContains(response, "Änderungsvergleich")

    def test_post_advance_payment_fixture_displays_advance_payments_section(self):
        content = ADVANCE_PAYMENT_FIXTURE.read_bytes()

        response = self.client.post(
            reverse("xgewerbesteuer_upload"),
            data={"bescheide": uploaded_xml(ADVANCE_PAYMENT_FIXTURE.name, content)},
            follow=True,
        )

        self.assertEqual(response.status_code, 200)
        self.assertIn("advance_payments", response.context)
        self.assertEqual(len(response.context["advance_payments"]), 1)
        self.assertEqual(response.context["advance_payments"][0]["amount"], "147.00")
        self.assertEqual(response.context["advance_payments"][0]["period"], "2023")
        self.assertEqual(response.context["payment_classification"]["type"], "Vorauszahlung")
        self.assertEqual(
            response.context["current_bescheid"]["message_type_label"],
            "Vorauszahlungsbescheid",
        )
        self.assertContains(response, "Vorauszahlungen")
        self.assertContains(response, "147.00")
        self.assertContains(response, "Vorauszahlung")
        self.assertContains(response, "Einordnung der Zahlung")

    def test_post_valid_current_and_previous_fixture_displays_previous_year_comparison(self):
        current_content = VALID_BESCHEID_FIXTURE.read_bytes()
        previous_content = PREVIOUS_BESCHEID_FIXTURE.read_bytes()

        response = self.client.post(
            reverse("xgewerbesteuer_upload"),
            data={
                "bescheide": [
                    uploaded_xml(VALID_BESCHEID_FIXTURE.name, current_content),
                    uploaded_xml(PREVIOUS_BESCHEID_FIXTURE.name, previous_content),
                ],
            },
            follow=True,
        )

        self.assertEqual(response.status_code, 200)
        self.assertIn("current_bescheid", response.context)
        self.assertIn("previous_bescheid", response.context)
        self.assertEqual(response.context["current_bescheid"]["tax_period"], "2023")
        self.assertEqual(response.context["previous_bescheid"]["tax_period"], "2022")
        self.assertContains(response, "Vergleich mit Vorbescheid")
        self.assertContains(response, "Aktueller Bescheid")
        self.assertContains(response, "Vorbescheid")
        self.assertContains(response, "Nachrichtentyp")
        self.assertContains(response, "Generische Gewerbesteuernachricht")
        self.assertContains(response, "2023")
        self.assertContains(response, "2022")
        self.assertIn("change_comparison_items", response.context)
        self.assertContains(response, "Änderungsvergleich")
        self.assertContains(response, "+117.50")
        self.assertContains(response, "+22.93 %")
        self.assertContains(response, "change-badge--up")
        self.assertContains(response, "Bewertung")
        self.assertContains(response, "Wichtige Änderung")
        self.assertContains(
            response,
            "Dieser Wert hat sich gegenüber dem Vorjahr erhöht.",
        )
        self.assertContains(response, "Keine wichtige Änderung")
        self.assertContains(response, "Wichtige Änderung zum Vorjahr")
        self.assertIn("status_indicator", response.context)
        self.assertEqual(response.context["status_indicator"]["status"], "warning")
        self.assertContains(response, "Warnung / Auffälligkeit")

    def test_post_valid_current_and_different_previous_type_shows_neutral_notice(self):
        current_content = VALID_BESCHEID_FIXTURE.read_bytes()
        previous_content = INTEREST_FIXTURE.read_bytes()

        response = self.client.post(
            reverse("xgewerbesteuer_upload"),
            data={
                "bescheide": [
                    uploaded_xml(VALID_BESCHEID_FIXTURE.name, current_content),
                    uploaded_xml(INTEREST_FIXTURE.name, previous_content),
                ],
            },
            follow=True,
        )

        self.assertEqual(response.status_code, 200)
        self.assertIn("previous_bescheid", response.context)
        self.assertNotIn("change_comparison_items", response.context)
        self.assertContains(response, "Zinsbescheid")
        self.assertContains(response, "unterschiedliche Nachrichtentypen")
        self.assertNotContains(response, "+117.50")

    def test_post_does_not_select_missing_tax_period_as_current_bescheid(self):
        known_period = processed_bescheid_with_due_date()
        known_period["bescheid"]["tax_period"] = "2023"
        known_period["bescheid"]["file_name"] = "known.xml"
        missing_period = processed_bescheid_with_due_date()
        missing_period["bescheid"]["tax_period"] = None
        missing_period["bescheid"]["file_name"] = "missing.xml"

        with patch(
            "xgewerbesteuer.views.process_uploaded_bescheid",
            side_effect=[known_period, missing_period],
        ):
            response = self.client.post(
                reverse("xgewerbesteuer_upload"),
                data={
                    "bescheide": [
                        uploaded_xml("known.xml", b"<nachricht/>"),
                        uploaded_xml("missing.xml", b"<nachricht/>"),
                    ],
                },
                follow=True,
            )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context["current_bescheid"]["file_name"], "known.xml")
        self.assertEqual(response.context["current_bescheid"]["tax_period"], "2023")

    def test_post_valid_current_with_invalid_previous_filename_keeps_current_summary(self):
        current_content = VALID_BESCHEID_FIXTURE.read_bytes()

        response = self.client.post(
            reverse("xgewerbesteuer_upload"),
            data={
                "bescheide": [
                    uploaded_xml(VALID_BESCHEID_FIXTURE.name, current_content),
                    uploaded_xml("vorjahr.txt", b"<nachricht/>"),
                ],
            },
            follow=True,
        )

        self.assertEqual(response.status_code, 200)
        self.assertIn("summary_items", response.context)
        self.assertNotIn("previous_bescheid", response.context)
        self.assertIn("multi_bescheid_upload_errors", response.context)
        self.assertEqual(len(response.context["multi_bescheid_upload_errors"]), 1)
        self.assertContains(response, "Zusammenfassung")

    def test_pdf_report_requires_successful_upload(self):
        response = self.client.get(reverse("xgewerbesteuer_pdf_report"))

        self.assertEqual(response.status_code, 404)
        self.assertEqual(response["Content-Type"], "text/plain; charset=utf-8")
        self.assertIn(
            "Bitte laden Sie zuerst einen gültigen Bescheid hoch.",
            response.content.decode("utf-8"),
        )

    def test_pdf_report_download_after_valid_upload(self):
        content = VALID_BESCHEID_FIXTURE.read_bytes()

        upload_response = self.client.post(
            reverse("xgewerbesteuer_upload"),
            data={"bescheide": uploaded_xml(VALID_BESCHEID_FIXTURE.name, content)},
            follow=True,
        )

        self.assertEqual(upload_response.status_code, 200)
        self.assertIn(PDF_REPORT_SESSION_KEY, self.client.session)
        pdf_report_data = self.client.session[PDF_REPORT_SESSION_KEY]
        pdf_summary_items = {
            item["label"]: item["value"] for item in pdf_report_data["summary_items"]
        }
        self.assertEqual(
            pdf_summary_items["Nachrichtentyp"],
            "Generische Gewerbesteuernachricht",
        )

        pdf_response = self.client.get(reverse("xgewerbesteuer_pdf_report"))

        self.assertEqual(pdf_response.status_code, 200)
        self.assertEqual(pdf_response["Content-Type"], "application/pdf")
        self.assertIn(
            'attachment; filename="gewerbesteuerbescheid-bericht.pdf"',
            pdf_response["Content-Disposition"],
        )
        self.assertTrue(pdf_response.content.startswith(b"%PDF"))
        self.assertGreater(len(pdf_response.content), 500)

    def test_invalid_upload_does_not_create_pdf_report(self):
        response = self.client.post(
            reverse("xgewerbesteuer_upload"),
            data={"bescheide": uploaded_xml("bescheid.xml", b"<nachricht/>")},
        )

        self.assertEqual(response.status_code, 200)
        self.assertNotIn(PDF_REPORT_SESSION_KEY, self.client.session)

        pdf_response = self.client.get(reverse("xgewerbesteuer_pdf_report"))

        self.assertEqual(pdf_response.status_code, 404)

    def test_csv_export_requires_successful_upload(self):
        response = self.client.get(reverse("xgewerbesteuer_csv_export"))

        self.assertEqual(response.status_code, 404)
        self.assertEqual(response["Content-Type"], "text/plain; charset=utf-8")
        self.assertIn(
            "Bitte laden Sie zuerst einen gültigen Bescheid hoch.",
            response.content.decode("utf-8"),
        )

    def test_csv_export_download_after_valid_upload(self):
        content = VALID_BESCHEID_FIXTURE.read_bytes()

        upload_response = self.client.post(
            reverse("xgewerbesteuer_upload"),
            data={"bescheide": uploaded_xml(VALID_BESCHEID_FIXTURE.name, content)},
            follow=True,
        )

        self.assertEqual(upload_response.status_code, 200)
        self.assertIn(CSV_EXPORT_SESSION_KEY, self.client.session)

        csv_response = self.client.get(reverse("xgewerbesteuer_csv_export"))

        self.assertEqual(csv_response.status_code, 200)
        self.assertEqual(csv_response["Content-Type"], "text/csv; charset=utf-8")
        self.assertIn(
            'attachment; filename="gewerbesteuerbescheid-export.csv"',
            csv_response["Content-Disposition"],
        )

        csv_content = csv_response.content.decode("utf-8")

        self.assertIn("Datensatztyp", csv_content)
        self.assertIn("Nachrichtentyp", csv_content)
        self.assertIn("Generische Gewerbesteuernachricht", csv_content)
        self.assertIn("Stadt Musterhausen", csv_content)
        self.assertIn("Nachzahlung", csv_content)
        self.assertNotIn("<nachricht", csv_content)
        self.assertNotIn("Traceback", csv_content)
        self.assertNotIn("DEBUG", csv_content)

    def test_invalid_upload_does_not_create_csv_export(self):
        response = self.client.post(
            reverse("xgewerbesteuer_upload"),
            data={"bescheide": uploaded_xml("bescheid.xml", b"<nachricht/>")},
        )

        self.assertEqual(response.status_code, 200)
        self.assertNotIn(CSV_EXPORT_SESSION_KEY, self.client.session)

        csv_response = self.client.get(reverse("xgewerbesteuer_csv_export"))

        self.assertEqual(csv_response.status_code, 404)

    def test_csv_export_after_advance_payment_upload_contains_advance_payment_row(self):
        content = ADVANCE_PAYMENT_FIXTURE.read_bytes()

        upload_response = self.client.post(
            reverse("xgewerbesteuer_upload"),
            data={"bescheide": uploaded_xml(ADVANCE_PAYMENT_FIXTURE.name, content)},
            follow=True,
        )

        self.assertEqual(upload_response.status_code, 200)

        csv_response = self.client.get(reverse("xgewerbesteuer_csv_export"))
        csv_content = csv_response.content.decode("utf-8")

        self.assertEqual(csv_response.status_code, 200)
        self.assertIn("Vorauszahlung", csv_content)
        self.assertIn("147.00", csv_content)

    def test_valid_upload_displays_plausibility_check(self):
        response = self.client.post(
            reverse("xgewerbesteuer_upload"),
            data={
                "bescheide": uploaded_xml(
                    VALID_BESCHEID_FIXTURE.name,
                    VALID_BESCHEID_FIXTURE.read_bytes(),
                )
            },
            follow=True,
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context["plausibility_check"]["status"], "plausible")
        self.assertContains(response, "Plausibilitätsprüfung")
        self.assertContains(response, "Status: Plausibel")
        self.assertContains(response, "Gewerbesteuer = Gewerbesteuermessbetrag")
        self.assertContains(response, "ersetzt keine steuerliche Beratung")
        self.assertNotContains(response, "Warnung / Abweichung")

    def test_unplausible_upload_displays_plausibility_warning(self):
        with patch(
            "xgewerbesteuer.views.process_uploaded_bescheid",
            return_value=processed_bescheid_with_plausibility_values(
                amount_due="120.00",
                trade_tax_assessment_amount="25.00",
                assessment_rate="420",
            ),
        ):
            response = self.client.post(
                reverse("xgewerbesteuer_upload"),
                data={"bescheide": uploaded_xml("bescheid.xml", b"<nachricht/>")},
                follow=True,
            )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context["plausibility_check"]["status"], "warning")
        self.assertContains(response, "Warnung / Abweichung")
        self.assertContains(response, "weicht von der rechnerischen Grundformel ab")

    def test_upload_with_missing_values_displays_not_checkable_plausibility(self):
        with patch(
            "xgewerbesteuer.views.process_uploaded_bescheid",
            return_value=processed_bescheid_with_plausibility_values(
                amount_due=None,
                trade_tax_assessment_amount="25.00",
                assessment_rate="420",
            ),
        ):
            response = self.client.post(
                reverse("xgewerbesteuer_upload"),
                data={"bescheide": uploaded_xml("bescheid.xml", b"<nachricht/>")},
                follow=True,
            )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            response.context["plausibility_check"]["status"],
            "not_checkable",
        )
        self.assertContains(response, "Nicht prüfbar")
        self.assertContains(response, "Nicht berechenbar")

    def test_plausibility_keeps_comparisons_history_and_downloads_working(self):
        with patch(
            "xgewerbesteuer.views.process_uploaded_bescheid",
            side_effect=[
                processed_bescheid_with_due_date(),
                {"is_valid": True, "bescheid": comparison_bescheid("2021")},
                {"is_valid": True, "bescheid": comparison_bescheid("2022")},
            ],
        ):
            upload_response = self.client.post(
                reverse("xgewerbesteuer_upload"),
                data={
                    "bescheide": [
                        uploaded_xml("bescheid.xml", b"<nachricht/>"),
                        uploaded_xml("vergleich-2021.xml", b"<nachricht/>"),
                        uploaded_xml("vergleich-2022.xml", b"<nachricht/>"),
                    ],
                },
                follow=True,
            )

        self.assertEqual(upload_response.status_code, 200)
        self.assertIn("plausibility_check", upload_response.context)
        self.assertIn("multi_bescheid_comparison", upload_response.context)
        self.assertIn("historical_development", upload_response.context)
        self.assertContains(upload_response, "Zusammenfassung")

        self.assertEqual(self.client.get(reverse("xgewerbesteuer_pdf_report")).status_code, 200)
        self.assertEqual(self.client.get(reverse("xgewerbesteuer_csv_export")).status_code, 200)
        self.assertEqual(self.client.get(reverse("xgewerbesteuer_ics_export")).status_code, 200)

    def test_multi_bescheid_upload_displays_multi_year_comparison(self):
        response = self.client.post(
            reverse("xgewerbesteuer_upload"),
            data={
                "bescheide": [
                    uploaded_xml(fixture.name, fixture.read_bytes())
                    for fixture in MULTI_YEAR_FIXTURES
                ],
            },
            follow=True,
        )

        comparison = response.context["multi_bescheid_comparison"]

        self.assertEqual(response.status_code, 200)
        self.assertEqual(comparison["valid_count"], 3)
        self.assertEqual(
            [record["tax_period"] for record in comparison["records"]],
            ["2021", "2022", "2023"],
        )
        self.assertTrue(
            all(
                record["message_type_label"] == "Generische Gewerbesteuernachricht"
                for record in comparison["records"]
            )
        )
        self.assertContains(response, "Mehrjahresvergleich")
        self.assertContains(response, "Nachrichtentyp")
        self.assertContains(response, "Generische Gewerbesteuernachricht")
        self.assertContains(response, "Gültige Bescheide")
        self.assertContains(response, "400.00")
        self.assertContains(response, "512.50")
        self.assertContains(response, "630.00")
        self.assertContains(response, "Gewerbesteuermessbetrag")
        self.assertContains(response, "Hebesatz")
        self.assertContains(response, "Fälligkeiten")
        self.assertContains(response, "Vorauszahlungen")
        self.assertContains(response, "table-wrapper")
        self.assertContains(response, "table")

    def test_multi_bescheid_upload_displays_historical_development(self):
        response = self.client.post(
            reverse("xgewerbesteuer_upload"),
            data={
                "bescheide": [
                    uploaded_xml(fixture.name, fixture.read_bytes())
                    for fixture in MULTI_YEAR_FIXTURES
                ],
            },
            follow=True,
        )

        history = response.context["historical_development"]

        self.assertEqual(response.status_code, 200)
        self.assertEqual(history["year_count"], 3)
        self.assertEqual(
            [row["tax_period"] for row in history["rows"]],
            ["2021", "2022", "2023"],
        )
        self.assertContains(response, "Historische Entwicklung")
        self.assertContains(response, "Mehrjahresvergleich")

    def test_multi_year_sections_remain_visible_for_print(self):
        response = self.client.post(
            reverse("xgewerbesteuer_upload"),
            data={
                "bescheide": [
                    uploaded_xml(fixture.name, fixture.read_bytes())
                    for fixture in MULTI_YEAR_FIXTURES
                ],
            },
            follow=True,
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "card")
        self.assertContains(response, "Mehrjahresvergleich")
        self.assertContains(response, "Historische Entwicklung")
        self.assertContains(response, "table-wrapper")
        self.assertContains(response, "table")

    def test_historical_development_table_contains_values_and_changes(self):
        response = self.client.post(
            reverse("xgewerbesteuer_upload"),
            data={
                "bescheide": [
                    uploaded_xml(fixture.name, fixture.read_bytes())
                    for fixture in MULTI_YEAR_FIXTURES
                ],
            },
            follow=True,
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Zahlbetrag")
        self.assertContains(response, "Gewerbesteuermessbetrag")
        self.assertContains(response, "Hebesatz")
        self.assertContains(response, "Wichtigste Fälligkeit")
        self.assertContains(response, "+112.50")
        self.assertContains(response, "+117.50")
        self.assertContains(response, "+25.00")
        self.assertContains(response, "+10.00")
        self.assertContains(response, "Nicht gefunden")

    def test_historical_development_uses_responsive_table_and_keeps_chart_additional(self):
        response = self.client.post(
            reverse("xgewerbesteuer_upload"),
            data={
                "bescheide": [
                    uploaded_xml(fixture.name, fixture.read_bytes())
                    for fixture in MULTI_YEAR_FIXTURES
                ],
            },
            follow=True,
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "table-wrapper")
        self.assertContains(response, "table")
        self.assertContains(response, "multi-metric-chart")
        self.assertContains(response, "<table", html=False)
        self.assertContains(response, "Entwicklung der ausgelesenen Werte")

    def test_historical_development_template_marks_missing_values_neutrally(self):
        historical_development = build_historical_development(
            [
                build_multi_bescheid_record(
                    comparison_bescheid("2021", amount_due=None)
                ),
                build_multi_bescheid_record(comparison_bescheid("2022", "512.50")),
            ]
        )

        rendered = render_to_string(
            "xgewerbesteuer/results.html",
            {
                "summary_items": [{"label": "Zahlbetrag", "value": "512.50"}],
                "historical_development": historical_development,
            },
        )

        self.assertIn("Historische Entwicklung", rendered)
        self.assertIn("Nicht gefunden", rendered)
        self.assertIn("Nicht berechenbar", rendered)

    def test_multi_bescheid_upload_keeps_valid_files_when_one_file_is_invalid(self):
        response = self.client.post(
            reverse("xgewerbesteuer_upload"),
            data={
                "bescheide": [
                    uploaded_xml(
                        VALID_BESCHEID_FIXTURE.name,
                        VALID_BESCHEID_FIXTURE.read_bytes(),
                    ),
                    uploaded_xml(
                        MULTI_YEAR_FIXTURES[1].name,
                        MULTI_YEAR_FIXTURES[1].read_bytes(),
                    ),
                    uploaded_xml(
                        MULTI_YEAR_FIXTURES[2].name,
                        MULTI_YEAR_FIXTURES[2].read_bytes(),
                    ),
                    uploaded_xml("ungueltig.txt", b"<nachricht/>"),
                ],
            },
            follow=True,
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            response.context["multi_bescheid_comparison"]["valid_count"],
            3,
        )
        self.assertEqual(len(response.context["multi_bescheid_upload_errors"]), 1)
        self.assertContains(response, "ungueltig.txt")
        self.assertContains(response, "Die hochgeladene Datei muss eine XML-Datei sein.")
        self.assertContains(response, "Mehrjahresvergleich")

    def test_multi_bescheid_upload_marks_duplicate_tax_periods(self):
        content = VALID_BESCHEID_FIXTURE.read_bytes()

        response = self.client.post(
            reverse("xgewerbesteuer_upload"),
            data={
                "bescheide": [
                    uploaded_xml(
                        VALID_BESCHEID_FIXTURE.name,
                        VALID_BESCHEID_FIXTURE.read_bytes(),
                    ),
                    uploaded_xml("erstbescheid-2023.xml", content),
                    uploaded_xml("aenderungsbescheid-2023.xml", content),
                ],
            },
            follow=True,
        )

        comparison = response.context["multi_bescheid_comparison"]

        self.assertEqual(response.status_code, 200)
        self.assertEqual(comparison["duplicate_tax_periods"], ["2023"])
        self.assertContains(response, "Mehrere Bescheide enthalten denselben Steuerzeitraum")
        self.assertContains(response, "multi-comparison-duplicate")

    def test_single_file_upload_does_not_show_multi_year_comparison(self):
        response = self.client.post(
            reverse("xgewerbesteuer_upload"),
            data={
                "bescheide": uploaded_xml(
                    VALID_BESCHEID_FIXTURE.name,
                    VALID_BESCHEID_FIXTURE.read_bytes(),
                ),
            },
            follow=True,
        )

        self.assertEqual(response.status_code, 200)
        self.assertNotIn("multi_bescheid_comparison", response.context)
        self.assertNotContains(response, "Mehrjahresvergleich")

    def test_downloads_still_work_after_multi_bescheid_upload(self):
        with patch(
            "xgewerbesteuer.views.process_uploaded_bescheid",
            side_effect=[
                processed_bescheid_with_due_date(),
                {"is_valid": True, "bescheid": comparison_bescheid("2021")},
                {"is_valid": True, "bescheid": comparison_bescheid("2022")},
            ],
        ):
            upload_response = self.client.post(
                reverse("xgewerbesteuer_upload"),
                data={
                    "bescheide": [
                        uploaded_xml("bescheid.xml", b"<nachricht/>"),
                        uploaded_xml("vergleich-2021.xml", b"<nachricht/>"),
                        uploaded_xml("vergleich-2022.xml", b"<nachricht/>"),
                    ],
                },
                follow=True,
            )

        self.assertEqual(upload_response.status_code, 200)
        self.assertIn("multi_bescheid_comparison", upload_response.context)

        pdf_response = self.client.get(reverse("xgewerbesteuer_pdf_report"))
        csv_response = self.client.get(reverse("xgewerbesteuer_csv_export"))
        ics_response = self.client.get(reverse("xgewerbesteuer_ics_export"))

        self.assertEqual(pdf_response.status_code, 200)
        self.assertEqual(csv_response.status_code, 200)
        self.assertEqual(ics_response.status_code, 200)
        self.assertTrue(pdf_response.content.startswith(b"%PDF"))
        self.assertIn("Datensatztyp", csv_response.content.decode("utf-8"))
        self.assertIn("BEGIN:VCALENDAR", ics_response.content.decode("utf-8"))

    def test_valid_upload_with_due_date_displays_ics_download_link(self):
        with patch(
            "xgewerbesteuer.views.process_uploaded_bescheid",
            return_value=processed_bescheid_with_due_date(),
        ):
            response = self.client.post(
                reverse("xgewerbesteuer_upload"),
                data={"bescheide": uploaded_xml("bescheid.xml", b"<nachricht/>")},
                follow=True,
            )

        self.assertEqual(response.status_code, 200)
        self.assertIn(ICS_EXPORT_SESSION_KEY, self.client.session)
        self.assertIn(PDF_REPORT_SESSION_KEY, self.client.session)
        self.assertIn(CSV_EXPORT_SESSION_KEY, self.client.session)
        self.assertContains(response, "Fristdatei (.ics)")
        self.assertContains(response, reverse("xgewerbesteuer_ics_export"))

    def test_ics_export_download_after_valid_upload(self):
        with patch(
            "xgewerbesteuer.views.process_uploaded_bescheid",
            return_value=processed_bescheid_with_due_date(),
        ):
            upload_response = self.client.post(
                reverse("xgewerbesteuer_upload"),
                data={"bescheide": uploaded_xml("bescheid.xml", b"<nachricht/>")},
                follow=True,
            )

        self.assertEqual(upload_response.status_code, 200)

        ics_response = self.client.get(reverse("xgewerbesteuer_ics_export"))

        self.assertEqual(ics_response.status_code, 200)
        self.assertEqual(ics_response["Content-Type"], "text/calendar; charset=utf-8")
        self.assertIn(
            'attachment; filename="fristtermine.ics"',
            ics_response["Content-Disposition"],
        )
        self.assertIn("BEGIN:VCALENDAR", ics_response.content.decode("utf-8"))
        self.assertIn("DTSTART;VALUE=DATE:20250215", ics_response.content.decode("utf-8"))

    def test_ics_export_requires_successful_upload_with_due_date(self):
        response = self.client.get(reverse("xgewerbesteuer_ics_export"))

        self.assertEqual(response.status_code, 404)
        self.assertEqual(response["Content-Type"], "text/plain; charset=utf-8")
        self.assertIn(
            "keine verwertbaren Fälligkeitstermine",
            response.content.decode("utf-8"),
        )

    def test_valid_upload_without_usable_due_date_does_not_offer_ics_download(self):
        content = VALID_BESCHEID_FIXTURE.read_bytes()

        response = self.client.post(
            reverse("xgewerbesteuer_upload"),
            data={"bescheide": uploaded_xml(VALID_BESCHEID_FIXTURE.name, content)},
            follow=True,
        )

        self.assertEqual(response.status_code, 200)
        self.assertNotIn(ICS_EXPORT_SESSION_KEY, self.client.session)
        self.assertNotContains(response, "Fristdatei (.ics)")

        ics_response = self.client.get(reverse("xgewerbesteuer_ics_export"))

        self.assertEqual(ics_response.status_code, 404)

    def test_post_valid_current_with_schema_invalid_previous_keeps_current_summary(self):
        current_content = VALID_BESCHEID_FIXTURE.read_bytes()

        response = self.client.post(
            reverse("xgewerbesteuer_upload"),
            data={
                "bescheide": [
                    uploaded_xml(VALID_BESCHEID_FIXTURE.name, current_content),
                    uploaded_xml("vorjahr.xml", b"<nachricht/>"),
                ],
            },
            follow=True,
        )

        self.assertEqual(response.status_code, 200)
        self.assertIn("summary_items", response.context)
        self.assertNotIn("previous_bescheid", response.context)
        self.assertIn("multi_bescheid_upload_errors", response.context)
        self.assertContains(response, "Zusammenfassung")

    def test_post_valid_current_with_oversized_previous_file_keeps_current_summary(self):
        current_content = VALID_BESCHEID_FIXTURE.read_bytes()

        response = self.client.post(
            reverse("xgewerbesteuer_upload"),
            data={
                "bescheide": [
                    uploaded_xml(VALID_BESCHEID_FIXTURE.name, current_content),
                    uploaded_xml(
                        "vorjahr.xml",
                        b"x" * (MAX_UPLOAD_SIZE_BYTES + 1),
                    ),
                ],
            },
            follow=True,
        )

        self.assertEqual(response.status_code, 200)
        self.assertIn("summary_items", response.context)
        self.assertNotIn("previous_bescheid", response.context)
        self.assertIn("multi_bescheid_upload_errors", response.context)
        self.assertEqual(len(response.context["multi_bescheid_upload_errors"]), 1)
        self.assertContains(response, "Zusammenfassung")
