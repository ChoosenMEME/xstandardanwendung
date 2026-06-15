# Beispieldateien / Testdaten (XGewerbesteuer 1.4)

Diese Übersicht beschreibt die Testdaten, die für die automatisierten Tests des
GewSt-Bescheidassistenten verwendet werden (siehe auch [README.md](../README.md) und
[CONTRIBUTING.md](../CONTRIBUTING.md)).

Im Verzeichnis [`app/xgewerbesteuer/tests/fixtures/`](../app/xgewerbesteuer/tests/fixtures/)
liegen anonymisierte XGewerbesteuer-1.4-Beispieldateien (Musterdaten) für Berechnungen
(`berechnung.gewerbesteuer.0021`) und Bescheide (`bescheide.gewerbesteuer.generisch.0010`).
Sie decken denselben Steuerfall jeweils über mehrere Jahre ab und eignen sich daher für
Tests rund um Upload, Import, Berechnungserklärung und Vorjahresvergleich:

| Datei | Typ | Unternehmen / Fall | Bezugsjahr(e) | Besonderheit |
| --- | --- | --- | --- | --- |
| `GEWST-BR-12345678-...-2019-10-11_...0000.xml` | Berechnung | Maxi Mustermann (Musterhausen) | 2017 | Insolvenzverfahren (eröffnet 2019-07-01), Verspätungszuschlag |
| `GEWST-BR-12345678-...-2017-08-18_...0010.xml` | Berechnung | Maxi Mustermann (Musterhausen) | 2016 | Vorjahr, ohne Insolvenz |
| `GEWST-BR-12345678-...-2016-08-10_...0013.xml` | Berechnung | Maxi Mustermann (Musterhausen) | 2015 | Vorvorjahr, ohne Insolvenz, niedrigerer Hebesatz |
| `GEWST-BR-23456789-...-2020-07-14_...0000.xml` | Berechnung | Musterbetrieb & Co. KG (Musterhausen) | 2011–2013 | Änderungsbescheide & Zinsen infolge Insolvenz (eröffnet 2017-11-01) |
| `GEWST-BR-23456789-...-2011-09-05_...0011.xml` | Berechnung | Musterbetrieb & Co. KG (Musterhausen) | 2010 | Vorjahr, ohne Insolvenz |
| `GEWST-BR-23456789-...-2010-09-12_...0014.xml` | Berechnung | Musterbetrieb & Co. KG (Musterhausen) | 2009 | Vorvorjahr, ohne Insolvenz, niedrigerer Hebesatz |
| `GEWST-BS-09162000-...-2020-09-07_...0000.xml` | Bescheid | Muster AG (München) | 2018, Vorauszahlungen 2020/2021 | – |
| `GEWST-BS-09162000-...-2021-09-06_...0012.xml` | Bescheid | Muster AG (München) | 2019, Vorauszahlungen 2021/2022 | Folgejahr / Änderungsbescheid |
| `GEWST-BS-09162000-...-2022-09-05_...0015.xml` | Bescheid | Muster AG (München) | 2020, Vorauszahlungen 2022/2023 | Folgejahr / Änderungsbescheid, knüpft an Festsetzung 2019 an |

Die Dateien werden in
[`app/xgewerbesteuer/tests/test_imports.py`](../app/xgewerbesteuer/tests/test_imports.py)
als Struktur- und Smoke-Tests genutzt und dienen als Ausgangspunkt für künftige
Import-/Parser-Tests des Bescheid-Uploads.

## Herkunft der Daten

Die Beispieldateien stammen aus den offiziellen Referenzbeispielen des
XGewerbesteuer-Standards im
[XRepository](https://www.xrepository.de/details/urn:xoev-de:xunternehmen:standard:gewerbesteuer_1.4#version).
Die darüber hinausgehenden, zusätzlichen Beispieldateien (weitere Jahre und Fallvarianten
desselben Steuerfalls) wurden KI-generiert. Alle Daten sind rein fiktiv (Musterdaten) und
enthalten keine echten Bescheid- oder Personendaten.

Konventionen für neue Fixtures (rein fiktive Daten, unbenutzte `nachrichtenID` usw.) sind in
[AGENTS.md](../AGENTS.md) beschrieben.
