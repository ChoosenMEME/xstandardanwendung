# Architektur

## 1. Ueberblick

Die Anwendung liest digitale Gewerbesteuerbescheide im XGewerbesteuer-1.4-Format,
extrahiert fachlich relevante Daten und stellt sie verstaendlich dar. Die Architektur
ist auf Django aufgebaut und nutzt SQLite als Datenbank, KERN-UX als UI-Framework
und Docker Compose fuer den Betrieb.

### Datenfluss

```text
XML-Datei (Upload)
  |
  v
Validierung (Dateityp, Groesse, XML-Struktur, XSD)
  |
  v
Extraktion (Gemeinde, Steuerjahr, Betraege, Faelligkeiten, Vorauszahlungen)
  |
  v
Berechnung (Formelerklaerung, Zahlungsklassifikation, Plausibilitaet)
  |
  v
Vergleich (optional: Vorjahr, Mehrjahresvergleich)
  |
  v
Darstellung (HTML mit KERN-UX, optional PDF/CSV-Export)
  |
  v
Persistenz (optional: gespeicherte Auswertungen mit Zugriffsschutz)
```

---

## 2. Ist-Zustand

### Modulstruktur

```text
app/
  config/
    settings.py          # Django-Einstellungen
    urls.py              # Root-URL-Konfiguration mit APP_PATH-Prefix
    url_paths.py         # Hilfsfunktion fuer Routenprefix
    wsgi.py / asgi.py    # Serveranbindung
  templates/
    base.html            # Basis-Template mit KERN-UX-CDN-Einbindung
  static/                # Eigene statische Dateien (aktuell leer)
  xgewerbesteuer/
    views.py             # View + Extraktion + Validierung + Berechnung + Vergleich (~719 Zeilen)
    urls.py              # Einzelne Route -> xgewerbesteuer_default
    models.py            # Leer (Anwendung ist aktuell zustandslos)
    admin.py             # Leer
    apps.py              # App-Konfiguration
    schemas/             # XSD-Dateien fuer Validierung
    templates/
      xgewerbesteuer_default.html  # Einziges Seiten-Template (~389 Zeilen)
    tests/
      test_views.py          # URL-/Routing-Tests
      test_fixtures.py       # Fixture-Struktur- und Smoke-Tests
      test_xml_uploads.py    # Extraktions-, Validierungs- und Upload-Tests
      fixtures/              # 18 anonymisierte XGewerbesteuer-XML-Dateien
```

### Bekannte Schwaechen

