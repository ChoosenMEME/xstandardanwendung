"""Tests fuer Django-Management-Commands."""

from io import StringIO
from unittest import mock

from django.core import mail
from django.core.management import CommandError, call_command
from django.test import SimpleTestCase


class SendTestEmailCommandTests(SimpleTestCase):
    def test_sends_test_email(self):
        stdout = StringIO()

        call_command("send_test_email", "admin@example.com", stdout=stdout)

        self.assertEqual(len(mail.outbox), 1)
        self.assertEqual(mail.outbox[0].to, ["admin@example.com"])
        self.assertIn("Test-E-Mail", mail.outbox[0].subject)
        self.assertIn("erfolgreich versendet", stdout.getvalue())

    def test_rejects_invalid_email_address(self):
        with self.assertRaisesMessage(CommandError, "ungueltig"):
            call_command("send_test_email", "keine-email")

    @mock.patch("xgewerbesteuer.management.commands.send_test_email.send_mail")
    def test_reports_failed_delivery(self, send_mail_mock):
        send_mail_mock.return_value = 0

        with self.assertRaisesMessage(CommandError, "nicht versendet"):
            call_command("send_test_email", "admin@example.com")
