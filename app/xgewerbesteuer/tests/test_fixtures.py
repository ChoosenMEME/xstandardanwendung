"""Schema- und Smoke-Tests fuer XGewerbesteuer-Beispieldateien."""

import xml.etree.ElementTree as ET
from collections import Counter, defaultdict
from pathlib import Path

from django.test import SimpleTestCase
from lxml import etree

FIXTURES_DIR = Path(__file__).resolve().parent / "fixtures"
# Die Demo-Dateien der /demo/-Ansicht liegen ausserhalb von tests/, damit sie
# ins Release-Image gelangen. Sie gehoeren fachlich zum selben Beispiel-Set
# und werden hier mitvalidiert.
DEMO_DATA_DIR = Path(__file__).resolve().parents[1] / "demo_data"
SCHEMAS_DIR = Path(__file__).resolve().parents[1] / "schemas"
SCHEMA_PATH = SCHEMAS_DIR / "gewerbesteuer.xsd"

GEWST_NS = "urn:xoev-de:xunternehmen:standard:gewerbesteuer_1.4"

ERWARTETE_NACHRICHTENARTEN = {
    "bescheide.gewerbesteuer.0001",
    "bescheide.zinsen.0002",
    "bescheide.vorauszahlung.0003",
    "bescheide.gewerbesteuer.generisch.0010",
    "berechnung.gewerbesteuer.0021",
}


def fixture_paths():
    return sorted(
        list(FIXTURES_DIR.glob("*.xml")) + list(DEMO_DATA_DIR.glob("*.xml")),
        key=lambda path: path.name,
    )


def load_schema():
    parser = etree.XMLParser(resolve_entities=False, no_network=True)
    return etree.XMLSchema(etree.parse(SCHEMA_PATH, parser))


def root_name(root):
    return root.tag.rsplit("}", 1)[-1]


def bezugsjahr(root):
    for path in (
        ".//gwstVeranlagung/festsetzungsAngaben/erhebungszeitraum/bezugsjahr",
        ".//gwstZinsen/festsetzungsAngaben/erhebungszeitraum/bezugsjahr",
        ".//gwstVorauszahlungen/festsetzungsAngaben/erhebungszeitraum/bezugsjahr",
        ".//gwstBerechnung/berechnungsAngaben/erhebungszeitraum/bezugsjahr",
    ):
        element = root.find(path)
        if element is not None:
            return int(element.text)
    return None


class XGewerbesteuerFixtureTests(SimpleTestCase):
    def test_fixture_set_enthaelt_drei_dateien_je_nachrichtenart(self):
        roots = [root_name(ET.parse(path).getroot()) for path in fixture_paths()]

        self.assertEqual(set(roots), ERWARTETE_NACHRICHTENARTEN)
        self.assertEqual(Counter(roots), {name: 3 for name in ERWARTETE_NACHRICHTENARTEN})

    def test_beispieldateien_sind_wohlgeformt_schema_valide_und_konsekutiv(self):
        schema = load_schema()
        parser = etree.XMLParser(resolve_entities=False, no_network=True)
        jahre = defaultdict(list)

        for path in fixture_paths():
            with self.subTest(filename=path.name):
                document = etree.parse(path, parser)
                schema.assertValid(document)
                root = ET.parse(path).getroot()
                jahre[root_name(root)].append(bezugsjahr(root))

        for nachrichtenart, werte in jahre.items():
            self.assertEqual(sorted(werte), [2021, 2022, 2023], nachrichtenart)

    def test_gewerbesteuer_grundformel_messbetrag_mal_hebesatz(self):
        for path in fixture_paths():
            root = ET.parse(path).getroot()
            blocks = root.findall("gwstBerechnung") + root.findall("gwstVeranlagung")
            for block in blocks:
                with self.subTest(filename=path.name, block=block.tag):
                    messbetrag = float(block.find("messbetrag").text)
                    hebesatz = float(block.find("hebesatz").text)
                    aktuell_el = block.find(".//berechnungAktuell")
                    if aktuell_el is None:
                        aktuell_el = block.find(".//festsetzungAktuell")
                    self.assertAlmostEqual(
                        messbetrag * hebesatz / 100,
                        float(aktuell_el.text),
                        places=2,
                    )

    def test_ungueltiges_xml_wird_als_parsefehler_erkannt(self):
        with self.assertRaises(ET.ParseError):
            ET.fromstring("<gewst:berechnung.gewerbesteuer.0021>")
