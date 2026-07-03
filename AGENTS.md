# AGENTS.md

## Projektueberblick

Dieses Repository enthaelt eine Django-Webanwendung fuer das xgewerbesteuer-Projekt. Die Anwendung wird lokal ueber Docker Compose betrieben und nutzt SQLite als Datenbank.

Ziel des Projekts ist eine verstaendliche Webanwendung zur Analyse digitaler Gewerbesteuerbescheide auf Basis von XGewerbesteuer. Die Anwendung soll Bescheiddaten importieren, verstaendlich zusammenfassen, Aenderungen vergleichbar machen und relevante Fristen sowie Zahlungsinformationen darstellen.

Das Projekt nutzt:

* Django als Webframework
* Docker Compose mit `compose.yaml`
* SQLite als Datenbank
* Django `staticfiles` fuer statische Dateien
* die Django-App `xgewerbesteuer`
* Umgebungsvariablen fuer Konfiguration und Secrets

## Grundregeln fuer Agents

* Keine Secrets, Tokens, Passwoerter oder privaten Schluessel in das Repository schreiben.
* Keine `.env`-Dateien committen.
* Keine Datenbankdaten, Uploads oder produktiven Mediendateien loeschen.
* Agents duerfen fuer Tests eigene Testdateien anlegen, wenn sie das Namensschema
  `test<endung>.<agent>.<dateiname>.<endung>` verwenden, zum Beispiel
  `testsqlite3.codex.import-smoke.sqlite3` oder `testxml.codex.invalid-upload.xml`.
* Solche Agent-Testdateien duerfen nach erfolgreichem Test wieder geloescht werden,
  duerfen nie committet werden und duerfen nicht ins Docker-Image gelangen.
* Keine destruktiven Docker-Befehle ohne ausdrueckliche Aufforderung ausfuehren.
* Keine Migrationen loeschen oder neu schreiben, wenn sie bereits Teil der Projektgeschichte sind.
* Aenderungen moeglichst klein, nachvollziehbar und thematisch fokussiert halten.
* Bestehende Projektstruktur respektieren.
* Bei Unsicherheit bestehende Konventionen im Code uebernehmen, statt neue Muster einzufuehren.

## Projektstruktur

Aktuelle Struktur:

```text
.
├── compose.yaml
├── compose.dev.yaml
├── Dockerfile
├── docker-entrypoint.sh
├── requirements.txt
├── .env.example
├── .editorconfig
├── .vscode/
│   ├── extensions.json
│   └── settings.json
├── README.md
├── CONTRIBUTING.md
├── AGENTS.md
├── docs/
│   ├── architektur.md
│   ├── design.md
│   ├── design-thinking.md
│   ├── datenstandard.md
│   └── testdaten.md
├── data/
└── app/
    ├── manage.py
    ├── config/
    │   ├── settings.py
    │   ├── urls.py
    │   ├── url_paths.py
    │   ├── asgi.py
    │   └── wsgi.py
    ├── static/
    │   └── branding/
    ├── staticfiles/
    ├── templates/
    │   ├── base.html
    │   ├── partials/
    │   │   ├── header.html
    │   │   ├── footer.html
    │   │   ├── messages.html
    │   │   ├── card_metric.html
    │   │   ├── alert.html
    │   │   ├── upload_form.html
    │   │   └── table_summary.html
    │   └── registration/
    │       ├── login.html
    │       ├── signup.html
    │       └── password_reset_*.html
    └── xgewerbesteuer/
        ├── models.py
        ├── views.py
        ├── urls.py
        ├── admin.py
        ├── forms.py
        ├── extractors.py
        ├── validators.py
        ├── calculations.py
        ├── comparisons.py
        ├── password_validators.py
        ├── context_processors.py
        ├── services/
        │   ├── __init__.py
        │   ├── bescheid.py
        │   ├── export.py
        │   ├── privacy.py
        │   ├── assistant.py
        │   ├── assistant_providers.py
        │   └── support_errors.py
        ├── templatetags/
        │   ├── __init__.py
        │   └── xgewerbesteuer_filters.py
        ├── migrations/
        ├── schemas/
        ├── templates/xgewerbesteuer/
        │   ├── dashboard.html
        │   ├── upload.html
        │   ├── results.html
        │   ├── help.html
        │   └── partials/assistant.html
        └── tests/
            ├── test_views.py
            ├── test_xml_uploads.py
            ├── test_fixtures.py
            ├── test_models.py
            ├── test_auth.py
            ├── test_assistant.py
            └── fixtures/
```

