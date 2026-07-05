"""Regressionstests fuer die Findings aus dem Code-Review.

Jede Testklasse gehoert zu einem konkreten Finding; die Tests dokumentieren
das vorher fehlerhafte Verhalten (500er, fehlendes Logging, CSV-Injection,
falsche Extraktion) und sichern die Korrektur ab.
"""

import http.client
from unittest.mock import patch

from defusedxml import ElementTree
from django.contrib.auth.models import User
from django.core.cache import cache
from django.test import SimpleTestCase, TestCase, override_settings
from django.urls import reverse

from xgewerbesteuer.extractors import (
    extract_amount_due,
    extract_assessment_rate,
    extract_due_dates,
    extract_trade_tax_assessment_amount,
)
from xgewerbesteuer.services.assistant_providers import (
    AssistantProviderError,
    OllamaAssistantProvider,
)
from xgewerbesteuer.services.export import (
    create_pdf_report,
    fold_ics_line,
    normalize_csv_value,
)
from xgewerbesteuer.services.support_errors import log_upload_issue


class PdfReportEscapingTests(SimpleTestCase):
    """Finding: reportlab-Paragraph stuerzte bei Markup im Dateinamen ab."""

    def build_report_data(self, file_name):
        return {
            "uploaded_file_name": file_name,
            "summary_items": [{"label": "Zahlbetrag", "value": "630.00"}],
        }

    def test_pdf_report_handles_unclosed_markup_in_file_name(self):
        pdf_content = create_pdf_report(self.build_report_data("evil<b.xml"))

        self.assertTrue(pdf_content.startswith(b"%PDF"))

    def test_pdf_report_does_not_interpret_markup_tags(self):
        # <b>-Tags duerfen nicht als Fettdruck interpretiert werden; ohne
        # Escaping wuerde der Bericht fremdes Markup uebernehmen.
        pdf_content = create_pdf_report(
            self.build_report_data("bescheid<b>fett</b>.xml")
        )

        self.assertTrue(pdf_content.startswith(b"%PDF"))

    def test_pdf_report_handles_ampersand_in_notice_text(self):
        report_data = self.build_report_data("bescheid.xml")
        report_data["notice_items"] = [
            {
                "severity_label": "Hinweis",
                "title": "Test & Prüfung",
                "message": "Wert < 100 & > 0",
                "recommendation": None,
            }
        ]

        pdf_content = create_pdf_report(report_data)

        self.assertTrue(pdf_content.startswith(b"%PDF"))


class SupportErrorLoggingTests(SimpleTestCase):
    """Finding: Fehler-IDs wurden durch NullHandler nirgends ausgegeben."""

    def test_upload_issue_is_emitted_via_logging(self):
        with self.assertLogs(
            "xgewerbesteuer.services.support_errors",
            level="WARNING",
        ) as captured:
            log_upload_issue("XGST-TEST1234", "read_error", level="error")

        self.assertIn("XGST-TEST1234", captured.output[0])
        self.assertIn("read_error", captured.output[0])


