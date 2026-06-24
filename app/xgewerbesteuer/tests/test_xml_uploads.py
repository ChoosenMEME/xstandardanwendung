"""Regressionstests fuer XML-Upload, Extraktion und Validierung."""

from pathlib import Path

from defusedxml import ElementTree
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import SimpleTestCase
from django.urls import reverse

from xgewerbesteuer.views import (
    MAX_UPLOAD_SIZE_BYTES,
    clean_text,
    extract_amount_due,
    extract_assessment_rate,
    extract_advance_payments,
    extract_due_dates,
    extract_municipality,
    extract_tax_period,
    extract_trade_tax_assessment_amount,
    get_local_name,
    validate_xml_against_xsd,
)


FIXTURES_DIR = Path(__file__).resolve().parent / "fixtures"
VALID_BESCHEID_FIXTURE = (
    FIXTURES_DIR
    / "GEWST-0010-12345678-1234567890000-2023-01-15_"
    "00000000-0000-0000-0000-000000000103.xml"
)
ADVANCE_PAYMENT_FIXTURE = (
    FIXTURES_DIR
    / "GEWST-0003-12345678-1234567890000-2023-01-15_"
    "00000000-0000-0000-0000-000000000033.xml"
)


def uploaded_xml(name, content):
    return SimpleUploadedFile(name, content, content_type="application/xml")


class XGewerbesteuerExtractionTests(SimpleTestCase):
    def parse(self, xml_text):
        return ElementTree.fromstring(xml_text.encode("utf-8"))

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
    def test_start_page_renders_upload_form_and_expected_summary_scope(self):
        response = self.client.get(reverse("xgewerbesteuer_default"))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Gewerbesteuerbescheid-Assistent")
        self.assertContains(response, 'name="bescheid"')
        self.assertContains(response, 'accept=".xml"')
        self.assertContains(response, "Anzeige des fälligen Zahlbetrags")

    def test_post_without_file_shows_missing_file_error(self):
        response = self.client.post(reverse("xgewerbesteuer_default"), data={})

        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            response.context["upload_error"],
            "Bitte wählen Sie eine XML-Datei aus.",
        )
        self.assertNotIn("uploaded_file_name", response.context)

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
        self.assertEqual(summary_items["Gewerbesteuermessbetrag"], "150.00")
        self.assertEqual(summary_items["Hebesatz"], "420")
        self.assertIn("validation_success", response.context)
        self.assertContains(response, "Zusammenfassung des Bescheids")

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
        self.assertContains(response, "Vorauszahlungen")
        self.assertContains(response, "147.00")
        self.assertContains(response, "Vorauszahlung")