Falls sich die Struktur aendert, soll sich der Agent an der tatsaechlich vorhandenen Struktur im Repository orientieren.

## Docker Compose

Das Projekt wird primaer ueber Docker Compose gestartet. Die Compose-Datei heisst `compose.yaml`.
Projektbefehle, Django-Kommandos, Tests und Qualitaetspruefungen sollen grundsaetzlich
zuerst ueber Docker Compose ausgefuehrt werden. Eine Ausfuehrung direkt auf dem Host
(Bare Metal) darf erst als Fallback versucht werden, wenn die entsprechende
Docker-Ausfuehrung fehlgeschlagen ist.

Haeufige Befehle:

```bash
docker compose up -d --build
docker compose logs -f
docker compose ps
docker compose down
```

Der Django-Service heisst aktuell `web`. Django-Befehle sollen bevorzugt innerhalb dieses Containers ausgefuehrt werden:

```bash
docker compose exec web python manage.py check
docker compose exec web python manage.py migrate
docker compose exec web python manage.py makemigrations
docker compose exec web python manage.py collectstatic
docker compose exec web python manage.py test
```

Der Containername des Web-Services ist `xstandardanwendung`.

## Verbotene oder gefaehrliche Befehle

Folgende Befehle duerfen nicht ohne ausdrueckliche Zustimmung ausgefuehrt oder empfohlen werden:

```bash
docker compose down -v
docker volume rm
docker system prune -a
rm -rf
git reset --hard
git clean -fdx
```

Diese Befehle koennen Datenbankdaten, Uploads, Volumes oder lokale Arbeit loeschen.

## Django-Konventionen

* Django-Einstellungen befinden sich unter `app/config/settings.py`.
* Die fachliche App heisst `xgewerbesteuer`.
* Neue Apps sollen nur angelegt werden, wenn sie fachlich sinnvoll sind.
* Models muessen mit Migrationen versehen werden.
* Views, Forms, Templates und URLs sollen sauber getrennt werden.
* Business-Logik soll nicht unnoetig in Templates liegen.
* Komplexere Fachlogik sollte in Services, Utilities oder Modellmethoden ausgelagert werden.
* Namen von Models, Views und Templates sollen fachlich lesbar sein und zur bestehenden App-Struktur passen.
* Fuer UI-Aenderungen gelten die Regeln aus `docs/design.md` (KERN-UX, Template-Partials, Barrierearmut, Fehlerzustaende).

Nach Model-Aenderungen ausfuehren:

```bash
docker compose exec web python manage.py makemigrations
docker compose exec web python manage.py migrate
docker compose exec web python manage.py check
```

## Code-Stil und Formatierung

Formatierungsregeln sind projektweit in `.editorconfig` festgelegt und gelten
editorunabhaengig; VS Code uebernimmt zusaetzlich Einstellungen aus `.vscode/settings.json`.
Agents sollen diese Konventionen einhalten:

* UTF-8, LF-Zeilenenden, abschliessende Leerzeile, keine ueberfluessigen Leerzeichen am
  Zeilenende (Ausnahme: Markdown).
* Einrueckung mit Leerzeichen: 4 fuer Python, 2 fuer YAML, JSON und Django-HTML-Templates.
* Python-Code orientiert sich an Black (Zeilenlaenge 88; Orientierungslinien bei 88 und 120).
* Nur die tatsaechlich geaenderten Stellen anpassen, nicht unbeteiligte Dateien umformatieren.

## Kommentare und Dokumentation

Zu neuen oder geaenderten Funktionen sollen sinnvolle Kommentare oder Docstrings erstellt werden, wenn sie das Verstaendnis verbessern.

* Kommentare sollen erklaeren, warum etwas so geloest wurde, nicht nur was der Code ohnehin zeigt.
* Fachliche XGewerbesteuer-Regeln, Berechnungen, Rundungen und Fristen sollen kurz kommentiert werden.
* Sicherheitsrelevante Entscheidungen, zum Beispiel XML-Parser-Konfiguration oder Upload-Validierung, sollen kommentiert werden.
* Workarounds, Annahmen und bewusst gewaehlte Einschraenkungen sollen mit einem kurzen Kommentar nachvollziehbar gemacht werden.
* Oeffentliche Hilfsfunktionen, Services und Parser sollen einen knappen Docstring erhalten.
* Offensichtliche Kommentare wie `# Wert setzen` oder `# Funktion aufrufen` vermeiden.
* Kommentare aktuell halten, wenn der zugehoerige Code geaendert wird.

