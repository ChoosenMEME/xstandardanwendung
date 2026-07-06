# Architektur

## 1. Ueberblick

Die Anwendung liest digitale Gewerbesteuerbescheide (und verwandte Nachrichtenarten wie
Zins-, Vorauszahlungs- und Berechnungsnachrichten) im XGewerbesteuer-1.4-Format,
extrahiert fachlich relevante Daten und stellt sie verstaendlich dar. Die Architektur
ist auf Django aufgebaut und nutzt SQLite als Datenbank, KERN-UX als UI-Framework
und Docker Compose fuer den Betrieb.

### Datenfluss

```text
XML-Datei(en) (Upload, Demo oder gespeicherte Auswertung)
  |
  v
Validierung (Dateityp, Groesse, XML-Struktur, XSD)
  |
  v
Extraktion (Nachrichtentyp, Gemeinde, Steuerjahr, Betraege, Faelligkeiten, Vorauszahlungen)
  |
  v
Berechnung (Formelerklaerung, Zahlungsklassifikation, Plausibilitaet)
  |
  v
Vergleich (bei mehreren Bescheiden: Vorjahr, Mehrjahresvergleich, historische Entwicklung)
  |
  v
Darstellung (HTML mit KERN-UX, optionaler KI-Assistent, PDF-/CSV-/ICS-Export)
  |
  v
Persistenz (optional: gespeicherte Auswertungen mit Login-Zugriffsschutz)
```

---

## 2. Modulstruktur

Die Geschaeftslogik ist thematisch in eigene Module aufgeteilt; `views.py` orchestriert
nur noch den Ablauf und delegiert an Extraktion, Validierung, Berechnung, Vergleich und
Services.

### 2.1 Verzeichnisbaum

```text
app/xgewerbesteuer/
  views.py                    # View-Funktionen, Request-Handling, Orchestrierung (~650 Zeilen)
  forms.py                    # SignupForm, LoggingPasswordResetForm
  models.py                   # SavedBescheidUpload
  constants.py                # Zentrale Konstanten (u. a. RESULT_SESSION_KEY)
  ratelimit.py                # Anfragebegrenzung fuer missbrauchsanfaellige Endpunkte
  extractors.py                # Nachrichtentyp-Erkennung und XML-Datenextraktion
  validators.py                 # Datei-, XML- und XSD-Validierung
  calculations.py               # Formatierung, Formelerklaerung, Plausibilitaetspruefung
  comparisons.py                 # Vorjahres-, Mehrjahresvergleich, historische Entwicklung
  password_validators.py       # Eigene Passwort-Komplexitaetsregeln
  context_processors.py        # Globale Template-Kontexte (Login-Status, KI-Assistent)
  management/
    commands/
      send_test_email.py       # manage.py send_test_email (Mailanbindung testen)
  services/
    __init__.py
    bescheid.py                 # Orchestrierung: Upload verarbeiten, Notices, gespeicherte Auswertungen
    export.py                   # PDF-, CSV- und ICS-Export
    privacy.py                  # Anonymisierungsmodus
    assistant.py                 # Kontext-/Prompt-Aufbereitung fuer den KI-Assistenten
    assistant_providers.py       # Austauschbare KI-Assistant-Provider (Ollama, deaktiviert)
    support_errors.py            # Supportfreundliche Fehler-IDs ohne sensible Daten im Log
    glossary.py                  # Zentrale Begriffserklaerungen (Tooltips, Hilfe)
  templatetags/
    __init__.py
    xgewerbesteuer_filters.py    # Template-Filter (default_display, format_currency, ...)
                                 # und Inclusion-Tag term_help (Begriffserklaerungen)
  urls.py
  apps.py
  schemas/                       # XSD-Dateien fuer Validierung
  demo_data/                     # 2 fiktive Demo-Dateien fuer /demo/ (im Release-Image enthalten)
  templates/
    xgewerbesteuer/
      dashboard.html             # Startseite mit gespeicherten Auswertungen
      upload.html                # Upload-Formular (mehrere Dateien, Demo-Einstieg)
      results.html                # Auswertung, Vergleich, Historie, Exporte
      help.html                   # Hilfe- und Glossarseite
      partials/
        assistant.html            # KI-Assistenten-Panel (global eingebunden)
        term_help.html             # Begriffserklaerung (via Inclusion-Tag term_help)
  tests/
    test_views.py                 # View-, URL- und Integrationstests
    test_xml_uploads.py            # Extraktions-, Validierungs- und Upload-Tests
    test_fixtures.py                # Fixture-Struktur- und Schema-Tests (inkl. demo_data)
    test_models.py                  # Model-Tests (SavedBescheidUpload)
    test_auth.py                     # Login, Registrierung, Passwort-Reset, Zugriffsschutz
    test_assistant.py                 # KI-Assistent: Kontextaufbereitung, Provider, Fehlerfaelle
    test_calculations.py              # Parsen deutsch/technisch formatierter Zahlenwerte
    test_commands.py                  # Management-Command send_test_email
    test_glossary.py                  # Begriffserklaerungen und term_help-Tag
    test_review_fixes.py              # Regressionstests zu Code-Review-Findings
    test_settings.py                  # Settings-Helfer und Env-Parsing
    fixtures/                          # 13 fiktive XGewerbesteuer-XML-Dateien (siehe docs/testdaten.md)
```

