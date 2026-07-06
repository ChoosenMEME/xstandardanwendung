"""Tests fuer Settings-Helfer und Env-Parsing."""

import os
from unittest import mock

from django.core.exceptions import ImproperlyConfigured
from django.test import SimpleTestCase

from config.settings import env_int, select_email_backend


class EnvIntTests(SimpleTestCase):
    def test_returns_default_when_variable_is_missing(self):
        with mock.patch.dict(os.environ, {}, clear=False):
            os.environ.pop("XGEWST_TEST_INT", None)

            self.assertEqual(env_int("XGEWST_TEST_INT", 10), 10)

    def test_empty_value_counts_as_unset(self):
        # Compose-Durchreichungen wie VAR=${VAR:-} liefern leere Strings.
        with mock.patch.dict(os.environ, {"XGEWST_TEST_INT": ""}):
            self.assertEqual(env_int("XGEWST_TEST_INT", 25), 25)

    def test_parses_valid_integer(self):
        with mock.patch.dict(os.environ, {"XGEWST_TEST_INT": "42"}):
            self.assertEqual(env_int("XGEWST_TEST_INT", 10), 42)

    def test_invalid_value_raises_understandable_error(self):
        with mock.patch.dict(os.environ, {"XGEWST_TEST_INT": "10s"}):
            with self.assertRaises(ImproperlyConfigured) as raised:
                env_int("XGEWST_TEST_INT", 10)

        self.assertIn("XGEWST_TEST_INT", str(raised.exception))
        self.assertIn("10s", str(raised.exception))


class EmailBackendTests(SimpleTestCase):
    def test_configured_smtp_server_is_used_in_debug_mode(self):
        self.assertEqual(
            select_email_backend(debug=True, email_host="smtp.example.com"),
            "django.core.mail.backends.smtp.EmailBackend",
        )

    def test_debug_without_smtp_server_uses_console(self):
        self.assertEqual(
            select_email_backend(debug=True, email_host="localhost"),
            "django.core.mail.backends.console.EmailBackend",
        )
