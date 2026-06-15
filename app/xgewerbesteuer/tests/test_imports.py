"""Struktur- und Smoke-Tests fuer die XGewerbesteuer-Beispieldateien.

Die Dateien unter ``fixtures/`` sind XGewerbesteuer-1.4-Musterdateien
(Berechnungen und Bescheide) mit fiktiven Daten. Sie decken denselben
Aktenzeichen-/Steuernummern-Fall jeweils in mehreren Jahren ab - mit und ohne
Insolvenzverfahren - und dienen als Ausgangspunkt fuer kuenftige
Import-/Parser-Tests des Bescheid-Uploads.
"""

import xml.etree.ElementTree as ET
from pathlib import Path

from django.test import SimpleTestCase

FIXTURES_DIR = Path(__file__).resolve().parent / "fixtures"

GEWST_NS = "urn:xoev-de:xunternehmen:standard:gewerbesteuer_1.4"
ADR_NS = "urn:xoev-de:xunternehmen:standard:basismodul:adressen_1.2"
NS = {"adr": ADR_NS}

# Maxi Mustermann (Musterhausen, Gemeindeschluessel 12345678): Insolvenz ab 2019-07-01
BERECHNUNG_INSOLVENZ = "GEWST-BR-12345678-1234567890000-2019-10-11_00000000-0000-0000-0000-000000000000.xml"
BERECHNUNG_VORJAHR_OHNE_INSOLVENZ = "GEWST-BR-12345678-1234567890000-2017-08-18_00000000-0000-0000-0000-000000000010.xml"
BERECHNUNG_VORVORJAHR_OHNE_INSOLVENZ = "GEWST-BR-12345678-1234567890000-2016-08-10_00000000-0000-0000-0000-000000000013.xml"

# Musterbetrieb & Co. KG (Musterhausen, Gemeindeschluessel 23456789): Aenderungen/Zinsen nach Insolvenz ab 2017-11-01
BERECHNUNG_AENDERUNG_NACH_INSOLVENZ = "GEWST-BR-23456789-1234567890000-2020-07-14_00000000-0000-0000-0000-000000000000.xml"
BERECHNUNG_VORJAHR_OHNE_INSOLVENZ_2 = "GEWST-BR-23456789-1234567890000-2011-09-05_00000000-0000-0000-0000-000000000011.xml"
BERECHNUNG_VORVORJAHR_OHNE_INSOLVENZ_2 = "GEWST-BR-23456789-1234567890000-2010-09-12_00000000-0000-0000-0000-000000000014.xml"

# Muster AG (Muenchen, Gemeindeschluessel 09162000): drei aufeinanderfolgende Veranlagungsjahre
BESCHEID_2018 = "GEWST-BS-09162000-0000000000000-2020-09-07_00000000-0000-0000-0000-000000000000.xml"
BESCHEID_2019 = "GEWST-BS-09162000-0000000000000-2021-09-06_00000000-0000-0000-0000-000000000012.xml"
BESCHEID_2020 = "GEWST-BS-09162000-0000000000000-2022-09-05_00000000-0000-0000-0000-000000000015.xml"

ALLE_FIXTURES = [
    BERECHNUNG_INSOLVENZ,
    BERECHNUNG_VORJAHR_OHNE_INSOLVENZ,
    BERECHNUNG_VORVORJAHR_OHNE_INSOLVENZ,
    BERECHNUNG_AENDERUNG_NACH_INSOLVENZ,
    BERECHNUNG_VORJAHR_OHNE_INSOLVENZ_2,
    BERECHNUNG_VORVORJAHR_OHNE_INSOLVENZ_2,
    BESCHEID_2018,
    BESCHEID_2019,
    BESCHEID_2020,
]


def load_fixture(filename):
    """Parst eine XGewerbesteuer-Beispieldatei aus ``fixtures/``.

    ``xml.etree.ElementTree`` nutzt den expat-Parser, der externe Entities
    nicht aufloest. Diese sichere Grundkonfiguration sollte auch fuer den
    spaeteren Upload echter, nicht vertrauenswuerdiger Bescheiddateien
    beibehalten werden.
    """
    return ET.parse(FIXTURES_DIR / filename).getroot()