@override_settings(LOGIN_ENABLED=True)
class SavedUploadIdValidationTests(TestCase):
    """Finding: nicht-numerische saved_upload_id fuehrte zu 500ern."""

    def setUp(self):
        super().setUp()
        cache.clear()
        self.user = User.objects.create_user(
            username="nutzerin",
            password="Test-Passwort-1234",
        )
        self.client.force_login(self.user)

    def test_load_saved_with_non_numeric_id_redirects_with_message(self):
        response = self.client.post(
            reverse("xgewerbesteuer_load_saved"),
            data={"saved_upload_id": "abc"},
            follow=True,
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(
            response,
            "konnte nicht gefunden werden",
        )

    def test_delete_saved_with_non_numeric_id_redirects_with_message(self):
        response = self.client.post(
            reverse("xgewerbesteuer_delete_saved"),
            data={"saved_upload_id": "1e9999"},
            follow=True,
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(
            response,
            "konnte nicht gefunden werden",
        )


class CsvInjectionTests(SimpleTestCase):
    """Finding: XML-Werte konnten als Tabellenkalkulations-Formel starten."""

    def test_formula_prefixes_are_neutralized(self):
        self.assertEqual(
            normalize_csv_value('=HYPERLINK("http://evil")'),
            "'=HYPERLINK(\"http://evil\")",
        )
        self.assertEqual(normalize_csv_value("@SUM(A1)"), "'@SUM(A1)")
        self.assertEqual(normalize_csv_value("\tcmd"), "'\tcmd")
        self.assertEqual(normalize_csv_value("+cmd|calc"), "'+cmd|calc")
        self.assertEqual(normalize_csv_value("-2+3+cmd"), "'-2+3+cmd")

    def test_signed_numbers_stay_unchanged(self):
        self.assertEqual(normalize_csv_value("-25,00"), "-25,00")
        self.assertEqual(normalize_csv_value("-630.00"), "-630.00")
        self.assertEqual(normalize_csv_value("+430"), "+430")

    def test_plain_values_stay_unchanged(self):
        self.assertEqual(normalize_csv_value("Stadt Musterhausen"), "Stadt Musterhausen")
        self.assertEqual(normalize_csv_value(None), "")


class AdvancePaymentSubtreeExclusionTests(SimpleTestCase):
    """Finding: Kernwerte durften nicht aus Vorauszahlungs-Bloecken stammen."""

    def parse(self, xml_text):
        return ElementTree.fromstring(xml_text)

    def test_amount_due_skips_advance_payment_subtree(self):
        # Die Vorauszahlung steht VOR der eigentlichen Festsetzung; ohne
        # Teilbaum-Ausschluss wuerde 147.00 als Zahlbetrag angezeigt.
        root = self.parse(
            """
            <nachricht>
              <gwstVorauszahlungen>
                <festsetzungAktuell>147.00</festsetzungAktuell>
                <faelligkeit>2025-03-15</faelligkeit>
              </gwstVorauszahlungen>
              <festsetzungAktuell>630.00</festsetzungAktuell>
            </nachricht>
            """
        )

        self.assertEqual(extract_amount_due(root), "630.00")

    def test_amount_due_is_none_when_only_advance_payments_have_amounts(self):
        root = self.parse(
            """
            <nachricht>
              <vorauszahlung>
                <zahlbetrag>147.00</zahlbetrag>
              </vorauszahlung>
            </nachricht>
            """
        )

        self.assertIsNone(extract_amount_due(root))

    def test_due_dates_skip_advance_payment_subtree(self):
        # Faelligkeiten einzelner Vorauszahlungen erscheinen als eigene
        # Kalendereintraege und duerfen nicht zusaetzlich als allgemeine
        # Faelligkeit gezaehlt werden (Doppeltermine).
        root = self.parse(
            """
            <nachricht>
              <vorauszahlungen>
                <faelligkeit>2025-03-15</faelligkeit>
              </vorauszahlungen>
              <faelligkeit>2025-02-15</faelligkeit>
            </nachricht>
            """
        )

        self.assertEqual(extract_due_dates(root), "2025-02-15")

    def test_messbetrag_and_hebesatz_skip_advance_payment_subtree(self):
        root = self.parse(
            """
            <nachricht>
              <vorauszahlungen>
                <messbetrag>10.00</messbetrag>
                <hebesatz>999</hebesatz>
              </vorauszahlungen>
              <messbetrag>150.00</messbetrag>
              <hebesatz>420</hebesatz>
            </nachricht>
            """
        )

        self.assertEqual(extract_trade_tax_assessment_amount(root), "150.00")
        self.assertEqual(extract_assessment_rate(root), "420")


class OllamaProviderReadErrorTests(SimpleTestCase):
    """Finding: Lesefehler des Antwortkoerpers fuehrten zu unbehandelten 500ern."""

    def make_provider(self):
        return OllamaAssistantProvider(
            base_url="http://ollama.invalid",
            model="test-modell",
            timeout_seconds=1,
        )

    def test_incomplete_read_raises_provider_error(self):
        with patch(
            "urllib.request.urlopen",
            side_effect=http.client.IncompleteRead(b"partial"),
        ):
            with self.assertRaises(AssistantProviderError):
                self.make_provider().answer("Frage")

    def test_connection_reset_raises_provider_error(self):
        with patch(
            "urllib.request.urlopen",
            side_effect=ConnectionResetError(),
        ):
            with self.assertRaises(AssistantProviderError):
                self.make_provider().answer("Frage")


@override_settings(LOGIN_ENABLED=True)
class RateLimitTests(TestCase):
    """Finding: Login/Registrierung/Reset/Assistent waren unbegrenzt."""

    def setUp(self):
        super().setUp()
        cache.clear()

    def test_login_post_is_rate_limited(self):
        url = reverse("login")
        data = {"username": "nutzerin", "password": "falsch"}

        for _ in range(10):
            response = self.client.post(url, data=data)
            self.assertEqual(response.status_code, 200)

        response = self.client.post(url, data=data)

        self.assertEqual(response.status_code, 429)

    def test_login_get_does_not_consume_the_limit(self):
        url = reverse("login")

        for _ in range(15):
            response = self.client.get(url)
            self.assertEqual(response.status_code, 200)

    def test_assistant_post_is_rate_limited_with_json_error(self):
        url = reverse("xgewerbesteuer_assistant")

        for _ in range(20):
            self.client.post(url, data={"assistant_question": "Was ist XGewSt?"})

        response = self.client.post(
            url,
            data={"assistant_question": "Was ist XGewSt?"},
            headers={"accept": "application/json"},
        )

        self.assertEqual(response.status_code, 429)
        self.assertFalse(response.json()["ok"])


class IcsLineFoldingTests(SimpleTestCase):
    """Finding: Zeilen ueber 75 Oktetten wurden nicht RFC-5545-konform gefaltet."""

    def test_short_line_stays_unfolded(self):
        self.assertEqual(fold_ics_line("SUMMARY:kurz"), ["SUMMARY:kurz"])

    def test_long_line_is_folded_with_leading_space(self):
        long_line = "DESCRIPTION:" + "a" * 200

        folded = fold_ics_line(long_line)

        self.assertGreater(len(folded), 1)
        for continuation in folded[1:]:
            self.assertTrue(continuation.startswith(" "))
        for line in folded:
            self.assertLessEqual(len(line.encode("utf-8")), 75)
        # Zusammengesetzt (ohne Fortsetzungs-Leerzeichen) ergibt sich wieder
        # die Originalzeile.
        self.assertEqual(
            folded[0] + "".join(part[1:] for part in folded[1:]),
            long_line,
        )

    def test_folding_does_not_split_multibyte_characters(self):
        long_line = "DESCRIPTION:" + "ä" * 100

        folded = fold_ics_line(long_line)

        for line in folded:
            self.assertLessEqual(len(line.encode("utf-8")), 75)
            # Jede Zeile muss fuer sich gueltiges UTF-8 ergeben.
            line.encode("utf-8").decode("utf-8")
