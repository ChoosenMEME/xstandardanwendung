"""Regressionstests fuer XML-Upload, Extraktion und Validierung."""

import csv
from io import StringIO
from pathlib import Path
from unittest.mock import patch

from defusedxml import ElementTree
from django.core.files.uploadedfile import SimpleUploadedFile
from django.template.loader import render_to_string
from django.test import SimpleTestCase
from django.urls import reverse

from xgewerbesteuer.views import (
    CSV_EXPORT_COLUMNS,
    CSV_EXPORT_SESSION_KEY,
    ICS_EXPORT_SESSION_KEY,
    MAX_UPLOAD_SIZE_BYTES,
    PDF_REPORT_SESSION_KEY,
    build_due_date_calendar,
    build_due_date_calendar_entries,
    build_ics_event,
    build_change_comparison,
    build_historical_chart_data,
    build_historical_development,
    build_historical_development_row,
    build_multi_bescheid_comparison,
    build_multi_bescheid_record,
    build_multi_bescheid_upload_errors,
    calculate_historical_change,
    create_ics_export,
    escape_ics_text,
    format_ics_date,
    group_bescheide_by_tax_period,
    group_calendar_entries_by_month,
    build_notice_area,
    build_period_comparison_notice,
    build_status_indicator,
    clean_text,
    classify_change_importance,
    classify_payment_type,
    create_csv_export,
    extract_amount_due,
    extract_assessment_rate,
    extract_advance_payments,
    extract_due_dates,
    extract_municipality,
    extract_tax_period,
    extract_trade_tax_assessment_amount,
    split_due_date_values,
    get_local_name,
    sort_bescheid_records_chronologically,
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
RESPONSIVE_CSS_FILE = (
    Path(__file__).resolve().parents[1]
    / "static"
    / "xgewerbesteuer"
    / "responsive.css"
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
        css_content = RESPONSIVE_CSS_FILE.read_text(encoding="utf-8")

        self.assertIn("@media (max-width: 640px)", css_content)
        self.assertIn(".responsive-table-wrapper", css_content)
        self.assertIn(".download-actions", css_content)
        self.assertIn(".app-shell", css_content)

    def test_responsive_css_contains_kern_layout_rules(self):
        css_content = RESPONSIVE_CSS_FILE.read_text(encoding="utf-8")

        self.assertIn(".content-section", css_content)
        self.assertIn(".result-section", css_content)
        self.assertIn(".message-card--error", css_content)
        self.assertIn(".message-card--success", css_content)
        self.assertIn(".status-card--deadline", css_content)
        self.assertIn(".download-panel", css_content)
        self.assertIn(".comparison-row--important", css_content)
        self.assertIn(".due-date-calendar", css_content)
        self.assertIn(".due-date-calendar-month", css_content)
        self.assertIn(".due-date-calendar-entry", css_content)
        self.assertIn(".multi-comparison-summary", css_content)
        self.assertIn(".multi-comparison-duplicate", css_content)
        self.assertIn(".historical-development-summary", css_content)
        self.assertIn(".historical-development-notice", css_content)
        self.assertIn(".historical-chart", css_content)
        self.assertIn(".historical-chart-bar", css_content)

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

        self.assertEqual(extract_amount_due(root), "Nicht gefunden")
        self.assertEqual(extract_assessment_rate(root), "Nicht gefunden")
        self.assertEqual(extract_due_dates(root), "Nicht gefunden")

    def test_extract_advance_payments_from_fixture(self):
        root = ElementTree.parse(ADVANCE_PAYMENT_FIXTURE).getroot()

        advance_payments = extract_advance_payments(root)

        self.assertEqual(len(advance_payments), 1)
        self.assertEqual(advance_payments[0]["amount"], "147.00")
        self.assertEqual(advance_payments[0]["due_date"], "Nicht gefunden")
        self.assertEqual(advance_payments[0]["period"], "2023")
        self.assertEqual(advance_payments[0]["type"], "Vorauszahlung")

    def test_extract_advance_payments_returns_empty_list_when_missing(self):
        root = self.parse("<nachricht />")

        self.assertEqual(extract_advance_payments(root), [])

    def test_classifies_advance_payment_when_advance_payments_exist(self):
        classification = classify_payment_type(
            "147.00",
            [
                {
                    "amount": "147.00",
                    "due_date": "Nicht gefunden",
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
        classification = classify_payment_type("Nicht gefunden", [])

        self.assertEqual(classification["type"], "Nicht eindeutig bestimmbar")

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
            build_period_comparison_notice("Nicht gefunden", "2022"),
        )

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
            "tax_period": "Nicht gefunden",
            "amount_due": "Nicht gefunden",
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
            "due_dates": "Nicht gefunden",
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
            "due_dates": "Nicht gefunden",
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
            "municipality": "Nicht gefunden",
            "tax_period": "Nicht gefunden",
            "amount_due": "Nicht gefunden",
            "due_dates": "Nicht gefunden",
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
            "due_dates": "Nicht gefunden",
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
            "due_dates": "Nicht gefunden",
            "tax_period": "2023",
        }
        previous_bescheid = {
            "amount_due": "512.50",
            "trade_tax_assessment_amount": "125.00",
            "assessment_rate": "420",
            "due_dates": "Nicht gefunden",
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
                comparison_bescheid("Nicht gefunden", amount_due="Nicht gefunden"),
                comparison_bescheid("2023"),
            ]
        )

        missing_record = comparison["records"][1]

        self.assertEqual(missing_record["tax_period"], "Nicht gefunden")
        self.assertEqual(missing_record["amount_due"], "Nicht gefunden")
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
            comparison_bescheid("2023", municipality="Nicht gefunden")
        )

        self.assertEqual(record["municipality"], "Nicht gefunden")
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
                comparison_bescheid("2022", amount_due="Nicht gefunden")
            ),
            build_multi_bescheid_record(comparison_bescheid("2021")),
        )

        self.assertEqual(row["amount_due"], "Nicht gefunden")
        self.assertEqual(row["amount_due_change"], "Nicht berechenbar")

    def test_missing_historical_value_does_not_affect_other_years(self):
        history = build_historical_development(
            [
                build_multi_bescheid_record(
                    comparison_bescheid("2021", amount_due="Nicht gefunden")
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
            "amount_due": "Nicht gefunden",
            "due_dates": "Nicht gefunden",
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
            "amount_due": "Nicht gefunden",
            "due_dates": "Nicht gefunden",
            "payment_classification": {"type": "Vorauszahlung"},
            "advance_payments": [
                {
                    "amount": "147.00",
                    "due_date": "Nicht gefunden",
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
            "amount_due": "Nicht gefunden",
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
            "due_dates": "Nicht gefunden",
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
                "due_dates": "Nicht gefunden",
                "payment_classification": {"type": "Nachzahlung"},
                "advance_payments": [],
            }
        )

        self.assertIsNone(create_ics_export(calendar))

    def test_create_csv_export_contains_stable_columns_and_summary_values(self):
        report_data = {
            "summary_items": [
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


class XGewerbesteuerXsdValidationTests(SimpleTestCase):
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


class XGewerbesteuerUploadViewTests(SimpleTestCase):
    databases = {"default"}

    def test_start_page_renders_upload_form_and_expected_summary_scope(self):
        response = self.client.get(reverse("xgewerbesteuer_default"))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Gewerbesteuerbescheid-Assistent")
        self.assertContains(response, 'name="bescheid"')
        self.assertContains(response, 'name="vorjahresbescheid"')
        self.assertContains(response, 'name="vergleichsbescheide"')
        self.assertContains(response, 'multiple')
        self.assertContains(response, 'accept=".xml"')
        self.assertContains(response, "Anzeige des fälligen Zahlbetrags")
        self.assertContains(response, 'name="viewport"')
        self.assertContains(response, "responsive.css")
        self.assertContains(response, 'class="app-shell"')
        self.assertContains(response, 'class="xgewerbesteuer-page"')
        self.assertContains(response, 'class="upload-form"')
        self.assertContains(response, "@kern-ux/native")
        self.assertContains(response, 'data-kern-theme="light"')
        self.assertContains(response, "page-header")
        self.assertContains(response, "content-section")
        self.assertContains(response, "form-card")
        self.assertContains(response, "form-field")
        self.assertContains(response, "primary-action")

    def test_post_without_file_shows_missing_file_error(self):
        response = self.client.post(reverse("xgewerbesteuer_default"), data={})

        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            response.context["upload_error"],
            "Bitte wählen Sie eine XML-Datei aus.",
        )
        self.assertNotIn("uploaded_file_name", response.context)
        self.assertNotIn("status_indicator", response.context)

    def test_post_rejects_non_xml_filename_before_parsing(self):
        response = self.client.post(
            reverse("xgewerbesteuer_default"),
            data={"bescheid": uploaded_xml("bescheid.txt", b"<nachricht/>")},
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            response.context["upload_error"],
            "Die hochgeladene Datei muss eine XML-Datei sein.",
        )
        self.assertNotIn("uploaded_file_name", response.context)

    def test_post_rejects_oversized_xml_before_parsing(self):
        response = self.client.post(
            reverse("xgewerbesteuer_default"),
            data={
                "bescheid": uploaded_xml(
                    "bescheid.xml",
                    b"x" * (MAX_UPLOAD_SIZE_BYTES + 1),
                )
            },
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            response.context["upload_error"],
            "Die hochgeladene Datei ist zu groß.",
        )
        self.assertNotIn("uploaded_file_name", response.context)

    def test_post_rejects_malformed_xml_with_user_safe_message(self):
        response = self.client.post(
            reverse("xgewerbesteuer_default"),
            data={"bescheid": uploaded_xml("bescheid.xml", b"<nachricht>")},
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            response.context["upload_error"],
            "Die Datei ist nicht XML-konform oder enthält unsichere XML-Inhalte "
            "und konnte nicht verarbeitet werden.",
        )
        self.assertNotIn("uploaded_file_name", response.context)

    def test_post_schema_invalid_xml_shows_validation_error_not_success(self):
        response = self.client.post(
            reverse("xgewerbesteuer_default"),
            data={"bescheid": uploaded_xml("bescheid.xml", b"<nachricht/>")},
        )

        self.assertEqual(response.status_code, 200)
        self.assertNotIn("uploaded_file_name", response.context)
        self.assertNotIn("summary_items", response.context)
        self.assertNotIn("calculation_explanation", response.context)
        self.assertNotIn("validation_success", response.context)
        self.assertIn("validation_error", response.context)
        self.assertContains(response, "Validierungsfehler")
        self.assertContains(
            response,
            "Bitte wählen Sie eine gültige XML-Datei im XGewerbesteuer-Format aus.",
        )

    def test_post_rejects_xml_with_unsafe_entity_declaration(self):
        response = self.client.post(
            reverse("xgewerbesteuer_default"),
            data={
                "bescheid": uploaded_xml(
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
        self.assertEqual(
            response.context["upload_error"],
            "Die Datei ist nicht XML-konform oder enthält unsichere XML-Inhalte "
            "und konnte nicht verarbeitet werden.",
        )

    def test_post_valid_fixture_displays_summary_with_core_values(self):
        content = VALID_BESCHEID_FIXTURE.read_bytes()

        response = self.client.post(
            reverse("xgewerbesteuer_default"),
            data={"bescheid": uploaded_xml(VALID_BESCHEID_FIXTURE.name, content)},
        )

        summary_items = {
            item["label"]: item["value"] for item in response.context["summary_items"]
        }

        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            response.context["uploaded_file_name"],
            VALID_BESCHEID_FIXTURE.name,
        )
        self.assertEqual(summary_items["Gemeinde / Kommune"], "Stadt Musterhausen")
        self.assertEqual(summary_items["Steuerjahr / Erhebungszeitraum"], "2023")
        self.assertEqual(summary_items["Zahlbetrag"], "630.00")
        self.assertEqual(summary_items["Zahlungsart"], "Nachzahlung")
        self.assertEqual(summary_items["Gewerbesteuermessbetrag"], "150.00")
        self.assertEqual(summary_items["Hebesatz"], "420")
        self.assertIn("validation_success", response.context)
        self.assertContains(response, "Zusammenfassung des Bescheids")
        self.assertContains(response, "Einordnung der Zahlung")
        self.assertContains(response, "Nachzahlung")
        self.assertIn("notice_items", response.context)
        self.assertContains(response, "Hinweisbereich")
        self.assertContains(response, "Zahlbetrag beachten")
        self.assertContains(
            response,
            "Der Bescheid weist einen positiven Zahlbetrag von 630.00 aus.",
        )
        self.assertIn("status_indicator", response.context)
        self.assertEqual(response.context["status_indicator"]["status"], "deadline")
        self.assertContains(response, "Statusanzeige")
        self.assertContains(response, "Status: Frist beachten")
        self.assertIn(PDF_REPORT_SESSION_KEY, self.client.session)
        self.assertContains(response, "PDF-Bericht")
        self.assertContains(response, "PDF-Bericht herunterladen")
        self.assertIn(CSV_EXPORT_SESSION_KEY, self.client.session)
        self.assertContains(response, "CSV-Export")
        self.assertContains(response, "CSV-Export herunterladen")

    def test_valid_upload_uses_responsive_result_layout(self):
        content = VALID_BESCHEID_FIXTURE.read_bytes()

        response = self.client.post(
            reverse("xgewerbesteuer_default"),
            data={"bescheid": uploaded_xml(VALID_BESCHEID_FIXTURE.name, content)},
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "responsive-table-wrapper")
        self.assertContains(response, "responsive-table")
        self.assertContains(response, "download-actions")
        self.assertContains(response, "status-card")

    def test_valid_upload_uses_kern_result_components(self):
        content = VALID_BESCHEID_FIXTURE.read_bytes()

        response = self.client.post(
            reverse("xgewerbesteuer_default"),
            data={"bescheid": uploaded_xml(VALID_BESCHEID_FIXTURE.name, content)},
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "message-card--success")
        self.assertContains(response, "result-section")
        self.assertContains(response, "download-panel")
        self.assertContains(response, "download-action")
        self.assertContains(response, "status-card--deadline")

    def test_valid_upload_displays_due_date_calendar(self):
        content = VALID_BESCHEID_FIXTURE.read_bytes()

        response = self.client.post(
            reverse("xgewerbesteuer_default"),
            data={"bescheid": uploaded_xml(VALID_BESCHEID_FIXTURE.name, content)},
        )

        self.assertEqual(response.status_code, 200)
        self.assertIn("due_date_calendar", response.context)
        self.assertContains(response, "Kalenderansicht der Fälligkeiten")
        self.assertContains(response, "due-date-calendar")
        self.assertContains(response, "due-date-calendar-empty")
        self.assertContains(
            response,
            "Für diesen Bescheid wurden keine verwertbaren Fälligkeitstermine gefunden.",
        )

    def test_due_date_calendar_keeps_existing_table_view_visible(self):
        content = VALID_BESCHEID_FIXTURE.read_bytes()

        response = self.client.post(
            reverse("xgewerbesteuer_default"),
            data={"bescheid": uploaded_xml(VALID_BESCHEID_FIXTURE.name, content)},
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "responsive-table-wrapper")
        self.assertContains(response, "Fälligkeiten")
        self.assertContains(response, "Kalenderansicht der Fälligkeiten")

    def test_due_date_calendar_mentions_no_external_calendar_services(self):
        content = VALID_BESCHEID_FIXTURE.read_bytes()

        response = self.client.post(
            reverse("xgewerbesteuer_default"),
            data={"bescheid": uploaded_xml(VALID_BESCHEID_FIXTURE.name, content)},
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "keine externen Kalenderdienste")
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
            "xgewerbesteuer_default.html",
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
        self.assertIn("due-date-calendar-entry", rendered)

    def test_advance_payment_upload_displays_due_date_calendar_empty_state(self):
        content = ADVANCE_PAYMENT_FIXTURE.read_bytes()

        response = self.client.post(
            reverse("xgewerbesteuer_default"),
            data={"bescheid": uploaded_xml(ADVANCE_PAYMENT_FIXTURE.name, content)},
        )

        self.assertEqual(response.status_code, 200)
        self.assertIn("due_date_calendar", response.context)
        self.assertContains(response, "Kalenderansicht der Fälligkeiten")
        self.assertContains(
            response,
            "Für diesen Bescheid wurden keine verwertbaren Fälligkeitstermine gefunden.",
        )

    def test_invalid_upload_uses_kern_error_component(self):
        response = self.client.post(reverse("xgewerbesteuer_default"), data={})

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'role="alert"')
        self.assertContains(response, "message-card")
        self.assertContains(response, "message-card--error")

    def test_post_valid_current_without_previous_hides_change_comparison(self):
        content = VALID_BESCHEID_FIXTURE.read_bytes()

        response = self.client.post(
            reverse("xgewerbesteuer_default"),
            data={"bescheid": uploaded_xml(VALID_BESCHEID_FIXTURE.name, content)},
        )

        self.assertEqual(response.status_code, 200)
        self.assertNotIn("change_comparison_items", response.context)
        self.assertNotContains(response, "Änderungsvergleich zum Vorjahr")

    def test_post_advance_payment_fixture_displays_advance_payments_section(self):
        content = ADVANCE_PAYMENT_FIXTURE.read_bytes()

        response = self.client.post(
            reverse("xgewerbesteuer_default"),
            data={"bescheid": uploaded_xml(ADVANCE_PAYMENT_FIXTURE.name, content)},
        )

        self.assertEqual(response.status_code, 200)
        self.assertIn("advance_payments", response.context)
        self.assertEqual(len(response.context["advance_payments"]), 1)
        self.assertEqual(response.context["advance_payments"][0]["amount"], "147.00")
        self.assertEqual(response.context["advance_payments"][0]["period"], "2023")
        self.assertEqual(response.context["payment_classification"]["type"], "Vorauszahlung")
        self.assertContains(response, "Vorauszahlungen")
        self.assertContains(response, "147.00")
        self.assertContains(response, "Vorauszahlung")
        self.assertContains(response, "Einordnung der Zahlung")

    def test_post_valid_current_and_previous_fixture_displays_previous_year_comparison(self):
        current_content = VALID_BESCHEID_FIXTURE.read_bytes()
        previous_content = PREVIOUS_BESCHEID_FIXTURE.read_bytes()

        response = self.client.post(
            reverse("xgewerbesteuer_default"),
            data={
                "bescheid": uploaded_xml(VALID_BESCHEID_FIXTURE.name, current_content),
                "vorjahresbescheid": uploaded_xml(
                    PREVIOUS_BESCHEID_FIXTURE.name,
                    previous_content,
                ),
            },
        )

        self.assertEqual(response.status_code, 200)
        self.assertIn("current_bescheid", response.context)
        self.assertIn("previous_bescheid", response.context)
        self.assertEqual(response.context["current_bescheid"]["tax_period"], "2023")
        self.assertEqual(response.context["previous_bescheid"]["tax_period"], "2022")
        self.assertContains(response, "Vergleich mit Vorjahresbescheid")
        self.assertContains(response, "Aktueller Bescheid")
        self.assertContains(response, "Vorjahresbescheid")
        self.assertContains(response, "2023")
        self.assertContains(response, "2022")
        self.assertIn("change_comparison_items", response.context)
        self.assertContains(response, "Änderungsvergleich zum Vorjahr")
        self.assertContains(response, "+117.50")
        self.assertContains(response, "+22.93 %")
        self.assertContains(response, "Erhöhung")
        self.assertContains(response, "Hervorhebung")
        self.assertContains(response, "Wichtige Änderung")
        self.assertContains(
            response,
            "Dieser Wert hat sich gegenüber dem Vorjahr erhöht.",
        )
        self.assertContains(response, "Keine wichtige Änderung")
        self.assertContains(response, "Wichtige Änderung zum Vorjahr")
        self.assertContains(
            response,
            "Folgende Werte haben sich gegenüber dem Vorjahresbescheid deutlich verändert",
        )
        self.assertIn("status_indicator", response.context)
        self.assertEqual(response.context["status_indicator"]["status"], "warning")
        self.assertContains(response, "Status: Warnung / Auffälligkeit")

    def test_post_valid_current_with_invalid_previous_filename_keeps_current_summary(self):
        current_content = VALID_BESCHEID_FIXTURE.read_bytes()

        response = self.client.post(
            reverse("xgewerbesteuer_default"),
            data={
                "bescheid": uploaded_xml(VALID_BESCHEID_FIXTURE.name, current_content),
                "vorjahresbescheid": uploaded_xml("vorjahr.txt", b"<nachricht/>"),
            },
        )

        self.assertEqual(response.status_code, 200)
        self.assertIn("summary_items", response.context)
        self.assertNotIn("previous_bescheid", response.context)
        self.assertEqual(
            response.context["previous_upload_error"],
            "Vorjahresbescheid: Die hochgeladene Datei muss eine XML-Datei sein.",
        )
        self.assertContains(response, "Zusammenfassung des Bescheids")
        self.assertContains(response, "Upload des Vorjahresbescheids nicht möglich")

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
            reverse("xgewerbesteuer_default"),
            data={"bescheid": uploaded_xml(VALID_BESCHEID_FIXTURE.name, content)},
        )

        self.assertEqual(upload_response.status_code, 200)
        self.assertIn(PDF_REPORT_SESSION_KEY, self.client.session)

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
            reverse("xgewerbesteuer_default"),
            data={"bescheid": uploaded_xml("bescheid.xml", b"<nachricht/>")},
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
            reverse("xgewerbesteuer_default"),
            data={"bescheid": uploaded_xml(VALID_BESCHEID_FIXTURE.name, content)},
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
        self.assertIn("Stadt Musterhausen", csv_content)
        self.assertIn("Nachzahlung", csv_content)
        self.assertNotIn("<nachricht", csv_content)
        self.assertNotIn("Traceback", csv_content)
        self.assertNotIn("DEBUG", csv_content)

    def test_invalid_upload_does_not_create_csv_export(self):
        response = self.client.post(
            reverse("xgewerbesteuer_default"),
            data={"bescheid": uploaded_xml("bescheid.xml", b"<nachricht/>")},
        )

        self.assertEqual(response.status_code, 200)
        self.assertNotIn(CSV_EXPORT_SESSION_KEY, self.client.session)

        csv_response = self.client.get(reverse("xgewerbesteuer_csv_export"))

        self.assertEqual(csv_response.status_code, 404)

    def test_csv_export_after_advance_payment_upload_contains_advance_payment_row(self):
        content = ADVANCE_PAYMENT_FIXTURE.read_bytes()

        upload_response = self.client.post(
            reverse("xgewerbesteuer_default"),
            data={"bescheid": uploaded_xml(ADVANCE_PAYMENT_FIXTURE.name, content)},
        )

        self.assertEqual(upload_response.status_code, 200)

        csv_response = self.client.get(reverse("xgewerbesteuer_csv_export"))
        csv_content = csv_response.content.decode("utf-8")

        self.assertEqual(csv_response.status_code, 200)
        self.assertIn("Vorauszahlung", csv_content)
        self.assertIn("147.00", csv_content)

    def test_multi_bescheid_upload_displays_multi_year_comparison(self):
        response = self.client.post(
            reverse("xgewerbesteuer_default"),
            data={
                "bescheid": uploaded_xml(
                    VALID_BESCHEID_FIXTURE.name,
                    VALID_BESCHEID_FIXTURE.read_bytes(),
                ),
                "vergleichsbescheide": [
                    uploaded_xml(fixture.name, fixture.read_bytes())
                    for fixture in reversed(MULTI_YEAR_FIXTURES)
                ],
            },
        )

        comparison = response.context["multi_bescheid_comparison"]

        self.assertEqual(response.status_code, 200)
        self.assertEqual(comparison["valid_count"], 3)
        self.assertEqual(
            [record["tax_period"] for record in comparison["records"]],
            ["2021", "2022", "2023"],
        )
        self.assertContains(response, "Mehrjahresvergleich")
        self.assertContains(response, "Gültige Bescheide im Vergleich")
        self.assertContains(response, "400.00")
        self.assertContains(response, "512.50")
        self.assertContains(response, "630.00")
        self.assertContains(response, "Gewerbesteuermessbetrag")
        self.assertContains(response, "Hebesatz")
        self.assertContains(response, "Fälligkeiten")
        self.assertContains(response, "Vorauszahlungen")
        self.assertContains(response, "responsive-table-wrapper")
        self.assertContains(response, "responsive-table")

    def test_multi_bescheid_upload_displays_historical_development(self):
        response = self.client.post(
            reverse("xgewerbesteuer_default"),
            data={
                "bescheid": uploaded_xml(
                    VALID_BESCHEID_FIXTURE.name,
                    VALID_BESCHEID_FIXTURE.read_bytes(),
                ),
                "vergleichsbescheide": [
                    uploaded_xml(fixture.name, fixture.read_bytes())
                    for fixture in reversed(MULTI_YEAR_FIXTURES)
                ],
            },
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

    def test_historical_development_table_contains_values_and_changes(self):
        response = self.client.post(
            reverse("xgewerbesteuer_default"),
            data={
                "bescheid": uploaded_xml(
                    VALID_BESCHEID_FIXTURE.name,
                    VALID_BESCHEID_FIXTURE.read_bytes(),
                ),
                "vergleichsbescheide": [
                    uploaded_xml(fixture.name, fixture.read_bytes())
                    for fixture in MULTI_YEAR_FIXTURES
                ],
            },
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
            reverse("xgewerbesteuer_default"),
            data={
                "bescheid": uploaded_xml(
                    VALID_BESCHEID_FIXTURE.name,
                    VALID_BESCHEID_FIXTURE.read_bytes(),
                ),
                "vergleichsbescheide": [
                    uploaded_xml(fixture.name, fixture.read_bytes())
                    for fixture in MULTI_YEAR_FIXTURES
                ],
            },
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "responsive-table-wrapper")
        self.assertContains(response, "responsive-table")
        self.assertContains(response, "historical-chart")
        self.assertContains(response, "<table", html=False)
        self.assertContains(response, "Die Darstellung zeigt nur aus den Bescheiden")

    def test_historical_development_template_marks_missing_values_neutrally(self):
        historical_development = build_historical_development(
            [
                build_multi_bescheid_record(
                    comparison_bescheid("2021", amount_due="Nicht gefunden")
                ),
                build_multi_bescheid_record(comparison_bescheid("2022", "512.50")),
            ]
        )

        rendered = render_to_string(
            "xgewerbesteuer_default.html",
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
            reverse("xgewerbesteuer_default"),
            data={
                "bescheid": uploaded_xml(
                    VALID_BESCHEID_FIXTURE.name,
                    VALID_BESCHEID_FIXTURE.read_bytes(),
                ),
                "vergleichsbescheide": [
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
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            response.context["multi_bescheid_comparison"]["valid_count"],
            2,
        )
        self.assertEqual(len(response.context["multi_bescheid_upload_errors"]), 1)
        self.assertContains(response, "ungueltig.txt")
        self.assertContains(response, "Die hochgeladene Datei muss eine XML-Datei sein.")
        self.assertContains(response, "Mehrjahresvergleich")

    def test_multi_bescheid_upload_marks_duplicate_tax_periods(self):
        content = VALID_BESCHEID_FIXTURE.read_bytes()

        response = self.client.post(
            reverse("xgewerbesteuer_default"),
            data={
                "bescheid": uploaded_xml(
                    VALID_BESCHEID_FIXTURE.name,
                    VALID_BESCHEID_FIXTURE.read_bytes(),
                ),
                "vergleichsbescheide": [
                    uploaded_xml("erstbescheid-2023.xml", content),
                    uploaded_xml("aenderungsbescheid-2023.xml", content),
                ],
            },
        )

        comparison = response.context["multi_bescheid_comparison"]

        self.assertEqual(response.status_code, 200)
        self.assertEqual(comparison["duplicate_tax_periods"], ["2023"])
        self.assertContains(response, "Mehrere Bescheide enthalten denselben Steuerzeitraum")
        self.assertContains(response, "multi-comparison-duplicate")

    def test_single_valid_comparison_file_does_not_show_multi_year_comparison(self):
        response = self.client.post(
            reverse("xgewerbesteuer_default"),
            data={
                "bescheid": uploaded_xml(
                    VALID_BESCHEID_FIXTURE.name,
                    VALID_BESCHEID_FIXTURE.read_bytes(),
                ),
                "vergleichsbescheide": [
                    uploaded_xml(
                        MULTI_YEAR_FIXTURES[2].name,
                        MULTI_YEAR_FIXTURES[2].read_bytes(),
                    ),
                ],
            },
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
                reverse("xgewerbesteuer_default"),
                data={
                    "bescheid": uploaded_xml("bescheid.xml", b"<nachricht/>"),
                    "vergleichsbescheide": [
                        uploaded_xml("vergleich-2021.xml", b"<nachricht/>"),
                        uploaded_xml("vergleich-2022.xml", b"<nachricht/>"),
                    ],
                },
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
                reverse("xgewerbesteuer_default"),
                data={"bescheid": uploaded_xml("bescheid.xml", b"<nachricht/>")},
            )

        self.assertEqual(response.status_code, 200)
        self.assertIn(ICS_EXPORT_SESSION_KEY, self.client.session)
        self.assertIn(PDF_REPORT_SESSION_KEY, self.client.session)
        self.assertIn(CSV_EXPORT_SESSION_KEY, self.client.session)
        self.assertContains(response, "Fristdatei herunterladen (.ics)")
        self.assertContains(response, reverse("xgewerbesteuer_ics_export"))
        self.assertContains(
            response,
            "Die Fristdatei kann in Kalenderprogramme importiert werden.",
        )

    def test_ics_export_download_after_valid_upload(self):
        with patch(
            "xgewerbesteuer.views.process_uploaded_bescheid",
            return_value=processed_bescheid_with_due_date(),
        ):
            upload_response = self.client.post(
                reverse("xgewerbesteuer_default"),
                data={"bescheid": uploaded_xml("bescheid.xml", b"<nachricht/>")},
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
            reverse("xgewerbesteuer_default"),
            data={"bescheid": uploaded_xml(VALID_BESCHEID_FIXTURE.name, content)},
        )

        self.assertEqual(response.status_code, 200)
        self.assertNotIn(ICS_EXPORT_SESSION_KEY, self.client.session)
        self.assertNotContains(response, "Fristdatei herunterladen (.ics)")

        ics_response = self.client.get(reverse("xgewerbesteuer_ics_export"))

        self.assertEqual(ics_response.status_code, 404)

    def test_post_valid_current_with_schema_invalid_previous_keeps_current_summary(self):
        current_content = VALID_BESCHEID_FIXTURE.read_bytes()

        response = self.client.post(
            reverse("xgewerbesteuer_default"),
            data={
                "bescheid": uploaded_xml(VALID_BESCHEID_FIXTURE.name, current_content),
                "vorjahresbescheid": uploaded_xml("vorjahr.xml", b"<nachricht/>"),
            },
        )

        self.assertEqual(response.status_code, 200)
        self.assertIn("summary_items", response.context)
        self.assertNotIn("previous_bescheid", response.context)
        self.assertIn("previous_validation_error", response.context)
        self.assertContains(response, "Zusammenfassung des Bescheids")
        self.assertContains(response, "Validierungsfehler beim Vorjahresbescheid")

    def test_post_valid_current_with_oversized_previous_file_keeps_current_summary(self):
        current_content = VALID_BESCHEID_FIXTURE.read_bytes()

        response = self.client.post(
            reverse("xgewerbesteuer_default"),
            data={
                "bescheid": uploaded_xml(VALID_BESCHEID_FIXTURE.name, current_content),
                "vorjahresbescheid": uploaded_xml(
                    "vorjahr.xml",
                    b"x" * (MAX_UPLOAD_SIZE_BYTES + 1),
                ),
            },
        )

        self.assertEqual(response.status_code, 200)
        self.assertIn("summary_items", response.context)
        self.assertNotIn("previous_bescheid", response.context)
        self.assertEqual(
            response.context["previous_upload_error"],
            "Vorjahresbescheid: Die hochgeladene Datei ist zu groß.",
        )
        self.assertContains(response, "Zusammenfassung des Bescheids")
        self.assertContains(response, "Upload des Vorjahresbescheids nicht möglich")
