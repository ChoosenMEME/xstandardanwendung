"""Tests fuer zentrale Begriffserklaerungen in der Oberflaeche."""

from django.template import Context, Template
from django.test import SimpleTestCase

from xgewerbesteuer.services.glossary import (
    CORE_GLOSSARY_TERMS,
    GLOSSARY_ALIASES,
    GLOSSARY_TERMS,
    get_glossary_definition,
    get_missing_core_terms,
    normalize_glossary_term,
)


class GlossaryDefinitionTests(SimpleTestCase):
    def test_core_terms_have_short_cautious_explanations(self):
        missing_terms = get_missing_core_terms(CORE_GLOSSARY_TERMS)

        self.assertEqual(missing_terms, [])

        for term in CORE_GLOSSARY_TERMS:
            definition = get_glossary_definition(term)

            self.assertIsNotNone(definition)
            self.assertLessEqual(len(definition["description"]), 180)
            self.assertNotIn("muss", definition["description"].lower())
            self.assertNotIn("rechtsverbindlich", definition["description"].lower())

    def test_aliases_resolve_to_single_central_definition(self):
        self.assertEqual(
            get_glossary_definition("Messbetrag"),
            get_glossary_definition("Gewerbesteuermessbetrag"),
        )
        self.assertEqual(
            get_glossary_definition("Fälligkeiten"),
            get_glossary_definition("Fälligkeit"),
        )

    def test_core_terms_do_not_share_duplicate_definition_text(self):
        descriptions_by_term = {
            term: get_glossary_definition(term)["description"]
            for term in CORE_GLOSSARY_TERMS
        }

        self.assertEqual(len(descriptions_by_term), len(CORE_GLOSSARY_TERMS))
        self.assertEqual(
            len(set(descriptions_by_term.values())),
            len(CORE_GLOSSARY_TERMS),
        )

    def test_all_aliases_resolve_to_known_central_terms(self):
        for alias, canonical_term in GLOSSARY_ALIASES.items():
            with self.subTest(alias=alias):
                self.assertEqual(normalize_glossary_term(alias), canonical_term)
                self.assertIn(canonical_term, GLOSSARY_TERMS)

    def test_payment_type_label_resolves_independently_from_dynamic_value(self):
        self.assertIsNotNone(get_glossary_definition("Zahlungsart"))
        self.assertEqual(
            get_glossary_definition("Nachzahlung"),
            get_glossary_definition("Zahlungsart"),
        )


class GlossaryTemplateTagTests(SimpleTestCase):
    def render_term_help(self, label):
        template = Template(
            "{% load xgewerbesteuer_filters %}"
            "{% term_help label %}"
        )
        return template.render(Context({"label": label}))

    def test_term_help_renders_keyboard_and_screenreader_reachable_markup(self):
        rendered = self.render_term_help("Hebesatz")

        self.assertIn("<details", rendered)
        self.assertIn("<summary", rendered)
        self.assertIn("aria-label", rendered)
        self.assertIn("Hebesatz", rendered)
        self.assertIn("Prozentwert", rendered)

    def test_unknown_term_renders_nothing(self):
        self.assertEqual(self.render_term_help("Gemeinde / Kommune").strip(), "")