* `views.py` enthaelt ueber 25 Funktionen in einer einzigen Datei: Extraktion, Validierung,
  Formatierung, Berechnung, Vergleich und View-Logik sind nicht getrennt (Issue #265).
* Fehlende Werte verwenden den Sentinel-String `"Nicht gefunden"` statt `None` (Issue #263).
* Kein Datenmodell: Bescheiddaten werden nur im Request verarbeitet, nicht gespeichert.
* Ein einzelnes Template fuer alle Zustaende (Upload, Ergebnis, Fehler, Vergleich).
* Keine wiederverwendbaren Template-Partials.
* Keine eigenen Forms; Validierung geschieht direkt in der View.
* Inline-Styles statt KERN-UX-Klassen in mehreren Template-Abschnitten (Issue #37).

---

## 3. Zielarchitektur

### 3.1 Modulaufteilung

Die Geschaeftslogik wird aus `views.py` in thematisch getrennte Module aufgeteilt.
Views orchestrieren nur noch den Ablauf und delegieren an spezialisierte Module.

```text
app/xgewerbesteuer/
  views.py              # View-Funktionen, Request-Handling, Orchestrierung
  forms.py              # Django-Formulare fuer Upload und Eingaben
  models.py             # Datenmodelle (Bescheid, Auswertung)
  extractors.py         # XML-Datenextraktion
  validators.py         # Datei-, XML- und XSD-Validierung
  calculations.py       # Dezimalformatierung, Formeln, Plausibilitaet
  comparisons.py        # Vorjahresvergleich, Mehrjahresvergleich
  services/
    __init__.py
    bescheid.py         # Orchestrierung: Upload verarbeiten, Bescheiddaten aufbauen
    export.py           # PDF- und CSV-Export
    privacy.py          # Datenschutz-/Anonymisierungsmodus
  templatetags/
    __init__.py
    xgewerbesteuer_filters.py  # Template-Filter (default-Werte, Formatierung)
  urls.py
  admin.py
  apps.py
  schemas/
  templates/
  tests/
```

### 3.2 Verantwortlichkeiten

| Modul | Aufgabe | Abhaengigkeiten |
| --- | --- | --- |
| `extractors.py` | XML-Elemente suchen, Rohwerte extrahieren, `None` bei fehlenden Werten | `lxml`, `defusedxml` |
| `validators.py` | Dateityp, Groesse, XML-Parsing, XSD-Validierung | `lxml`, Schemas |
| `calculations.py` | Dezimalwerte parsen/formatieren, Formelerklaerung, Plausibilitaetspruefung | `decimal` |
| `comparisons.py` | Vorjahresvergleich, Mehrjahresvergleich, Aenderungstypen | `calculations` |
| `services/bescheid.py` | Upload verarbeiten, Bescheiddaten zusammenfuehren, Ergebnis aufbauen | `extractors`, `validators`, `calculations`, `comparisons` |
| `services/export.py` | PDF-/CSV-Erzeugung aus strukturierten Bescheiddaten | `services/bescheid` |
| `services/privacy.py` | Sensible Felder maskieren, Modus verwalten | -- |
| `forms.py` | Upload-Formular mit Validierungsregeln | Django Forms |
| `models.py` | Bescheid-Persistenz, Nutzerzuordnung | Django ORM |
| `views.py` | HTTP-Handling, Formularverarbeitung, Template-Rendering | `services`, `forms` |
| `templatetags/` | Anzeigelogik: fehlende Werte, Formatierung | -- |

### 3.3 Datenfluss im Detail

```text
Request (POST mit XML-Datei)
  |
  v
views.py: xgewerbesteuer_default()
  |-- forms.py: BescheidUploadForm.is_valid()
  |     |-- Dateityp, Groesse pruefen
  |
  v
services/bescheid.py: process_uploaded_bescheid()
  |-- validators.py: validate_xml_against_xsd()
  |-- extractors.py: extract_municipality(), extract_tax_period(), ...
  |-- calculations.py: build_calculation_explanation(), classify_payment_type()
  |-- calculations.py: check_plausibility()  [neu]
  |-- comparisons.py: build_change_comparison()  [bei Vorjahresbescheid]
  |
  v
services/bescheid.py: build_bescheid_data()
  |-- Strukturiertes Dict mit allen Auswertungsdaten
  |
  v
views.py: Template rendern mit Kontextdaten
  |
  v
Template: xgewerbesteuer_default.html
  |-- templatetags: {{ value|default_display }}
  |-- partials: {% include "partials/card_metric.html" %}
```

---

## 4. Datenmodell

### 4.1 Aktuell

Die Anwendung ist zustandslos. Bescheiddaten existieren nur waehrend der
Request-Verarbeitung als Python-Dicts.

### 4.2 Zielmodell

Fuer gespeicherte Uploads (Issue #46), historische Entwicklung (Issue #43) und
Mehrfachvergleich (Issue #42) wird ein Datenmodell eingefuehrt.

```text
Bescheid
  id                    AutoField
  user                  ForeignKey(User, null=True)  # Optional, erst mit Login
  upload_date           DateTimeField
  file_name             CharField
  file_hash             CharField                    # Duplikaterkennung
  schema_name           CharField(null=True)         # Verwendetes XSD-Schema
  municipality          CharField(null=True)         # Gemeinde/Kommune
  tax_period            CharField(null=True)         # Steuerjahr/Erhebungszeitraum
  amount_due            DecimalField(null=True)      # Zahlbetrag
  assessment_amount     DecimalField(null=True)      # Gewerbesteuermessbetrag
  assessment_rate       DecimalField(null=True)      # Hebesatz
  payment_type          CharField(null=True)         # Nachzahlung/Erstattung/...
  due_dates             JSONField(default=list)      # Faelligkeiten
  advance_payments      JSONField(default=list)      # Vorauszahlungen
  raw_xml_stored        BooleanField(default=False)  # Ob Original-XML gespeichert ist
  is_demo               BooleanField(default=False)  # Demo-Beispielfall

AdvancePayment (optional, falls Normalisierung gewuenscht)
  bescheid              ForeignKey(Bescheid)
  amount                DecimalField
  due_date              DateField(null=True)
  period                CharField(null=True)
  payment_type          CharField(null=True)
```

### 4.3 Designentscheidungen

* **Strukturierte Daten statt Roh-XML**: Gespeichert werden die extrahierten
  Auswertungsdaten, nicht das vollstaendige XML. Das reduziert Speicherbedarf und
  Datenschutzrisiken. Optionales Speichern des Original-XML ist bewusst aktivierbar.
* **User-Zuordnung optional**: Ohne Login-Feature (Issues #47, #254) bleibt `user`
  leer. Bescheide sind dann sessiongebunden oder oeffentlich.
* **JSONField fuer variable Listen**: Faelligkeiten und Vorauszahlungen haben
  unterschiedliche Laengen pro Bescheid. JSONField vermeidet unnoetige Joins
  fuer Lesezugriffe.

---

## 5. URL-Struktur

Alle Routen liegen unter dem konfigurierbaren `APP_PATH`-Prefix.

### 5.1 Aktuell

```text
/           -> xgewerbesteuer_default (Upload + Ergebnis)
/admin/     -> Django Admin
/healthz/   -> Health Check
```

### 5.2 Zielstruktur

Die URL-Struktur wird um Seiten fuer Ergebnis, Export, Historie und Demo erweitert.


```text
/                      -> Startseite / Upload
/ergebnis/<id>/        -> Auswertung eines Bescheids
/ergebnis/<id>/pdf/    -> PDF-Export
/ergebnis/<id>/csv/    -> CSV-Export
/vergleich/            -> Mehrjahresvergleich
/historie/             -> Historische Entwicklung (gespeicherte Bescheide)
/demo/                 -> Demo-Beispielfall laden
/admin/                -> Django Admin
/healthz/              -> Health Check
```

Oeffentliche Routen (Upload, Demo, Health Check) bleiben ohne Login zugaenglich.
Geschuetzte Routen (Historie, gespeicherte Ergebnisse) erfordern Authentifizierung,
sobald Login eingefuehrt wird.

---

## 6. Template-Architektur

### 6.1 Vererbung

```text
base.html                          # KERN-UX, Meta, Bloecke
  |
  +-- xgewerbesteuer_upload.html   # Upload-Formular
  +-- xgewerbesteuer_result.html   # Auswertung
  +-- xgewerbesteuer_compare.html  # Mehrjahresvergleich
  +-- xgewerbesteuer_history.html  # Gespeicherte Bescheide
  +-- xgewerbesteuer_demo.html     # Demo-Ansicht
```

### 6.2 Wiederverwendbare Partials

```text
app/templates/partials/
  navigation.html          # Hauptnavigation mit aktivem Zustand
  messages.html            # Erfolgs-/Fehler-/Hinweismeldungen
  card_metric.html         # Kennzahlen-Card (Label + Wert)
  card_payment.html        # Zahlungsinformation mit Einordnung
  table_summary.html       # Zusammenfassungstabelle
  table_comparison.html    # Vergleichstabelle (Vorjahr/Mehrjahr)
  table_advance_payments.html  # Vorauszahlungstabelle
  alert.html               # Hinweis-/Warnungsbox
  empty_state.html         # Leerezustand mit Handlungsvorschlag
  upload_form.html         # Upload-Formular
  calculation_explanation.html  # Berechnungserklaerung
  privacy_badge.html       # Datenschutzmodus-Anzeige
```

Partials werden per `{% include "partials/card_metric.html" with label=item.label value=item.value %}`
eingebunden und verwenden ausschliesslich KERN-UX-Klassen.

### 6.3 Template-Tags und Filter

```python
# templatetags/xgewerbesteuer_filters.py

@register.filter
def default_display(value):
    """Zeigt 'Nicht verfuegbar' fuer None-Werte an."""

@register.filter
def format_currency(value):
    """Formatiert Dezimalwert als '1.234,56 EUR'."""

@register.filter
def format_date_de(value):
    """Formatiert Datum als 'TT.MM.JJJJ'."""

@register.filter
def format_percent(value):
    """Formatiert Dezimalwert als '12,5 %'."""

@register.filter
def mask_sensitive(value):
    """Maskiert sensible Werte im Datenschutzmodus."""
```

Verwendung im Template:

```html
{% load xgewerbesteuer_filters %}
{{ bescheid.amount_due|format_currency|default_display }}
```

---

## 7. Services

### 7.1 Bescheid-Service

Zentrale Orchestrierung fuer die Bescheidverarbeitung. Entkoppelt die View-Logik
von Extraktion, Berechnung und Persistenz.

```python
# services/bescheid.py

def process_uploaded_bescheid(uploaded_file):
    """Validiert, parst und extrahiert Bescheiddaten.
    Gibt strukturiertes Dict oder Fehler zurueck."""

def build_bescheid_data(uploaded_file, root, schema_name):
    """Baut Auswertungsdaten aus geparster XML auf."""

def save_bescheid(bescheid_data, user=None):
    """Speichert extrahierte Daten als Bescheid-Model-Instanz."""

def load_demo_bescheid(fixture_name):
    """Laedt Demo-Beispielfall aus Fixture-Datei."""
```

### 7.2 Export-Service

Erzeugt PDF- und CSV-Exporte aus strukturierten Bescheiddaten.

```python
# services/export.py

def export_as_pdf(bescheid_data, privacy_mode=False):
    """Erzeugt PDF-Bericht. Gibt HttpResponse mit PDF zurueck."""

def export_as_csv(bescheid_data, privacy_mode=False):
    """Erzeugt CSV-Export. Gibt HttpResponse mit CSV zurueck."""
```

### 7.3 Privacy-Service

Maskierung sensibler Daten fuer Anzeige, Export und Screenshots.

```python
# services/privacy.py

SENSITIVE_FIELDS = ["municipality", "tax_number", "message_id", ...]

def mask_bescheid_data(bescheid_data):
    """Gibt Kopie mit maskierten sensiblen Feldern zurueck."""

def is_privacy_mode(request):
    """Prueft, ob Datenschutzmodus aktiv ist (Session/Parameter)."""
```

---

## 8. Authentifizierung und Zugriffsschutz

### 8.1 Stufenmodell

Die Authentifizierung wird stufenweise eingefuehrt:

| Stufe | Zustand | Oeffentlich | Geschuetzt |
| --- | --- | --- | --- |
| 1 | Ohne Login (aktuell) | Alles | Nichts |
| 2 | Django-Auth (Issue #47) | Upload, Demo, Ergebnis | Historie, gespeicherte Bescheide |
| 3 | OIDC optional (Issue #254) | Upload, Demo, Ergebnis | Historie, gespeicherte Bescheide |

### 8.2 Zugriffsregeln

* Einmaliger Upload und Auswertung bleiben immer ohne Login nutzbar.
* Gespeicherte Bescheide sind an den Nutzer gebunden (`Bescheid.user`).
* Ohne Login-Feature werden Bescheide nicht dauerhaft gespeichert.
* OIDC ist optional konfigurierbar und erzwingt keinen Login fuer oeffentliche Seiten.

---

## 9. Sicherheitsarchitektur

### XML-Verarbeitung

* `defusedxml` fuer sicheres XML-Parsing (XXE-Schutz).
* `lxml.etree` mit `resolve_entities=False`, `no_network=True`, `load_dtd=False`.
* XSD-Validierung gegen lokale Schema-Dateien.
* Maximale Dateigroesse: 5 MB.

### Datenschutz

* Keine vertraulichen Bescheiddaten in Logs.
* Keine Roh-XML-Anzeige in der Oberflaeche.
* Fehlermeldungen ohne technische Interna.
* Optionaler Anonymisierungsmodus fuer Anzeige und Export.
* Gespeicherte Daten nur mit Nutzerzuordnung zugaenglich.

### Django-Sicherheit

* CSRF-Schutz fuer alle POST-Requests.
* `SECRET_KEY` ueber Umgebungsvariable.
* `DEBUG=False` in Produktion.
* `ALLOWED_HOSTS` konfigurierbar.

---

## 10. Abhaengigkeiten

### Bestehend

| Paket | Zweck |
| --- | --- |
| Django 6.0 | Webframework |
| lxml 5-7 | XML-Parsing und XSD-Validierung |
| defusedxml | Sicheres XML-Parsing |

### Geplant

| Paket | Zweck | Benoetigt fuer |
| --- | --- | --- |
| weasyprint oder reportlab | PDF-Erzeugung | Issue #34 |
| mozilla-django-oidc oder authlib | OIDC-Anbindung | Issue #254 |

Neue Abhaengigkeiten werden nur eingefuehrt, wenn Django-Bordmittel nicht ausreichen.

---

## 11. Umsetzungsreihenfolge

Die Reihenfolge orientiert sich an Abhaengigkeiten zwischen den Issues und den
Prioritaeten (muss > soll > kann).

### Phase 1: Grundlagen bereinigen

Voraussetzung fuer alle weiteren Aenderungen.

1. **Sentinel durch None ersetzen** (Issue #263, soll):
   Template-Filter einfuehren, Extraktionsfunktionen auf `None` umstellen.
2. **Modulaufteilung** (Issue #265, kann):
   `views.py` in `extractors.py`, `validators.py`, `calculations.py`, `comparisons.py`
   aufteilen. Services-Verzeichnis anlegen.
3. **DEFAULT_AUTO_FIELD setzen** (Issue #264, kann):
   `DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"` in `settings.py`.

### Phase 2: UI/UX verbessern

Bestehende Funktionalitaet besser darstellen.

4. **KERN-UX-konformes Layout** (Issue #37, soll):
   Inline-Styles entfernen, KERN-UX-Klassen verwenden, Partials einfuehren.
5. **Responsive Design** (Issue #36, soll):
   Tabellen und Cards fuer kleine Bildschirme optimieren.
6. **Fehlerseite bei ungueligem Upload** (Issue #25, muss):
   Eigenes Fehler-Template mit verstaendlicher Meldung.
7. **UI/UX-Verbesserung der Auswertungsstrecke** (Issue #255, kann):
   Kennzahlen-Cards, visuelle Hierarchie, Leerezustaende.
8. **Ampel-/Statusanzeige** (Issue #33, soll),
   **Hinweisbereich** (Issue #32, soll),
   **Hervorhebung wichtiger Aenderungen** (Issue #31, soll),
   **Begriffserklaeung per Tooltip** (Issue #41, kann).

### Phase 3: Fachliche Erweiterungen

Neue Analysefunktionen auf Basis der bereinigten Architektur.

9. **Plausibilitaetspruefung** (Issue #44, kann):
   Formelcheck, Rundungstoleranz, Plausibilitaetshinweise.
10. **Demo-Beispielfall laden** (Issue #258, kann):
    Fixture-basierter Demo-Einstieg ohne eigene Datei.
11. **STATIC_URL an APP_PATH anpassen** (Issue #262, soll).
12. **Supportfreundliche Fehler-ID** (Issue #261, kann),
    **Validierungsdetails nur bei Fehler** (Issue #260, kann).

### Phase 4: Export

Auswertungsdaten in externen Formaten bereitstellen.

13. **Export als CSV** (Issue #35, soll):
    `services/export.py` mit CSV-Erzeugung.
14. **Export als PDF-Bericht** (Issue #34, soll):
    PDF-Erzeugung mit weasyprint oder reportlab.
15. **Download einer Fristdatei** (Issue #40, kann):
    ICS-Export fuer Kalenderanwendungen.

### Phase 5: Persistenz und Vergleich

Bescheiddaten speichern und ueber mehrere Jahre vergleichen.

16. **Datenmodell einfuehren** (Voraussetzung fuer #46, #43, #42):
    `Bescheid`-Model mit Migrationen.
17. **Speichern vergangener Uploads** (Issue #46, kann):
    Bewusstes Speichern mit Uebersicht und Loeschmoeglichkeit.
18. **Mehrere Bescheide vergleichen** (Issue #42, kann):
    Mehrfachupload oder Auswahl aus gespeicherten Bescheiden.
19. **Historische Entwicklung anzeigen** (Issue #43, kann):
    Chronologische Tabelle und optionales Diagramm.
20. **Kalenderansicht fuer Fristen** (Issue #39, kann),
    **Liquiditaetsauswirkung** (Issue #38, kann).

### Phase 6: Authentifizierung und Datenschutz

Zugriffsschutz fuer gespeicherte Daten.

21. **Benutzerkonto / Login** (Issue #47, kann):
    Django-Auth, geschuetzte Views, Nutzerzuordnung.
22. **Login mit OIDC** (Issue #254, kann):
    Optionale OIDC-Anbindung als Erweiterung.
23. **Datenschutz-/Anonymisierungsmodus** (Issue #259, kann):
    Maskierung sensibler Felder in Anzeige und Export.

---

## 12. Testarchitektur

### Teststruktur

```text
app/xgewerbesteuer/tests/
  __init__.py
  test_views.py              # View-, URL- und Integrationstests
  test_fixtures.py           # Fixture-Struktur- und Smoke-Tests
  test_xml_uploads.py        # Upload-, Extraktions- und Validierungstests
  test_extractors.py         # Unit-Tests fuer Extraktionsfunktionen
  test_validators.py         # Unit-Tests fuer Validierungslogik
  test_calculations.py       # Unit-Tests fuer Berechnungen und Plausibilitaet
  test_comparisons.py        # Unit-Tests fuer Vergleichslogik
  test_services.py           # Service-Tests (Bescheid, Export, Privacy)
  test_models.py             # Model- und Migrationstests
  test_templatetags.py       # Template-Filter-Tests
  fixtures/                  # 18 anonymisierte XGewerbesteuer-XML-Dateien
```

### Testprinzipien

* Tests werden vor der Implementierung geschrieben (testgetrieben, siehe AGENTS.md).
* Jedes neue Modul bekommt eine eigene Testdatei.
* Extraktions-, Berechnungs- und Vergleichslogik ist unabhaengig von Django testbar.
* View-Tests pruefen Statuscode, Template und Kontextdaten.
* Export-Tests pruefen Content-Type, Header und Inhalte.
* Zugriffsschutztests pruefen eigene und fremde Daten.
* Alle Tests verwenden ausschliesslich fiktive Daten und vorhandene Fixtures.