## Datenbank und Migrationen

Das Projekt verwendet SQLite. Die Entwicklungsdatenbank liegt lokal standardmaessig unter `app/dev.db.sqlite3`.
In `compose.dev.yaml` zeigt `SQLITE_PATH` im Container auf `/app/dev.db.sqlite3`; in der
produktiven `compose.yaml` zeigt `SQLITE_PATH` auf `/data/db.sqlite3` und `./data` wird
nach `/data` gemountet.
Ohne gesetztes `SQLITE_PATH` verwendet `settings.py` im Debug-Modus `app/dev.db.sqlite3`
und im Nicht-Debug-Modus `/data/db.sqlite3`.

* Bestehende Migrationen nicht nachtraeglich veraendern, wenn sie bereits verwendet wurden.
* Neue Schemaaenderungen immer ueber neue Migrationen abbilden.
* Keine produktiven Daten loeschen.
* Keine Testdaten fest in produktiven Migrationscode schreiben.
* Datenmigrationen muessen nachvollziehbar und reversibel sein, soweit sinnvoll.
* Lokale SQLite-Datenbanken nicht loeschen, ausser der Nutzer fordert dies ausdruecklich.
* Ausnahme fuer Agents: selbst angelegte Testdateien mit Namen nach
  `test<endung>.<agent>.<dateiname>.<endung>` duerfen nach erfolgreicher Validierung
  geloescht werden. Diese Dateien sind per `.gitignore` und `.dockerignore`
  ausgeschlossen, duerfen nicht committet werden und duerfen nicht ins Docker-Image gelangen.

## Static Files

Statische Dateien liegen in `app/static/`. Gesammelte Static Files liegen in `app/staticfiles/`.

Zu beachten:

* `app/staticfiles/` wird durch `collectstatic` erzeugt und sollte normalerweise nicht manuell bearbeitet werden.
* Eigene statische Projektdateien gehoeren nach `app/static/` oder in App-spezifische `static/`-Ordner.
* Der Entrypoint fuehrt beim Containerstart `collectstatic --noinput` aus.
* Bei Aenderungen an statischen Dateien moeglichst pruefen:

```bash
docker compose exec web python manage.py collectstatic
```

## Entrypoint und Laufzeit

`docker-entrypoint.sh` bereitet `/app/staticfiles` vor, fuehrt Migrationen aus, sammelt statische Dateien und startet anschliessend den Django-Development-Server.

Wichtige Punkte:

* Die Runtime-UID/GID wird ueber `PUID` und `PGID` gesteuert.
* `WEB_HOST` und `WEB_PORT` steuern Bind-Adresse und Port.
* Die automatische Migration beim Start nicht ohne Grund entfernen.
* Die Ownership-Logik fuer `/app` nicht ohne Grund entfernen.

## XGewerbesteuer-Fachlogik

Die Anwendung soll Gewerbesteuerbescheide nutzerverstaendlich darstellen.

Wichtige Begriffe:

* Gewerbeertrag
* Gewerbesteuermessbetrag
* Hebesatz
* Gewerbesteuerbetrag
* Vorauszahlung
* Faelligkeit
* Einspruchsfrist
* Aenderungsbescheid
* Vorbescheid
* Vorjahr-Vergleich
* Nachrichtenart (Gewerbesteuerbescheid, Zinsbescheid, Vorauszahlungsbescheid,
  generischer Bescheid, Berechnung – siehe `extractors.py: detect_message_type()`)

Fachliche Berechnungen muessen transparent und nachvollziehbar bleiben.

Grundformel:

```text
Gewerbesteuer = Gewerbesteuermessbetrag x Hebesatz / 100
```

Bei Unsicherheit ueber steuerliche Auslegung keine rechtlich verbindlichen Aussagen formulieren. Stattdessen neutrale Hinweise verwenden, zum Beispiel:

```text
Diese Darstellung dient der Verstaendlichkeit und ersetzt keine steuerliche Beratung.
```

## XML-Import und Uploads

Falls XGewerbesteuer-Dateien importiert werden:

* Dateityp pruefen.
* Dateigroesse begrenzen.
* XML-Struktur validieren.
* Die XSD-Dateien unter `app/xgewerbesteuer/schemas/` beruecksichtigen
  (`gewerbesteuer.xsd` und eingebundene Basis-, Adress-, Code- und Datentyp-Schemas).
* XML-Parser sicher konfigurieren.
* Fehlermeldungen fuer Nutzer verstaendlich formulieren.
* Keine vertraulichen Bescheiddaten in Logs schreiben.
* Importierte Originaldateien nicht ohne ausdrueckliche Anforderung loeschen.

## Sicherheit

* `DEBUG=True` darf nur in Entwicklung verwendet werden.
* `SECRET_KEY` niemals hardcoden.
* Uploads muessen validiert werden.
* XML-Verarbeitung muss gegen unsichere Parser-Konfigurationen abgesichert sein.
* Keine vertraulichen Bescheiddaten in Logs schreiben.
* Fehlermeldungen duerfen intern hilfreich sein, aber Nutzern keine sensiblen technischen Details offenlegen.
* `ALLOWED_HOSTS` wird ueber `DJANGO_ALLOWED_HOSTS` konfiguriert.

## Umgebungsvariablen

Wichtige Umgebungsvariablen sollten in einer `.env.example` dokumentiert werden, falls eine solche Datei angelegt wird.

Aktuell relevante Variablen:

```env
IMAGE_TAG=latest
DEBUG=1
SECRET_KEY=change-me
DJANGO_ALLOWED_HOSTS=localhost 127.0.0.1
WEB_HOST=0.0.0.0
WEB_PORT=8000
LANGUAGE_CODE=de-de
TZ=Europe/Berlin
PUID=1000
PGID=1000
SQLITE_PATH=/app/dev.db.sqlite3
LOGIN_ENABLED=1
EMAIL_HOST=localhost
EMAIL_PORT=25
EMAIL_HOST_USER=
EMAIL_HOST_PASSWORD=
EMAIL_USE_TLS=0
DEFAULT_FROM_EMAIL=webmaster@localhost
AI_ASSISTANT_ENABLED=false
AI_ASSISTANT_PROVIDER=disabled
AI_ASSISTANT_MODEL=
AI_ASSISTANT_BASE_URL=
AI_ASSISTANT_TIMEOUT_SECONDS=10
CSRF_TRUSTED_ORIGINS=
USE_X_FORWARDED_PROTO=0
COOKIES_SECURE=0
SECURE_HSTS_SECONDS=0
SECURE_HSTS_INCLUDE_SUBDOMAINS=0
SECURE_HSTS_PRELOAD=0
SECURE_SSL_REDIRECT=0
```