Projektweite Templates (Basis-Layout, Partials, Registrierung/Login) liegen unter
`app/templates/` (siehe [Abschnitt 5](#5-template-architektur)).

### 2.2 Verantwortlichkeiten der Module

| Modul | Aufgabe | Abhaengigkeiten |
| --- | --- | --- |
| `extractors.py` | Nachrichtentyp erkennen (`bescheide.gewerbesteuer.0001`, `bescheide.zinsen.0002`, `bescheide.vorauszahlung.0003`, `bescheide.gewerbesteuer.generisch.0010`, `berechnung.gewerbesteuer.0021`), Rohwerte extrahieren, `None` bei fehlenden Werten | `lxml`, `defusedxml` |
| `validators.py` | Dateityp, Groesse (max. 5 MB), XML-Parsing, XSD-Validierung | `lxml`, Schemas |
| `calculations.py` | Dezimal-/Datumswerte parsen und formatieren, Formelerklaerung (Messbetrag × Hebesatz), Plausibilitaetspruefung | `decimal` |
| `comparisons.py` | Vorjahresvergleich, Nachrichtenart-Vergleichshinweis, Mehrjahresvergleich, historische Entwicklung inkl. Diagrammdaten | `calculations` |
| `services/bescheid.py` | Upload-Orchestrierung, Zahlungsklassifikation, Liquiditaetswirkung, Faelligkeitskalender, Hinweis-/Statusbereich, gespeicherte Auswertungen | `extractors`, `validators`, `calculations`, `comparisons` |
| `services/export.py` | PDF- (`reportlab`), CSV- und ICS-Erzeugung aus aufbereiteten Auswertungsdaten | `services/bescheid` |
| `services/privacy.py` | Sensible Felder fuer Anzeige/Export maskieren | -- |
| `services/assistant.py` | Erlaubte Auswertungsfelder in einen Assistant-Kontext uebernehmen, Fragen validieren, Antworten aufbereiten | `services/assistant_providers` |
| `services/assistant_providers.py` | Austauschbare KI-Provider (aktuell Ollama), sicherer deaktivierter Standard | `urllib` |
| `services/support_errors.py` | Neutrale Fehler-IDs erzeugen, Upload-Probleme ohne Falldaten loggen | `logging`, `uuid` |
| `services/glossary.py` | Zentrale Begriffserklaerungen fuer Tooltips (`term_help`) und Hilfeseite | -- |
| `password_validators.py` | Gross-/Kleinbuchstabe, Ziffer, Sonderzeichen, kein Bezug zu Nutzerdaten | Django Auth |
| `context_processors.py` | `LOGIN_ENABLED`-Status und KI-Assistent global in Templates verfuegbar machen | `services/assistant` |
| `forms.py` | Registrierungsformular (`SignupForm`), Passwort-Reset mit datensparsamem Logging (`LoggingPasswordResetForm`) | Django Forms |
| `management/commands/send_test_email.py` | Test-E-Mail ueber die konfigurierte Mailanbindung versenden | Django Mail |
| `models.py` | Persistenz gespeicherter Auswertungen | Django ORM |
| `views.py` | HTTP-Handling, Formularverarbeitung, Template-Rendering | `services`, `forms`, `comparisons` |
| `templatetags/` | Anzeigelogik: fehlende Werte, Formatierung | -- |

### 2.3 Datenfluss im Detail

```text
Request (POST mit einer oder mehreren XML-Dateien, Feld "bescheide")
  |
  v
views.py: xgewerbesteuer_upload()
  |-- je Datei: validators.py + extractors.py ueber
  |     services/bescheid.py: process_uploaded_bescheid()
  |-- calculations.py: build_calculation_explanation(), build_plausibility_check()
  |-- services/bescheid.py: classify_payment_type()
  |
  v
views.py: _build_result_session_data()
  |-- sortiert alle erfolgreich gelesenen Bescheide chronologisch
  |-- letzter Bescheid = "aktuell", vorletzter = "Vorbescheid"
  |-- comparisons.py: build_change_comparison() [ab 2 Bescheiden]
  |-- comparisons.py: build_multi_bescheid_comparison(), build_historical_development() [ab 2 Bescheiden]
  |-- optional: services/bescheid.py: create_saved_upload() [Checkbox + Login]
  |
  v
Session: request.session["xgewerbesteuer_result"]
  |
  v
views.py: xgewerbesteuer_results() -> _build_result_context()
  |-- services/bescheid.py: build_notice_area(), build_status_indicator(),
  |     build_due_date_calendar(), build_liquidity_impact()
  |-- services/export.py: PDF-/CSV-/ICS-Daten in Session vorbereiten
  |
  v
Template: xgewerbesteuer/results.html (+ partials/assistant.html)
  |-- templatetags: {{ value|default_display|format_currency }}
```

Alternative Einstiege in denselben Ablauf:

* **Demo** (`/demo/`): laedt zwei feste Beispieldateien (`GEWST-0010-...-2022-...` und
  `-2023-...`) aus `app/xgewerbesteuer/demo_data/` und zeigt dadurch direkt den
  Vorjahresvergleich. Die Demo-Dateien liegen bewusst ausserhalb von `tests/`,
  weil das Test-Verzeichnis per `.dockerignore` nicht ins Release-Image gelangt.
* **Gespeicherte Auswertung laden** (`/gespeichert/laden/`, Login erforderlich): stellt
  eine einzelne zuvor gespeicherte Auswertung wieder in die Session ein (ohne erneuten
  Mehrjahresvergleich, da nur die gespeicherten Ergebnisdaten vorliegen).

---

## 3. Datenmodell

Die Anwendung speichert bewusst keine normalisierten Bescheid-Tabellen, sondern die
bereits aufbereiteten Auswertungsdaten optional als JSON:

```text
SavedBescheidUpload
  id                            AutoField
  user                          ForeignKey(User)           # Pflichtfeld; Login erforderlich
  file_name                     CharField
  file_size                     PositiveIntegerField
  uploaded_at                   DateTimeField (auto_now_add)
  municipality                  CharField, blank
  tax_period                    CharField, blank
  amount_due                    CharField, blank
  payment_type                  CharField, blank
  trade_tax_assessment_amount   CharField, blank
  assessment_rate                CharField, blank
  due_dates                     TextField, blank
  advance_payments               JSONField(default=list)
  summary_items                   JSONField(default=list)
  result_data                     JSONField(default=dict)   # vollstaendiger aufbereiteter Auswertungskontext
```

### Designentscheidungen

* **Aufbereitete Auswertungsdaten statt Roh-XML**: Gespeichert werden die bereits
  extrahierten und aufbereiteten Werte (u. a. `result_data`, `summary_items`), nicht das
  Original-XML. Das reduziert Speicherbedarf und Datenschutzrisiken.
* **`user` ist Pflichtfeld**: Gespeicherte Auswertungen setzen `user` ueber Login
  voraus (`xgewerbesteuer_upload` bietet die Speichern-Option nur eingeloggten
  Nutzer:innen an). Das frueher nullable Feld sowie das nie abgefragte
  `session_key`-Feld aus der Zeit vor dem Login (Issue #47) wurden mit
  Migration 0003 entfernt; verwaiste Alt-Zeilen ohne Nutzer loescht die
  Migration.
* **JSONField fuer variable Listen**: Faelligkeiten, Vorauszahlungen und der komplette
  Ergebniskontext haben eine variable Struktur. JSONField vermeidet unnoetige
  Normalisierung fuer ein rein lesendes Anzeigeszenario (Dashboard, erneutes Oeffnen).
* **Kein Django-Admin**: `django.contrib.admin` ist nicht installiert — es waeren
  keine Modelle registriert, und die oeffentliche Admin-Loginseite waere nur
  zusaetzliche Angriffsflaeche. Verwaltung erfolgt ausschliesslich ueber die
  Anwendung selbst.

---

## 4. URL-Struktur

Alle Routen liegen unter dem konfigurierbaren `APP_PATH`-Prefix
(`app/xgewerbesteuer/urls.py`).

```text
/                              -> Dashboard (Startseite, gespeicherte Auswertungen)
/upload/                       -> Bescheid(e) hochladen
/demo/                         -> Demo-Beispielfall laden
/ergebnis/                     -> Auswertung der aktuellen Session
/ergebnis/datenschutzmodus/    -> Datenschutzmodus umschalten (nur POST)
/ki-assistent/                 -> KI-Assistent (POST, HTML- oder JSON-Antwort)
/hilfe/                        -> Hilfe- und Glossarseite
/gespeichert/laden/             -> Gespeicherte Auswertung oeffnen (Login erforderlich)
/gespeichert/loeschen/           -> Gespeicherte Auswertung loeschen (Login erforderlich)
/pdf-bericht/                    -> PDF-Export der aktuellen Session
/csv-export/                      -> CSV-Export der aktuellen Session
/fristdatei.ics                    -> ICS-Kalenderdatei der Faelligkeiten
/login/, /logout/                   -> Django-Auth-Views
/registrieren/                       -> Selbstregistrierung
/passwort-vergessen/ (+ Folgeschritte) -> Passwort-Reset-Flow
/healthz/                               -> Health Check
```

Alle mit `require_login_enabled()` markierten Routen (Login, Logout, Registrierung,
Passwort-Reset, gespeicherte Auswertungen) liefern **404**, solange
`settings.LOGIN_ENABLED` `False` ist (siehe [Abschnitt 7](#7-authentifizierung-und-zugriffsschutz)).
Login, Registrierung, Passwort-Reset und der KI-Assistent sind zusaetzlich pro
Client-IP ratenbegrenzt (`ratelimit.py`, HTTP 429). Einen Django-Admin gibt es
nicht (siehe Designentscheidungen in Abschnitt 3).
Es gibt bewusst keine separaten Routen fuer Mehrjahresvergleich oder Historie: Beides ist
Teil von `/ergebnis/`, sobald mehrere Bescheide in der Session vorliegen.

---

## 5. Template-Architektur

### 5.1 Vererbung

```text
app/templates/base.html                     # KERN-UX, Meta, Bloecke, Navigation
  |
  +-- app/xgewerbesteuer/templates/xgewerbesteuer/dashboard.html
  +-- app/xgewerbesteuer/templates/xgewerbesteuer/upload.html
  +-- app/xgewerbesteuer/templates/xgewerbesteuer/results.html
  +-- app/xgewerbesteuer/templates/xgewerbesteuer/help.html
  +-- app/templates/registration/login.html, signup.html, password_reset_*.html
```

### 5.2 Wiederverwendbare Partials

```text
app/templates/partials/
  header.html               # Kopfbereich / Hauptnavigation
  footer.html                # Fusszeile

app/xgewerbesteuer/templates/xgewerbesteuer/partials/
  assistant.html              # Global eingebundenes KI-Assistenten-Panel
  term_help.html              # Begriffserklaerung (via Inclusion-Tag term_help)
```

Partials werden per `{% include %}` bzw. Inclusion-Tag eingebunden und verwenden
ausschliesslich KERN-UX-Klassen (siehe [`docs/design.md`](design.md)). Nicht
referenzierte Partials werden geloescht statt auf Vorrat gepflegt.

### 5.3 Template-Tags und Filter

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
```

Die Maskierung sensibler Werte im Datenschutzmodus erfolgt **nicht** ueber einen
Template-Filter, sondern ueber `services/privacy.py: anonymize_result_context()`
auf dem bereits aufbereiteten Kontext (siehe [Abschnitt 6.3](#63-privacy-service)).

### 5.4 Globale Template-Kontexte

`context_processors.py` stellt zwei projektweite Kontextvariablen bereit:

* `login_enabled` -> `LOGIN_ENABLED` fuer Navigation/Templates.
* `assistant_context` -> baut das KI-Assistenten-Panel (`partials/assistant.html`) aus
  der aktuellen Session neu auf, damit es auf jeder Seite konsistent verfuegbar ist.

---

## 6. Services im Detail

### 6.1 Bescheid-Service

Zentrale Orchestrierung fuer Upload, Aufbereitung und gespeicherte Auswertungen.

```python
# services/bescheid.py

def process_uploaded_bescheid(uploaded_file):
    """Validiert, parst und extrahiert eine hochgeladene Datei."""

def build_bescheid_data(uploaded_file, root, schema_name):
    """Baut die Auswertungsdaten aus dem geparsten XML auf."""

def classify_payment_type(amount_due, advance_payments):
    """Ordnet den Zahlbetrag ein (Nachzahlung/Erstattung/...)."""

def build_notice_area(current_bescheid, change_comparison_items=None):
    """Baut den zusammengefassten Hinweisbereich (fehlende Werte, Zahlungs-,
    Vergleichshinweise)."""

def build_liquidity_impact(current_bescheid, reference_date=None):
    """Berechnet die Liquiditaetswirkung anstehender Zahlungen."""

def build_due_date_calendar(current_bescheid):
    """Gruppiert Faelligkeiten chronologisch nach Monat."""

def create_saved_upload(request, bescheid_data, context_data):
    """Speichert eine Auswertung fuer den eingeloggten Nutzer."""
```

### 6.2 Export-Service

Erzeugt PDF-, CSV- und ICS-Exporte aus den in der Session aufbereiteten Auswertungsdaten.

```python
# services/export.py

def create_pdf_report(report_data):
    """Erzeugt einen PDF-Bericht mit reportlab."""

def create_csv_export(report_data):
    """Erzeugt einen CSV-Export der Kennzahlen."""

def create_ics_export(due_date_calendar):
    """Erzeugt eine ICS-Kalenderdatei mit Faelligkeitsterminen."""
```

### 6.3 Privacy-Service

Maskierung sensibler Daten fuer Anzeige, Export und Screenshots (Datenschutz-/
Anonymisierungsmodus).

```python
# services/privacy.py

def anonymize_value(value):
    """Ersetzt einen einzelnen Wert durch eine neutrale Platzhalterdarstellung."""

def anonymize_result_context(context):
    """Gibt eine Kopie des Auswertungskontexts mit maskierten sensiblen Feldern zurueck."""
```

### 6.4 KI-Assistent

Optionaler Assistent fuer allgemeine Bedienhilfe und Fragen zur aktuellen Auswertung
(`ASSISTANT_MODE_GENERAL` / `ASSISTANT_MODE_RESULT`). Standardmaessig deaktiviert
(`AI_ASSISTANT_ENABLED=false`); ohne Konfiguration wird die Anwendung ohne
Einschraenkung nutzbar, es erscheint lediglich ein Hinweis.

```python
# services/assistant.py

def build_assistant_context(result_context=None):
    """Uebernimmt ausschliesslich eine Positivliste bereits aufbereiteter
    Auswertungsfelder (Gemeinde, Steuerjahr, Betraege, Faelligkeiten,
    Vergleichsergebnisse, verfuegbare Exporte) - keine Rohdaten aus dem
    hochgeladenen XML, keine IDs oder Session-/Nutzerinformationen."""

def answer_assistant_question(question, result_context):
    """Validiert die Frage (Laenge, Inhalt) und ruft den konfigurierten Provider auf."""

# services/assistant_providers.py

class DisabledAssistantProvider(AssistantProvider):
    """Sicherer Standard, falls kein Provider konfiguriert ist."""

class OllamaAssistantProvider(AssistantProvider):
    """Lokaler Ollama-Provider (AI_ASSISTANT_BASE_URL/-MODEL), ohne externe
    Python-Abhaengigkeiten (nutzt urllib)."""
```

Jede Antwort ist als „KI-generierte Antwort" gekennzeichnet und enthaelt den Hinweis,
dass sie keine steuerliche Beratung ersetzt. Provider-Fehler (Timeout, nicht
erreichbar, unlesbare Antwort) werden als benutzerverstaendliche Meldung ausgegeben,
nie als technischer Fehler.

### 6.5 Support-Fehler-IDs

```python
# services/support_errors.py

def generate_error_id():
    """Erzeugt eine kurze neutrale ID (z. B. 'XGST-A1B2C3D4') ohne Bezug zu
    Eingabedaten."""

def log_upload_issue(error_id, code, level="warning", exception=None):
    """Loggt nur neutrale Metadaten (Fehler-ID, Code, Exception-Typ) - keine
    Bescheiddaten."""
```

Nutzer:innen erhalten bei Upload-Fehlern eine Fehler-ID, die im Support-Fall
zurueckverfolgt werden kann, ohne dass dafuer vertrauliche Bescheiddaten geloggt
werden muessten.

### 6.6 Glossar-Service

```python
# services/glossary.py

def get_glossary_definition(label):
    """Gibt die zentrale Erklaerung zu einem UI-Label zurueck, falls vorhanden."""
```

Zentrale, kurz gehaltene Begriffserklaerungen (Messbetrag, Hebesatz,
Faelligkeit usw.). Die Templates binden sie ueber das Inclusion-Tag
`{% term_help label %}` (`templatetags/xgewerbesteuer_filters.py`,
`partials/term_help.html`) als Tooltip ein; UI-Label-Varianten werden ueber
Aliasse auf denselben Glossarbegriff abgebildet.

---

## 7. Authentifizierung und Zugriffsschutz

### 7.1 Stufenmodell

| Stufe | Zustand | Oeffentlich | Geschuetzt |
| --- | --- | --- | --- |
| 1 | Ohne Login | Alles | Nichts |
| 2 | Django-Auth (Issue #47, umgesetzt) | Upload, Demo, Ergebnis, Hilfe, Exporte, Dashboard-Grundgeruest | Speichern/Laden/Loeschen gespeicherter Bescheide |
| 3 | OIDC optional (Issue #254, offen) | wie Stufe 2 | wie Stufe 2 |

Stufe 2 nutzt ausschliesslich Django-Bordmittel: `django.contrib.auth`
(`LoginView`, `LogoutView`, `login_required`), `UserCreationForm`
(`SignupForm`) fuer die Selbstregistrierung sowie `PasswordResetView`/
`PasswordResetConfirmView` fuer den Passwort-Vergessen-Flow. Es gibt keine
Abhaengigkeit zu allauth oder OIDC; das bleibt der optionalen Stufe 3 vorbehalten.

### 7.2 Automatische Login-Deaktivierung ohne Mailserver

Ohne echten Mailserver koennen Passwort-Reset-Mails nicht zugestellt werden. Deshalb
gilt in `config/settings.py`:

```text
LOGIN_ENABLED = DEBUG or EMAIL_SERVER_CONFIGURED
```

`EMAIL_SERVER_CONFIGURED` ist wahr, sobald `EMAIL_HOST` auf einen anderen Wert als
`localhost` gesetzt ist. Die Heuristik laesst sich per `LOGIN_ENABLED=1`/`0` explizit
uebersteuern. Ist Login deaktiviert, liefern alle betroffenen Routen (siehe
[Abschnitt 4](#4-url-struktur)) **404** statt eines Formulars, und Navigation/Dashboard
blenden die entsprechenden Links aus (`context_processors.login_enabled`).

### 7.3 Passwort-Anforderungen

Zusaetzlich zu Djangos `MinimumLengthValidator` und `CommonPasswordValidator` prueft
`password_validators.py`:

* mindestens ein Grossbuchstabe (`UppercaseValidator`)
* mindestens ein Kleinbuchstabe (`LowercaseValidator`)
* mindestens eine Ziffer (`DigitValidator`)
* mindestens ein Sonderzeichen (`SpecialCharacterValidator`)
* kein Bestandteil aus Benutzername oder E-Mail-Adresse (`NoUserInfoFragmentValidator`)

### 7.4 Welche Funktionen brauchen Login

* **Oeffentlich (kein Login):** Dashboard (`/`), Bescheid(e) hochladen (`/upload/`),
  Demo-Beispielfall (`/demo/`), Ergebnisanzeige (`/ergebnis/`), Hilfe (`/hilfe/`),
  PDF-/CSV-/ICS-Export, KI-Assistent (`/ki-assistent/`).
* **Login erforderlich:** Auswertung speichern (Checkbox beim Upload), gespeicherte
  Auswertung laden (`/gespeichert/laden/`), gespeicherte Auswertung loeschen
  (`/gespeichert/loeschen/`), Anzeige der eigenen gespeicherten Auswertungen im
  Dashboard.

### 7.5 Zugriffsregeln

* Einmaliger Upload und Auswertung bleiben immer ohne Login nutzbar.
* Gespeicherte Bescheide sind an den Nutzer gebunden (`SavedBescheidUpload.user`).
* Ohne Login werden keine Bescheide gespeichert; die Speichern-Option wird
  anonymen Nutzer:innen nicht angeboten, stattdessen ein Login-Hinweis.
* `xgewerbesteuer_load_saved` und `xgewerbesteuer_delete_saved` sind mit
  `@login_required` geschuetzt und filtern ausschliesslich nach dem
  angemeldeten Nutzer; fremde oder unbekannte IDs liefern dieselbe generische
  Fehlermeldung (kein Enumeration-Leak).
* Selbstregistrierung erfolgt ueber `SignupForm` (`UserCreationForm` + Pflicht-E-Mail
  fuer Passwort-Reset), danach automatischer Login. Es gibt keine
  E-Mail-Verifizierung, passend zum kleinen, nicht-oeffentlichen Nutzerkreis der
  Anwendung.
* Passwort-Vergessen nutzt Djangos Standardverhalten und bestaetigt jede
  Anfrage mit derselben Erfolgsseite, unabhaengig davon, ob die E-Mail-Adresse
  existiert (kein User-Enumeration-Leak).
* OIDC ist optional konfigurierbar und erzwingt keinen Login fuer oeffentliche Seiten.

---

## 8. Sicherheitsarchitektur

### XML-Verarbeitung

* `defusedxml` fuer sicheres XML-Parsing (XXE-Schutz).
* `lxml.etree` mit `resolve_entities=False`, `no_network=True`.
* XSD-Validierung gegen lokale Schema-Dateien.
* Maximale Dateigroesse: 5 MB (`validators.MAX_UPLOAD_SIZE_BYTES`).
* Mehrere Dateien pro Upload werden einzeln validiert; ungueltige Dateien blockieren
  nicht die gueltigen (`upload_errors` je Datei).

### Datenschutz

* Keine vertraulichen Bescheiddaten in Logs; Upload-Fehler werden ueber neutrale
  Fehler-IDs korrelierbar gemacht (`services/support_errors.py`).
* Keine Roh-XML-Anzeige in der Oberflaeche.
* Fehlermeldungen ohne technische Interna.
* Optionaler Anonymisierungsmodus fuer Anzeige und Export (`services/privacy.py`).
* Der KI-Assistent erhaelt nur eine explizite Positivliste bereits aufbereiteter
  Auswertungsfelder, nie das Original-XML oder Datenbank-/Session-IDs
  (siehe [Abschnitt 6.4](#64-ki-assistent)); Standard-Provider ist deaktiviert.
* Gespeicherte Daten nur mit Nutzerzuordnung zugaenglich.

### Django-Sicherheit

* CSRF-Schutz fuer alle POST-Requests.
* `SECRET_KEY` ueber Umgebungsvariable.
* `DEBUG=False` in Produktion.
* `ALLOWED_HOSTS` konfigurierbar.
* CodeQL-Scanning ist als Pull-Request-Check aktiv (siehe `CONTRIBUTING.md`).

---

## 9. Abhaengigkeiten

### Laufzeit (`requirements.txt`)

Die Versionsspannen stehen in `requirements.txt`; das Release-Image installiert
aus `requirements.lock` (exakte, reproduzierbare Versionen inkl. transitiver
Abhaengigkeiten). Die CI-Testsuite prueft weiterhin die Spannen.

| Paket | Zweck |
| --- | --- |
| Django >=6.0,<6.1 | Webframework, Auth, ORM |
| lxml >=5.0,<7.0 | XML-Parsing und XSD-Validierung |
| defusedxml | Sicheres XML-Parsing (XXE-Schutz) |
| reportlab >=4.0,<5.0 | PDF-Erzeugung (`services/export.py`) |

### Optional / zur Laufzeit konfigurierbar

| Komponente | Zweck | Aktivierung |
| --- | --- | --- |
| Ollama (extern, nicht als Python-Paket eingebunden) | KI-Assistent-Provider | `AI_ASSISTANT_ENABLED=true`, `AI_ASSISTANT_PROVIDER=ollama` |
| SMTP-Server (extern) | Passwort-Reset-Mails, schaltet Login/Registrierung frei | `EMAIL_HOST` != `localhost` oder `LOGIN_ENABLED=1` |

### Geplant

| Paket | Zweck | Benoetigt fuer |
| --- | --- | --- |
| mozilla-django-oidc oder authlib | OIDC-Anbindung (Stufe 3) | Issue #254 |

Neue Abhaengigkeiten werden nur eingefuehrt, wenn Django-Bordmittel nicht ausreichen.

---

## 10. Testarchitektur

### Teststruktur

```text
app/xgewerbesteuer/tests/
  __init__.py
  test_views.py              # View-, URL- und Integrationstests
  test_xml_uploads.py         # Upload-, Extraktions- und Validierungstests
  test_fixtures.py            # Fixture-Struktur- und Schema-Tests (XSD, Grundformel, inkl. demo_data)
  test_models.py              # Model-Tests (SavedBescheidUpload)
  test_auth.py                # Login, Registrierung, Passwort-Reset, Zugriffsschutz
  test_assistant.py           # KI-Assistent: Kontext, Provider, Fehlerfaelle
  test_calculations.py        # Parsen deutsch/technisch formatierter Zahlenwerte
  test_commands.py            # Management-Command send_test_email
  test_glossary.py            # Begriffserklaerungen und term_help-Tag
  test_review_fixes.py        # Regressionstests zu Code-Review-Findings
  test_settings.py            # Settings-Helfer und Env-Parsing
  fixtures/                   # 13 fiktive XGewerbesteuer-XML-Dateien (siehe docs/testdaten.md)
```

### Testprinzipien

* Tests werden vor der Implementierung geschrieben (testgetrieben, siehe AGENTS.md).
* Extraktions-, Berechnungs- und Vergleichslogik ist unabhaengig von Django testbar.
* View-Tests pruefen Statuscode, Template und Kontextdaten.
* Export-Tests pruefen Content-Type, Header und Inhalte.
* Zugriffsschutztests pruefen eigene und fremde Daten sowie das Verhalten bei
  deaktiviertem Login (`LOGIN_ENABLED=False` -> 404).
* Assistant-Tests pruefen Kontextaufbereitung (keine Rohdaten), Providerfehler und die
  deaktivierte Standardkonfiguration.
* Alle Tests verwenden ausschliesslich fiktive Daten und vorhandene Fixtures.

---

## 11. Bekannte technische Schulden / Ausblick

* OIDC (Stufe 3, Issue #254) ist weiterhin nur als Option vorgesehen, nicht umgesetzt.
* Der KI-Assistent unterstuetzt aktuell nur den Ollama-Provider; weitere Provider
  lassen sich in `assistant_providers.py` ergaenzen, ohne `assistant.py` oder die
  Views anzupassen.
