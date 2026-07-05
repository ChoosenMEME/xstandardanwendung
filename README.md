# GewSt-Bescheidassistent

> 🤝 **Beitragen:** Eine Schritt-für-Schritt-Anleitung (Setup mit und ohne Docker, Branch
> anlegen, testen, Pull Request, Branch-Schutz) findet sich in
> [`CONTRIBUTING.md`](CONTRIBUTING.md).

Prüfungsleistung im Modul **Digitale Transformation** (6. Semester DSWVI, SoSe 2026).

> 📎 **Design Thinking Prozess:** Die Konzeption dieser Anwendung basiert auf einem
> vorgeschalteten Design-Thinking-Prozess (Empathize, Define, Ideate, Prototype, Test).
> Die vollständige Dokumentation findet sich unter
> [`docs/design-thinking.md`](docs/design-thinking.md).

## Inhaltsverzeichnis

- [Über das Projekt](#über-das-projekt)
- [Technologie-Stack](#technologie-stack)
- [Projektstruktur](#projektstruktur)
- [Voraussetzungen](#voraussetzungen)
- [Installation & Start](#installation--start)
- [Konfiguration](#konfiguration)
- [Nutzung](#nutzung)
- [Status & Roadmap](#status--roadmap)
- [Lizenz](#lizenz)
- [Mitwirkende & Einsatz von KI-Tools](#mitwirkende--einsatz-von-ki-tools)

## Über das Projekt

Digitale Gewerbesteuerbescheide werden zunehmend im strukturierten XÖV-Format
**XGewerbesteuer** ausgetauscht. Für Verwaltung und Software ist das ein Gewinn an
Interoperabilität – für die Empfänger:innen, häufig Inhaber:innen kleiner Unternehmen,
bleibt der Inhalt jedoch oft schwer verständlich.

Der **GewSt-Bescheidassistent** ist eine Django-Webanwendung, die digitale
Gewerbesteuerbescheide einliest und die wichtigsten Informationen – Zahlbetrag,
Fälligkeiten, Berechnungsgrundlagen und Veränderungen zum Vorjahr – verständlich
aufbereitet.

### Funktionen im Überblick

- Upload einer oder mehrerer XGewerbesteuer-XML-Dateien (Bescheid, Zins-, Vorauszahlungs-
  oder Berechnungsnachricht) mit Validierung gegen die offiziellen XSD-Schemas
- Verständliche Zusammenfassung, Berechnungserklärung (Messbetrag × Hebesatz) und
  Plausibilitätsprüfung
- Automatischer Vorjahres- und Mehrjahresvergleich inkl. historischer Entwicklung, sobald
  mehrere Bescheide vorliegen
- Fälligkeitskalender und Liquiditätswirkung anstehender Zahlungen
- Demo-Beispielfall (`/demo/`) mit fiktiven Testdaten zum Ausprobieren ohne eigenen Upload
- Export der Auswertung als PDF-Bericht, CSV-Datei oder ICS-Kalenderdatei
- Optionales Nutzerkonto (Registrierung/Login), um Auswertungen zu speichern und später
  wieder zu öffnen
- Optionaler, lokal konfigurierbarer KI-Assistent für allgemeine Bedienhilfe und Fragen zur
  aktuellen Auswertung
- Optionaler Datenschutz-/Anonymisierungsmodus für Anzeige und Export

Details zur technischen Umsetzung stehen in [`docs/architektur.md`](docs/architektur.md).

## Technologie-Stack

- **[Django](https://www.djangoproject.com/)** als Webframework (Python), inkl.
  `django.contrib.auth` für Login, Registrierung und Passwort-Reset
- **SQLite** als Datenbank
- **Docker** / **Docker Compose** für Build, Betrieb und lokale Entwicklung
- **[KERN UX](https://www.kern-ux.de/)** als UI-/Designsystem für Verwaltungsanwendungen
  (eingebunden über `base.html`)
- **[XGewerbesteuer 1.4](https://www.xrepository.de/details/urn:xoev-de:xunternehmen:standard:gewerbesteuer_1.4#version)**
  als zu verarbeitender XÖV-Datenstandard (Details: [`docs/datenstandard.md`](docs/datenstandard.md))
- **[lxml](https://lxml.de/)** / **[defusedxml](https://github.com/tiran/defusedxml)** für
  sicheres XML-Parsing und XSD-Validierung
- **[reportlab](https://www.reportlab.com/)** für den PDF-Export
- **[gunicorn](https://gunicorn.org/)** als WSGI-Server und
  **[WhiteNoise](https://whitenoise.readthedocs.io/)** für die Auslieferung
  statischer Dateien im Container-Betrieb
- **[Ollama](https://ollama.com/)** (optional, extern) als lokaler Provider für den
  KI-Assistenten – ohne Konfiguration bleibt der Assistent deaktiviert

## Projektstruktur

```text
.
├── compose.yaml                # Produktion: zieht das fertige Image von Docker Hub
├── compose.dev.yaml            # Entwicklung: baut lokal und mountet ./app
├── Dockerfile                  # Image-Definition (Python/Django)
├── docker-entrypoint.sh        # Migrationen, collectstatic, Start des Dev-Servers
├── requirements.txt            # Python-Abhängigkeiten
├── .env.example                # Beispiel-Konfiguration (siehe Konfiguration)
├── .editorconfig               # editorübergreifende Formatierungsregeln (Einrückung, Zeilenenden)
├── .vscode/                    # empfohlene Einrichtung für Visual Studio Code
│   ├── extensions.json         # empfohlene Erweiterungen (Installations-Hinweis beim Öffnen)
│   └── settings.json           # Workspace-Einstellungen (Formatierung, Django-HTML, Suche)
├── data/                       # lokale Runtime-Daten der produktiven Compose (ignoriert)
├── docs/
│   ├── architektur.md          # Architektur, Module, Services, Sicherheit, Tests
│   ├── design.md                # Verbindliche UI-/Designrichtlinie (KERN-UX)
│   ├── design-thinking.md      # Dokumentation des Design-Thinking-Prozesses
│   ├── datenstandard.md        # Erläuterung des XGewerbesteuer-Datenstandards
│   └── testdaten.md            # Übersicht der XGewerbesteuer-Beispieldateien (Tests)
├── README.md
├── LICENSE                     # MIT-Lizenz des Projekts
├── THIRD-PARTY-NOTICES.md      # Lizenzen der Drittanbieter-Komponenten
├── CONTRIBUTING.md             # Anleitung zum Mitwirken
├── AGENTS.md                   # Konventionen für KI-gestützte Beiträge
└── app/
    ├── manage.py
    ├── dev.db.sqlite3          # lokale SQLite-Datenbank der Dev-Compose/Bare-Metal
    ├── config/
    │   ├── settings.py         # Django-Settings (liest Umgebungsvariablen)
    │   ├── urls.py             # Root-URL-Konfiguration (healthz, App-Routen)
    │   ├── url_paths.py        # Hilfsfunktion für konfigurierbaren App-Pfad
    │   ├── asgi.py / wsgi.py
    │   └── __init__.py
    ├── static/                 # eigene statische Dateien
    │   ├── branding/           # Logo/Favicon (logo.svg, favicon.svg/.ico, apple-touch-icon.png)
    │   └── vendor/kern/        # Lokal ausgeliefertes KERN-UX inkl. Fira Sans (kein CDN)
    ├── staticfiles/            # Ergebnis von collectstatic (generiert)
    ├── templates/
    │   ├── base.html           # Basistemplate inkl. KERN-UX-Einbindung
    │   ├── partials/           # projektweite Partials (Header, Footer)
    │   └── registration/       # Login, Registrierung, Passwort-Reset-Flow
    └── xgewerbesteuer/         # Fachliche App
        ├── models.py           # SavedBescheidUpload
        ├── views.py
        ├── urls.py
        ├── apps.py             # inkl. System-Check fuer das SQLite-Verzeichnis
        ├── forms.py            # Upload- und Registrierungsformular
        ├── ratelimit.py        # Anfragebegrenzung für Login/Registrierung/Reset/KI-Assistent
        ├── extractors.py       # Nachrichtentyp-Erkennung und XML-Datenextraktion
        ├── validators.py       # Datei-, XML- und XSD-Validierung
        ├── calculations.py     # Formatierung, Formelerklärung, Plausibilitätsprüfung
        ├── comparisons.py      # Vorjahres-/Mehrjahresvergleich, historische Entwicklung
        ├── password_validators.py   # Eigene Passwort-Komplexitätsregeln
        ├── context_processors.py    # Globale Template-Kontexte (Login-Status, KI-Assistent)
        ├── services/
        │   ├── bescheid.py     # Upload-Orchestrierung, Notices, gespeicherte Auswertungen
        │   ├── export.py       # PDF-, CSV- und ICS-Export
        │   ├── privacy.py      # Anonymisierungsmodus
        │   ├── assistant.py    # Kontextaufbereitung für den KI-Assistenten
        │   ├── assistant_providers.py  # Austauschbare KI-Provider (Ollama, deaktiviert)
        │   └── support_errors.py       # Supportfreundliche Fehler-IDs ohne sensible Daten
        ├── templatetags/       # Template-Filter (Währung, Datum, Prozent, Platzhalter)
        ├── migrations/
        ├── schemas/            # XGewerbesteuer-XSD-Dateien fuer XML-Validierung
        ├── templates/xgewerbesteuer/  # dashboard.html, upload.html, results.html, help.html, ...
        └── tests/
            ├── test_views.py       # Routing- und View-Tests
            ├── test_xml_uploads.py # Extraktions-, Validierungs- und Upload-Tests
            ├── test_fixtures.py    # Schema-/Smoke-Tests der Beispieldateien
            ├── test_models.py      # Model-Tests
            ├── test_auth.py        # Login, Registrierung, Passwort-Reset, Zugriffsschutz
            ├── test_assistant.py   # KI-Assistent: Kontext, Provider, Fehlerfälle
            └── fixtures/       # XGewerbesteuer-1.4-Beispieldateien (siehe docs/testdaten.md)
```

Ausführliche Modul- und Service-Beschreibungen stehen in
[`docs/architektur.md`](docs/architektur.md). Die XSD-Dateien fuer XGewerbesteuer liegen
unter `app/xgewerbesteuer/schemas/` (`gewerbesteuer.xsd` sowie die eingebundenen Basis-,
Adress-, Code- und Datentyp-Schemas).

## Voraussetzungen

- [Docker](https://docs.docker.com/get-docker/) und [Docker Compose](https://docs.docker.com/compose/)

> Für die lokale Entwicklung – auch ohne Docker – siehe [`CONTRIBUTING.md`](CONTRIBUTING.md).

## Installation & Start

1. Repository klonen und in das Projektverzeichnis wechseln.
2. `.env`-Datei aus der Vorlage erstellen und bei Bedarf anpassen:

   ```bash
   cp .env.example .env
   ```

3. Anwendung starten – das fertige Image wird von Docker Hub geladen
   (kein lokaler Build nötig):

   ```bash
   docker compose up -d
   ```

4. Die Anwendung ist anschließend unter [http://localhost:8000/](http://localhost:8000/)
   erreichbar (Port konfigurierbar über `WEB_PORT`).

Weitere nützliche Befehle:

```bash
docker compose pull          # Neueste Image-Version holen
docker compose up -d          # Mit aktualisiertem Image neu starten
docker compose logs -f        # Logs verfolgen
docker compose ps             # Status der Container anzeigen
docker compose down           # Anwendung stoppen
```

Standardmäßig wird das Image-Tag `latest` verwendet. Eine bestimmte Version lässt
sich über `IMAGE_TAG` wählen, z. B. `IMAGE_TAG=1.2.3 docker compose up -d`.
Verfügbare Tags sind bei
[`Docker Hub`](https://hub.docker.com/repository/docker/choosenmeme/xstandardanwendung/tags)
einsehbar. Die SQLite-Datenbank wird bei der produktiven `compose.yaml` lokal
in `./data/db.sqlite3` persistiert und liegt im Container standardmäßig unter
`/data/db.sqlite3` (`SQLITE_PATH`).
In der Entwicklungs-Compose liegt die Datenbank standardmäßig unter
`./app/dev.db.sqlite3`; ohne gesetztes `SQLITE_PATH` nutzt Django im Debug-Modus
`app/dev.db.sqlite3` und sonst `/data/db.sqlite3`.

### Lokale Entwicklung & Mitwirken

Die lokale Entwicklung (mit `compose.dev.yaml` oder ohne Docker per Python), das Ausführen
der Tests und der vollständige Beitragsworkflow (Aufgabe, Branch, Pull Request,
Branch-Schutz) sind in [`CONTRIBUTING.md`](CONTRIBUTING.md) beschrieben.

### Image bauen und veröffentlichen

Build und Betrieb sind getrennt: Das Release-Image wird einmalig gebaut, auf
Docker Hub veröffentlicht und von der Produktions-`compose.yaml` nur noch
geladen. Es enthält weder Tests noch DB-, Doku- oder Build-Artefakte
(siehe `.dockerignore`).

```bash
# Manuell bauen und pushen
docker build -t choosenmeme/xstandardanwendung:latest .
docker push choosenmeme/xstandardanwendung:latest
```

Automatisiert geschieht das über den Workflow
[`.github/workflows/docker-publish.yml`](.github/workflows/docker-publish.yml):
Beim Pushen eines Versions-Tags (`vX.Y.Z`) wird das Image gebaut und nach Docker
Hub gepusht. Dafür müssen die Repository-Secrets `DOCKERHUB_USERNAME` und
`DOCKERHUB_TOKEN` gesetzt sein.

Der Entrypoint (`docker-entrypoint.sh`) führt beim Start automatisch
`migrate --noinput` und `collectstatic --noinput` aus, bevor der
Django-Entwicklungsserver gestartet wird.

## Konfiguration

Die Konfiguration erfolgt vollständig über Umgebungsvariablen (`.env`, siehe
`.env.example`). Viele Einträge in `.env.example` sind kommentierte optionale
Defaults; `SECRET_KEY` muss gesetzt werden. Die echte `.env`-Datei wird
**nicht** versioniert.

| Variable | Beschreibung | Default |
| --- | --- | --- |
| `DEBUG` | Django-Debug-Modus (`1` = an). Nur für Entwicklung! | `0` in `compose.yaml`, `1` in `compose.dev.yaml` |
| `IMAGE_TAG` | Docker-Image-Tag für die produktive `compose.yaml` | `latest` |
| `SQLITE_PATH` | Optionaler Pfad zur SQLite-Datenbank im Container; in `compose.yaml` wird `./data` nach `/data` gemountet, in `compose.dev.yaml` `./app` nach `/app` | `/data/db.sqlite3` in `compose.yaml`, `/app/dev.db.sqlite3` in `compose.dev.yaml`; ohne Variable abhängig von `DEBUG` |
| `SECRET_KEY` | Django Secret Key, muss gesetzt sein; für Entwicklung siehe `.env.example` | – |
| `DJANGO_ALLOWED_HOSTS` | Leerzeichen-getrennte Liste erlaubter Hosts | – in `compose.yaml`, `localhost 127.0.0.1 [::1]` in `compose.dev.yaml` |
| `APP_PATH` | Optionaler URL-Präfix, unter dem die App eingebunden wird (z. B. hinter einem Reverse Proxy) | `""` |
| `WEB_HOST` | Bind-Adresse des Entwicklungsservers | `0.0.0.0` |
| `WEB_PORT` | Port des Entwicklungsservers | `8000` |
| `LANGUAGE_CODE` | Django-Sprachcode | `de-de` |
| `TZ` | Zeitzone des Containers | `Europe/Berlin` |
| `PUID` / `PGID` | UID/GID, unter der der Container-Prozess läuft | `1000` |
| `LOGIN_ENABLED` | Erzwingt Login/Registrierung/Passwort-Reset an (`1`) oder aus (`0`); ohne Wert gilt `DEBUG or EMAIL_SERVER_CONFIGURED` | – (Heuristik) |
| `SESSION_COOKIE_AGE` | Session-Lebensdauer in Sekunden; die Bescheid-Auswertung liegt in der Session, kurze Werte begrenzen die Verweildauer von Steuerdaten in der Datenbank. Abgelaufene Sessions räumt der Entrypoint per `clearsessions` auf | `86400` (24 h) |
| `EMAIL_HOST` | SMTP-Host für Passwort-Reset-Mails; ein Wert ≠ `localhost` schaltet Login automatisch frei | `localhost` |
| `EMAIL_PORT` / `EMAIL_HOST_USER` / `EMAIL_HOST_PASSWORD` / `EMAIL_USE_TLS` | SMTP-Zugangsdaten | `25` / – / – / `0` |
| `DEFAULT_FROM_EMAIL` | Absenderadresse für Passwort-Reset-Mails | `webmaster@localhost` |
| `AI_ASSISTANT_ENABLED` | Aktiviert den optionalen KI-Assistenten (`true`/`false`) | `false` |
| `AI_ASSISTANT_PROVIDER` | KI-Provider; aktuell unterstützt: `ollama` | `disabled` |
| `AI_ASSISTANT_MODEL` / `AI_ASSISTANT_BASE_URL` | Modellname und Basis-URL des Ollama-Servers | – |
| `AI_ASSISTANT_TIMEOUT_SECONDS` | Timeout für Anfragen an den KI-Provider | `10` |
| `CSRF_TRUSTED_ORIGINS` | Leerzeichen-getrennte Liste vollständiger Origins (z. B. `https://steuer.example.de`) für den CSRF-Origin-Check hinter einem HTTPS-Reverse-Proxy; ohne diesen Wert liefern POSTs hinter TLS-Terminierung 403 | – |
| `USE_X_FORWARDED_PROTO` | `1` = Django vertraut dem `X-Forwarded-Proto`-Header des Proxys (`SECURE_PROXY_SSL_HEADER`). Nur setzen, wenn der Proxy den Header selbst setzt/überschreibt | `0` |
| `COOKIES_SECURE` | `1` = Session- und CSRF-Cookie nur über HTTPS ausliefern | `0` |
| `SECURE_HSTS_SECONDS` | HSTS-Laufzeit in Sekunden (`0` = aus); erst aktivieren, wenn die Domain dauerhaft per HTTPS erreichbar ist | `0` |
| `SECURE_HSTS_INCLUDE_SUBDOMAINS` / `SECURE_HSTS_PRELOAD` | HSTS auf Subdomains ausweiten bzw. Preload-Flag setzen (`1` = an) | `0` / `0` |
| `SECURE_SSL_REDIRECT` | `1` = HTTP-Anfragen serverseitig auf HTTPS umleiten (meist erledigt das der Proxy) | `0` |

Für den Betrieb hinter einem HTTPS-Reverse-Proxy sind typischerweise
`CSRF_TRUSTED_ORIGINS`, `USE_X_FORWARDED_PROTO=1` und `COOKIES_SECURE=1` nötig.
`python manage.py check --deploy` listet verbleibende Härtungsempfehlungen auf.

Im DEBUG-Modus (Bare-Metal- und Docker-Dev-Setup) werden E-Mails standardmäßig auf der
Konsole ausgegeben (`EmailBackend` = console) – Registrierungs- und
Passwort-Reset-Links landen also in den Logs (`docker compose -f compose.dev.yaml logs -f`)
statt in einem echten Postfach.

### Lokale Datenbanken

Lokale SQLite-Dateien wie `app/dev.db.sqlite3`, `data/db.sqlite3` und ihre
Journal-Dateien werden nicht versioniert.

## Nutzung

Nach dem Start stehen folgende Routen zur Verfügung (jeweils relativ zu einem optionalen
`APP_PATH`-Präfix):

| Route | Funktion |
| --- | --- |
| `/` | Dashboard: Einstieg, Kurzerklärung, gespeicherte Auswertungen (falls eingeloggt) |
| `/upload/` | Ein oder mehrere XGewerbesteuer-Bescheide hochladen |
| `/demo/` | Demo-Beispielfall mit fiktiven Testdaten laden |
| `/ergebnis/` | Auswertung, Vergleich und Historie der aktuellen Session |
| `/ki-assistent/` | Fragen an den optionalen KI-Assistenten stellen |
| `/hilfe/` | Hilfe- und Glossarseite |
| `/pdf-bericht/`, `/csv-export/`, `/fristdatei.ics` | Export der aktuellen Auswertung |
| `/gespeichert/laden/`, `/gespeichert/loeschen/` | Gespeicherte Auswertung öffnen/löschen (Login erforderlich) |
| `/login/`, `/logout/`, `/registrieren/`, `/passwort-vergessen/` | Benutzerkonto (siehe unten) |
| `/healthz/` | Health-Check-Endpunkt (liefert `{"status": "ok"}`), wird auch vom Docker-`HEALTHCHECK` verwendet |

Der Django-Admin ist bewusst nicht installiert (keine registrierten Modelle, weniger
Angriffsfläche). Login, Registrierung, Passwort-Reset und der KI-Assistent sind pro
Client-IP ratenbegrenzt (HTTP 429 bei zu vielen Anfragen).

Login, Registrierung und Passwort-Reset sind nur erreichbar, wenn `LOGIN_ENABLED` aktiv
ist (siehe [Konfiguration](#konfiguration)); ohne echten Mailserver bleiben sie außerhalb
von `DEBUG` automatisch deaktiviert, da Passwort-Reset-Mails sonst nicht zugestellt werden
könnten. Alle übrigen Funktionen (Upload, Demo, Auswertung, Exporte, KI-Assistent) sind
immer ohne Login nutzbar. Details zu Ablauf und Zugriffsschutz stehen in
[`docs/architektur.md`](docs/architektur.md).

## Status & Roadmap

Das technische Grundgerüst (Django-Projekt, Docker-Setup, KERN-UX-Anbindung,
konfigurierbarer App-Pfad) sowie die zentralen fachlichen Funktionen aus der Story Map des
Design-Thinking-Prozesses sind umgesetzt: Upload und Validierung mehrerer
XGewerbesteuer-Nachrichtenarten, Berechnungserklärung und Plausibilitätsprüfung,
Fälligkeitsübersicht, Vorjahres- und Mehrjahresvergleich, PDF-/CSV-/ICS-Export sowie ein
Demo-Beispielfall. Ergänzend wurden ein optionales Nutzerkonto zum Speichern von
Auswertungen und ein optionaler, lokal konfigurierbarer KI-Assistent hinzugefügt.

Offene Punkte (siehe [`docs/architektur.md`](docs/architektur.md#11-bekannte-technische-schulden--ausblick)):
optionale OIDC-Anbindung (Stufe 3), Registrierung von `SavedBescheidUpload` im
Django-Admin.

Der laufende Fortschritt wird im
[GitHub Project](https://github.com/users/ChoosenMEME/projects/1) getrackt. Die
ursprüngliche Story Map aus dem Design-Thinking-Prozess ist in
[`docs/design-thinking.md`](docs/design-thinking.md) dokumentiert.

## Lizenz

Dieses Projekt steht unter der **MIT-Lizenz** (siehe [`LICENSE`](LICENSE)). Die Lizenzen der
mitgelieferten bzw. genutzten Drittanbieter-Komponenten (Python, Django, KERN UX,
XGewerbesteuer u. a.) sind in [`THIRD-PARTY-NOTICES.md`](THIRD-PARTY-NOTICES.md) dokumentiert.

## Mitwirkende & Einsatz von KI-Tools

> **Hinweis:** Die folgenden Tabellen sind aus der Git-Historie abgeleitet (Autor:innen,
> Commit-Themen). Bitte vor der Abgabe prüfen und ergänzen – insbesondere echte Namen,
> Rollen in eigenen Worten und der tatsächliche Einsatz von KI-Tools je Person/Aufgabe
> (siehe Prüfungshinweise, Dimension „Transparenz").

### Mitwirkende

| Person (GitHub) | Schwerpunkt laut Commit-Historie |
| --- | --- |
| `ChoosenMEME` / `ChoosenMeme` | Projekt-Setup (Django/Docker), CI/CD (GitHub Actions, Docker-Hub-Publish), Konfiguration (`APP_PATH`, Healthcheck), KERN-UX-Einbindung, laufende Pflege von README/AGENTS.md |
| Alexander Bahlmann | Kernfunktionen: Upload/Extraktion, Nachrichtentyp-Unterscheidung, Vorjahres- und Mehrjahresvergleich, Plausibilitätsprüfung, PDF-/CSV-/ICS-Export, KI-Assistent, responsives KERN-UX-Layout |
| Sören Schulzke | Demo-Beispielfall, Datenschutz-/Anonymisierungsmodus, supportfreundliche Fehler-IDs, Healthcheck-/Static-URL-Stabilisierung, Validierungsdetails |

### Einsatz von KI-Tools

| Tool | Zweck | Status |
| --- | --- | --- |
| Claude Code (Anthropic) | Unterstützung bei Implementierung, Refactoring und Dokumentationspflege | im Projekt genutzt (u. a. `.claude` bewusst in `.gitignore`) |
| ChatGPT / Codex (OpenAI) | Unterstützung bei Implementierung | Hinweise im Projekt vorhanden (`openai.chatgpt`-Erweiterung in `.vscode/extensions.json`, Agent-Namenskonvention „codex" in `AGENTS.md`) – **bitte konkretisieren, wofür genau** |

KI-Tools wurden gemäß Aufgabenstellung ausschließlich unterstützend eingesetzt; die
fachliche Konzeption (Design-Thinking-Prozess, siehe [`docs/design-thinking.md`](docs/design-thinking.md))
sowie die Abnahme aller Beiträge liegen bei den Gruppenmitgliedern.