`LOGIN_ENABLED` steuert, ob Login/Registrierung/Passwort-Reset erreichbar sind (siehe
`docs/architektur.md`, Abschnitt „Authentifizierung und Zugriffsschutz"); ohne gesetzten
Wert greift die Heuristik `DEBUG or EMAIL_SERVER_CONFIGURED`. Die `AI_ASSISTANT_*`- und
`EMAIL_*`-Variablen sind optional; ohne Konfiguration bleiben KI-Assistent bzw.
Login/Registrierung inaktiv, die uebrige Anwendung funktioniert uneingeschraenkt.

Fuer die produktive `compose.yaml` ist der Standard fuer `SQLITE_PATH` `/data/db.sqlite3`;
die lokale Datei liegt dann unter `data/db.sqlite3`.

Die echte `.env` darf nicht committet werden.

## Tests und Qualitaetspruefung

Das Projekt arbeitet testgetrieben. Fuer neue Anforderungen, Bugfixes und fachliche
Aenderungen sollen zuerst die erwarteten Testfaelle beschrieben und als automatisierte
Tests umgesetzt werden. Danach wird die Implementierung gegen diese Tests gebaut.

Zu Codeaenderungen sollen passende Tests erstellt oder angepasst werden.

* Vor der Implementierung die testbaren Anforderungen aus Issue, Beschreibung oder
  fachlicher Regel ableiten.
* Erst Tests fuer erwartetes Verhalten, Fehlerfaelle und relevante Randfaelle schreiben
  oder bestehende Tests entsprechend erweitern.
* Danach Code so implementieren, dass diese Tests und die bestehende Suite gruenden.
* Neue Models, Views, Forms, Services, Parser, Importfunktionen und fachliche Berechnungen brauchen Tests.
* Bugfixes sollen einen Regressionstest enthalten, der den behobenen Fehler abdeckt.
* Bei XGewerbesteuer-Importen sollen gueltige und ungueltige XML-Beispiele getestet werden.
* Bei fachlichen Berechnungen sollen typische Faelle, Grenzfaelle und Rundungsverhalten getestet werden.
* Bei Views sollen Statuscode, verwendetes Template und wichtige Kontextdaten geprueft werden.
* Sicherheitsrelevante Upload- und XML-Pfade brauchen Tests fuer Ablehnung, Fehlermeldung
  und sichere Parser-Konfiguration.
* Wenn fuer eine Aenderung kein Test sinnvoll ist, soll der Grund kurz dokumentiert werden.

Tests liegen in `app/xgewerbesteuer/tests/` als Testpaket:

```text
app/xgewerbesteuer/tests/
├── __init__.py
├── test_views.py
├── test_xml_uploads.py
├── test_fixtures.py
├── test_models.py
├── test_auth.py
├── test_assistant.py
└── fixtures/
```

Bei Bedarf koennen weitere Module wie `test_services.py` ergaenzt werden.

### XGewerbesteuer-Beispieldateien (Fixtures)

`app/xgewerbesteuer/tests/fixtures/` enthaelt 15 rein fiktive XGewerbesteuer-1.4-Beispieldateien:
5 Nachrichtenarten (`bescheide.gewerbesteuer.0001`, `bescheide.zinsen.0002`,
`bescheide.vorauszahlung.0003`, `bescheide.gewerbesteuer.generisch.0010`,
`berechnung.gewerbesteuer.0021`) mit je 3 Dateien fuer die Bezugsjahre 2021-2023. Alle
Dateien beziehen sich auf denselben fiktiven Fall (Kommune „Stadt Musterhausen",
Adressat „Musterbetrieb") und werden in `test_fixtures.py` fuer Schema- und Smoke-Tests
verwendet. Details je Nachrichtenart stehen in [`docs/testdaten.md`](docs/testdaten.md).

* Dateinamen folgen dem Muster `GEWST-<Nachrichtenartcode>-<Gemeindeschluessel>-<SteuernummerBund>-<Datum>_<nachrichtenID>.xml`.
* Neue Fixtures sollen ebenfalls rein fiktive Daten (`Muster...`, Steuernummern wie `1234567890000`) verwenden.
* Fuer neue Fixtures eine bisher unbenutzte `nachrichtenID` (z. B. `00000000-0000-0000-0000-0000000000XX`) waehlen.
* Vorhandene Fixtures nicht ohne Grund veraendern, da sich Tests in `test_fixtures.py` auf konkrete Werte beziehen.

Vor Abschluss einer Aenderung moeglichst ausfuehren:

```bash
docker compose exec web python manage.py check
docker compose exec web python manage.py test
```

Nur wenn die Ausfuehrung ueber Docker Compose fehlgeschlagen ist, kann als Fallback
lokal im App-Verzeichnis geprueft werden, sofern die Abhaengigkeiten installiert sind:

```bash
cd app
python manage.py check
python manage.py test
```

Falls spaeter Tools wie Ruff oder mypy eingefuehrt werden, sollen sie ebenfalls genutzt werden:

```bash
docker compose exec web ruff check .
docker compose exec web ruff format .
docker compose exec web mypy .
```

## Arbeitsweise fuer Agents

* Vor Aenderungen relevante Dateien lesen.
* Testgetrieben arbeiten: Anforderungen in konkrete Tests uebersetzen, diese Tests zuerst
  anlegen oder erweitern und erst danach die Implementierung anpassen.
* Kleine, fokussierte Commits oder Aenderungsbloecke bevorzugen.
* Bestehende Nutzerarbeit nicht zuruecksetzen.
* Keine generierten Dateien manuell anfassen, wenn die Quelle bearbeitet werden kann.
* Zu neuen oder geaenderten Funktionen passende Tests erstellen oder bestehende Tests aktualisieren.
* Sinnvolle Kommentare oder Docstrings ergaenzen, wenn Logik, Fachregeln oder Sicherheitsentscheidungen sonst schwer nachvollziehbar sind.
* Nach Aenderungen die passenden Checks ausfuehren oder klar dokumentieren, warum sie nicht ausgefuehrt wurden.
* Zum Abschluss einer Aenderung immer eine passende Commit-Message vorschlagen.
* Bei fachlichen Steuerfragen vorsichtig formulieren und keine verbindliche Beratung geben.
