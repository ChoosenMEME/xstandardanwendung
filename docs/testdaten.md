# Beispieldateien / Testdaten (XGewerbesteuer 1.4)

Diese Übersicht beschreibt die Testdaten, die für die automatisierten Tests des
GewSt-Bescheidassistenten verwendet werden (siehe auch [README.md](../README.md) und
[CONTRIBUTING.md](../CONTRIBUTING.md)).

Im Verzeichnis [`app/xgewerbesteuer/tests/fixtures/`](../app/xgewerbesteuer/tests/fixtures/)
liegen 15 rein fiktive XGewerbesteuer-1.4-Beispieldateien: 5 Nachrichtenarten mit je 3
Dateien für die Bezugsjahre 2021, 2022 und 2023. Alle Dateien beziehen sich auf denselben
fiktiven Steuerfall (Musterbetrieb, Stadt Musterhausen) und eignen sich dadurch für Tests
rund um Upload, Import, Berechnungserklärung sowie Vorjahres- und Mehrjahresvergleich:

| Nachrichtenart | Dateipräfix | Abgabeart | Bezugsjahre | Besonderheit |
| --- | --- | --- | --- | --- |
| `bescheide.gewerbesteuer.0001` | `GEWST-0001-...` | GV (Gewerbesteuer-Veranlagung) | 2021–2023 | Regulärer Gewerbesteuerbescheid |
| `bescheide.zinsen.0002` | `GEWST-0002-...` | ZS (Zinsen) | 2021–2023 | Zinsbescheid |
| `bescheide.vorauszahlung.0003` | `GEWST-0003-...` | VZ (Vorauszahlung) | 2021–2023 | Vorauszahlungsbescheid |
| `bescheide.gewerbesteuer.generisch.0010` | `GEWST-0010-...` | GV (Gewerbesteuer-Veranlagung) | 2021–2023 | Generischer Bescheid; die Jahre 2022 und 2023 werden als **Demo-Beispielfall** (`/demo/`) geladen |
| `berechnung.gewerbesteuer.0021` | `GEWST-0021-...` | GV (Gewerbesteuer-Veranlagung) | 2021–2023 | Berechnungsnachricht (kein Bescheid) mit Insolvenzeröffnung in allen drei Jahren |

Alle Dateien verwenden dieselben fiktiven Stammdaten: Kommune „Stadt Musterhausen"
(Gemeindeschlüssel `12345678`), Steuernummer Bund `1234567890000` und Adressat
„Musterbetrieb". Dadurch bilden je drei Dateien pro Nachrichtenart einen durchgehenden
Drei-Jahres-Verlauf desselben fiktiven Falls ab, wie ihn `test_fixtures.py` erwartet.

## Namensschema

Dateinamen folgen dem Muster
`GEWST-<Nachrichtenartcode>-<Gemeindeschlüssel>-<SteuernummerBund>-<Datum>_<nachrichtenID>.xml`,
zum Beispiel:

```text
GEWST-0010-12345678-1234567890000-2022-01-15_00000000-0000-0000-0000-000000000102.xml
```

Der `<Nachrichtenartcode>` (`0001`, `0002`, `0003`, `0010`, `0021`) entspricht dabei dem
Suffix der jeweiligen Nachrichtenart aus dem XGewerbesteuer-Standard (siehe Tabelle oben).

## Verwendung in Tests und Anwendung

Die Dateien werden verwendet in:

- [`app/xgewerbesteuer/tests/test_fixtures.py`](../app/xgewerbesteuer/tests/test_fixtures.py) –
  prüft, dass alle 5 Nachrichtenarten mit je 3 Dateien vorhanden, wohlgeformt, XSD-valide
  und rechnerisch konsistent (Messbetrag × Hebesatz / 100) sind.
- [`app/xgewerbesteuer/tests/test_xml_uploads.py`](../app/xgewerbesteuer/tests/test_xml_uploads.py) –
  Extraktions-, Validierungs- und Upload-Tests auf Basis einzelner Fixtures.
- [`app/xgewerbesteuer/views.py`](../app/xgewerbesteuer/views.py) (`xgewerbesteuer_demo`) –
  lädt die Dateien `GEWST-0010-...-2022-...` und `GEWST-0010-...-2023-...` als
  Demo-Beispielfall, um die Anwendung inklusive Vorjahresvergleich ohne eigenen Upload
  vorzuführen.

## Herkunft der Daten

Alle Beispieldateien sind vollständig KI-generiert auf Basis der Struktur- und
Fachvorgaben des XGewerbesteuer-Standards im
[XRepository](https://www.xrepository.de/details/urn:xoev-de:xunternehmen:standard:gewerbesteuer_1.4#version).
Die Daten sind rein fiktiv (Musterdaten) und enthalten keine echten Bescheid- oder
Personendaten.

Konventionen für neue Fixtures (rein fiktive Daten, unbenutzte `nachrichtenID` usw.) sind in
[AGENTS.md](../AGENTS.md) beschrieben.