class XGewerbesteuerFixtureTests(SimpleTestCase):
    def test_alle_beispieldateien_vorhanden_und_wohlgeformt(self):
        for filename in ALLE_FIXTURES:
            with self.subTest(filename=filename):
                path = FIXTURES_DIR / filename
                self.assertTrue(path.is_file(), f"{filename} fehlt im fixtures-Verzeichnis")
                load_fixture(filename)  # wirft ET.ParseError bei ungueltigem XML

    def test_berechnung_root_element(self):
        root = load_fixture(BERECHNUNG_INSOLVENZ)
        self.assertEqual(root.tag, f"{{{GEWST_NS}}}berechnung.gewerbesteuer.0021")

    def test_bescheid_root_element(self):
        root = load_fixture(BESCHEID_2018)
        self.assertEqual(root.tag, f"{{{GEWST_NS}}}bescheide.gewerbesteuer.generisch.0010")

    def test_insolvenzfall_enthaelt_insolvenzeroeffnung_und_vertretung(self):
        root = load_fixture(BERECHNUNG_INSOLVENZ)

        insolvenzeroeffnung = root.find("briefkopf/insolvenzeroeffnung")
        self.assertIsNotNone(insolvenzeroeffnung)
        self.assertEqual(insolvenzeroeffnung.text, "2019-07-01")

        art_vertretung = root.find("bekanntgabeAdressat/strukturiert/artVertretung/code")
        self.assertEqual(art_vertretung.text, "02")

    def test_vorjahresberechnung_gleiches_unternehmen_ohne_insolvenz(self):
        insolvenz_root = load_fixture(BERECHNUNG_INSOLVENZ)
        vorjahr_root = load_fixture(BERECHNUNG_VORJAHR_OHNE_INSOLVENZ)

        # gleiches Unternehmen / gleiche Kommune ueber Steuernummer und Gemeindeschluessel
        self.assertEqual(
            vorjahr_root.find("briefkopf/steuernummerBund").text,
            insolvenz_root.find("briefkopf/steuernummerBund").text,
        )
        self.assertEqual(
            vorjahr_root.find("kommune/adr:gemeindeschluessel/code", NS).text,
            insolvenz_root.find("kommune/adr:gemeindeschluessel/code", NS).text,
        )

        # Vorjahr ohne Insolvenzverfahren und ohne abweichenden Bekanntgabeadressaten
        self.assertIsNone(vorjahr_root.find("briefkopf/insolvenzeroeffnung"))
        self.assertIsNone(vorjahr_root.find("bekanntgabeAdressat"))

        bezugsjahr = vorjahr_root.find("gwstBerechnung/berechnungsAngaben/erhebungszeitraum/bezugsjahr").text
        self.assertEqual(bezugsjahr, "2016")

    def test_musterbetrieb_vorjahr_ohne_insolvenz(self):
        aenderung_root = load_fixture(BERECHNUNG_AENDERUNG_NACH_INSOLVENZ)
        vorjahr_root = load_fixture(BERECHNUNG_VORJAHR_OHNE_INSOLVENZ_2)

        self.assertEqual(
            vorjahr_root.find("briefkopf/steuernummerBund").text,
            aenderung_root.find("briefkopf/steuernummerBund").text,
        )
        self.assertEqual(
            vorjahr_root.find("kommune/adr:gemeindeschluessel/code", NS).text,
            aenderung_root.find("kommune/adr:gemeindeschluessel/code", NS).text,
        )

        self.assertIsNone(vorjahr_root.find("briefkopf/insolvenzeroeffnung"))
        # Vorjahr besteht aus genau einer Erstfestsetzung, ohne Zinsen aus dem Insolvenzverfahren
        self.assertEqual(len(vorjahr_root.findall("gwstBerechnung")), 1)
        self.assertEqual(len(vorjahr_root.findall("gwstZinsen")), 0)
        self.assertGreater(len(aenderung_root.findall("gwstZinsen")), 0)

    def test_mehrjahresreihe_maxi_mustermann(self):
        jahresreihe = [
            (BERECHNUNG_VORVORJAHR_OHNE_INSOLVENZ, "2015", "440"),
            (BERECHNUNG_VORJAHR_OHNE_INSOLVENZ, "2016", "450"),
            (BERECHNUNG_INSOLVENZ, "2017", "460"),
        ]
        for filename, bezugsjahr, hebesatz in jahresreihe:
            with self.subTest(filename=filename):
                block = load_fixture(filename).find("gwstBerechnung")
                self.assertEqual(block.find("berechnungsAngaben/erhebungszeitraum/bezugsjahr").text, bezugsjahr)
                self.assertEqual(block.find("hebesatz").text, hebesatz)

        # nur das Insolvenzjahr 2017 enthaelt eine Insolvenzeroeffnung
        self.assertIsNone(load_fixture(BERECHNUNG_VORVORJAHR_OHNE_INSOLVENZ).find("briefkopf/insolvenzeroeffnung"))
        self.assertIsNone(load_fixture(BERECHNUNG_VORJAHR_OHNE_INSOLVENZ).find("briefkopf/insolvenzeroeffnung"))
        self.assertIsNotNone(load_fixture(BERECHNUNG_INSOLVENZ).find("briefkopf/insolvenzeroeffnung"))

    def test_mehrjahresreihe_musterbetrieb(self):
        root_2009 = load_fixture(BERECHNUNG_VORVORJAHR_OHNE_INSOLVENZ_2)
        root_2010 = load_fixture(BERECHNUNG_VORJAHR_OHNE_INSOLVENZ_2)
        root_2011_2013 = load_fixture(BERECHNUNG_AENDERUNG_NACH_INSOLVENZ)

        block_2009 = root_2009.find("gwstBerechnung")
        self.assertEqual(block_2009.find("berechnungsAngaben/erhebungszeitraum/bezugsjahr").text, "2009")
        self.assertEqual(block_2009.find("hebesatz").text, "440")

        block_2010 = root_2010.find("gwstBerechnung")
        self.assertEqual(block_2010.find("berechnungsAngaben/erhebungszeitraum/bezugsjahr").text, "2010")
        self.assertEqual(block_2010.find("hebesatz").text, "450")

        erstes_jahr_2011 = root_2011_2013.find("gwstBerechnung")
        self.assertEqual(erstes_jahr_2011.find("berechnungsAngaben/erhebungszeitraum/bezugsjahr").text, "2011")
        self.assertEqual(erstes_jahr_2011.find("hebesatz").text, "460")

        # erst die Jahre ab 2011 sind vom Insolvenzverfahren betroffen
        self.assertIsNone(root_2009.find("briefkopf/insolvenzeroeffnung"))
        self.assertIsNone(root_2010.find("briefkopf/insolvenzeroeffnung"))
        self.assertIsNotNone(root_2011_2013.find("briefkopf/insolvenzeroeffnung"))

    def test_bescheid_dreijahresreihe_muster_ag(self):
        bescheide = [load_fixture(f) for f in (BESCHEID_2018, BESCHEID_2019, BESCHEID_2020)]

        bezugsjahre = [
            b.find("gwstVeranlagung/festsetzungsAngaben/erhebungszeitraum/bezugsjahr").text for b in bescheide
        ]
        self.assertEqual(bezugsjahre, ["2018", "2019", "2020"])

        # die Festsetzung des Vorjahres bildet die "Bisher"-Grundlage des Folgejahres
        festsetzung_2019 = float(bescheide[1].find("gwstVeranlagung/festsetzungsAngaben/festsetzungAktuell").text)
        festsetzung_bisher_2020 = float(bescheide[2].find("gwstVeranlagung/festsetzungsAngaben/festsetzungBisher").text)
        self.assertEqual(festsetzung_2019, festsetzung_bisher_2020)

    def test_bescheid_vorjahresvergleich(self):
        bescheid_2018 = load_fixture(BESCHEID_2018)
        bescheid_2019 = load_fixture(BESCHEID_2019)

        gemeinde_2018 = bescheid_2018.find("kommune/adr:gemeindeschluessel/code", NS).text
        gemeinde_2019 = bescheid_2019.find("kommune/adr:gemeindeschluessel/code", NS).text
        self.assertEqual(gemeinde_2018, gemeinde_2019)

        bezugsjahr_2018 = bescheid_2018.find("gwstVeranlagung/festsetzungsAngaben/erhebungszeitraum/bezugsjahr").text
        bezugsjahr_2019 = bescheid_2019.find("gwstVeranlagung/festsetzungsAngaben/erhebungszeitraum/bezugsjahr").text
        self.assertEqual(bezugsjahr_2018, "2018")
        self.assertEqual(bezugsjahr_2019, "2019")

        festsetzung_2018 = float(bescheid_2018.find("gwstVeranlagung/festsetzungsAngaben/festsetzungAktuell").text)
        festsetzung_2019 = float(bescheid_2019.find("gwstVeranlagung/festsetzungsAngaben/festsetzungAktuell").text)
        self.assertNotEqual(festsetzung_2018, festsetzung_2019)

    def test_gewerbesteuer_grundformel_messbetrag_mal_hebesatz(self):
        # Grundformel laut AGENTS.md: Gewerbesteuer = Messbetrag x Hebesatz / 100
        for filename in ALLE_FIXTURES:
            root = load_fixture(filename)
            for block in root.findall("gwstBerechnung") + root.findall("gwstVeranlagung"):
                with self.subTest(filename=filename, block=block.tag):
                    messbetrag = float(block.find("messbetrag").text)
                    hebesatz = float(block.find("hebesatz").text)
                    aktuell_el = block.find(".//berechnungAktuell")
                    if aktuell_el is None:
                        aktuell_el = block.find(".//festsetzungAktuell")
                    self.assertAlmostEqual(messbetrag * hebesatz / 100, float(aktuell_el.text), places=2)

    def test_ungueltiges_xml_wird_als_parsefehler_erkannt(self):
        with self.assertRaises(ET.ParseError):
            ET.fromstring("<gewst:berechnung.gewerbesteuer.0021>")
