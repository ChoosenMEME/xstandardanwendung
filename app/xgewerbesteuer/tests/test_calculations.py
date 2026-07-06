"""Tests fuer das Parsen deutsch und technisch formatierter Zahlenwerte."""

from decimal import Decimal

from django.test import SimpleTestCase

from xgewerbesteuer.calculations import parse_decimal_value


class ParseDecimalValueTests(SimpleTestCase):
    def assert_parsed(self, raw_value, expected):
        self.assertEqual(parse_decimal_value(raw_value), Decimal(expected))

    def test_plain_xsd_decimal_values(self):
        self.assert_parsed("630.00", "630.00")
        self.assert_parsed("1234.56", "1234.56")
        self.assert_parsed("400.5", "400.5")
        self.assert_parsed("-25.00", "-25.00")
        self.assert_parsed("400", "400")

    def test_german_decimal_comma(self):
        self.assert_parsed("630,50", "630.50")
        self.assert_parsed("-0,25", "-0.25")

    def test_german_thousands_with_decimal_comma(self):
        self.assert_parsed("1.234,56", "1234.56")
        self.assert_parsed("12.345.678,90", "12345678.90")

    def test_german_thousands_without_decimal_part(self):
        # Regression fuer #316: Dreiergruppen ohne Komma sind
        # Tausendertrennzeichen, keine Dezimalpunkte.
        self.assert_parsed("1.234", "1234")
        self.assert_parsed("12.345", "12345")
        self.assert_parsed("10.000", "10000")
        self.assert_parsed("12.345.678", "12345678")
        self.assert_parsed("-4.500", "-4500")

    def test_leading_zero_group_stays_decimal(self):
        # "0.500" kann keine Tausendergruppierung sein (fuehrende 0)
        # und bleibt eine xsd:decimal-Zahl.
        self.assert_parsed("0.500", "0.500")

    def test_english_thousands_with_decimal_point(self):
        self.assert_parsed("1,234.56", "1234.56")

    def test_currency_and_percent_suffixes_are_removed(self):
        self.assert_parsed("1.234,56 EUR", "1234.56")
        self.assert_parsed("630,00 €", "630.00")
        self.assert_parsed("400 %", "400")

    def test_unparsable_values_return_none(self):
        self.assertIsNone(parse_decimal_value(None))
        self.assertIsNone(parse_decimal_value(""))
        self.assertIsNone(parse_decimal_value("abc"))
        self.assertIsNone(parse_decimal_value("1.23.45"))

    def test_decimal_passthrough(self):
        self.assertEqual(parse_decimal_value(Decimal("630.00")), Decimal("630.00"))
