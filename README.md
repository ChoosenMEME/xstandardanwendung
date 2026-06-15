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

Der **GewSt-Bescheidassistent** ist eine Django-Webanwendung, die einen digitalen
Gewerbesteuerbescheid einliest und die wichtigsten Informationen – Zahlbetrag,
Fälligkeiten, Berechnungsgrundlagen und Veränderungen zum Vorjahr – verständlich
aufbereitet.

## Technologie-Stack

- **[Django](https://www.djangoproject.com/)** als Webframework (Python)
- **SQLite** als Datenbank
- **Docker** / **Docker Compose** für Build, Betrieb und lokale Entwicklung
- **[KERN UX](https://www.kern-ux.de/)** als UI-/Designsystem für Verwaltungsanwendungen
  (eingebunden über `base.html`)
- **[XGewerbesteuer 1.4](https://www.xrepository.de/details/urn:xoev-de:xunternehmen:standard:gewerbesteuer_1.4#version)**
  als zu verarbeitender XÖV-Datenstandard (Details: [`docs/datenstandard.md`](docs/datenstandard.md))

## Projektstruktur

```text
.
├── compose.yaml                # Produktion: zieht das fertige Image von Docker Hub
├── compose.dev.yaml            # Entwicklung: baut lokal und mountet ./app
├── Dockerfile                  # Image-Definition (Python/Django)
├── docker-entrypoint.sh        # Migrationen, collectstatic, Start des Dev-Servers
├── requirements.txt            # Python-Abhängigkeiten
├── .env.example                # Beispiel-Konfiguration (siehe Konfiguration)
├── docs/
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
    ├── db.sqlite3              # lokale SQLite-Datenbank
    ├── config/
    │   ├── settings.py         # Django-Settings (liest Umgebungsvariablen)
    │   ├── urls.py             # Root-URL-Konfiguration (healthz, App-Routen)
    │   ├── url_paths.py        # Hilfsfunktion für konfigurierbaren App-Pfad
    │   ├── asgi.py / wsgi.py
    │   └── __init__.py
    ├── static/                 # eigene statische Dateien
    ├── staticfiles/            # Ergebnis von collectstatic (generiert)
    ├── templates/
    │   └── base.html           # Basistemplate inkl. KERN-UX-Einbindung
    └── xgewerbesteuer/         # Fachliche App
        ├── models.py
        ├── views.py
        ├── urls.py
        ├── admin.py
        ├── apps.py
        ├── migrations/
        ├── templates/
        └── tests/
            ├── test_views.py   # Routing- und View-Tests
            ├── test_imports.py # Struktur-Tests fuer XGewerbesteuer-Beispieldateien
            └── fixtures/       # XGewerbesteuer-1.4-Beispieldateien (siehe docs/testdaten.md)
```

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

Standardmäßig wird das Tag `latest` verwendet. Eine bestimmte Version lässt sich
über `IMAGE_TAG` wählen, z. B. `IMAGE_TAG=1.2.3 docker compose up -d`. Die
SQLite-Datenbank wird fest in `./app/db.sqlite3` persistiert.

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
`.env.example`). Die echte `.env`-Datei wird **nicht** versioniert.

| Variable | Beschreibung | Default |
| --- | --- | --- |
| `DEBUG` | Django-Debug-Modus (`1` = an). Nur für Entwicklung! | `0` |
| `SECRET_KEY` | Django Secret Key, muss in produktiven Umgebungen gesetzt werden | `dev-secret-key` |
| `DJANGO_ALLOWED_HOSTS` | Leerzeichen-getrennte Liste erlaubter Hosts | – |
| `APP_PATH` | Optionaler URL-Präfix, unter dem die App eingebunden wird (z. B. hinter einem Reverse Proxy) | `""` |
| `WEB_HOST` | Bind-Adresse des Entwicklungsservers | `0.0.0.0` |
| `WEB_PORT` | Port des Entwicklungsservers | `8000` |
| `LANGUAGE_CODE` | Django-Sprachcode | `de-de` |
| `TZ` | Zeitzone des Containers | `UTC` |
| `PUID` / `PGID` | UID/GID, unter der der Container-Prozess läuft | `1000` |

## Nutzung

Nach dem Start stehen folgende Routen zur Verfügung (jeweils relativ zu einem optionalen
`APP_PATH`-Präfix):

- `/` – Startseite der `xgewerbesteuer`-App
- `/healthz/` – Health-Check-Endpunkt (liefert `{"status": "ok"}`), wird auch vom
  Docker-`HEALTHCHECK` verwendet

Die Bescheid-Upload- und Auswertungsfunktionen befinden sich in Entwicklung, siehe
[Status & Roadmap](#status--roadmap).

## Status & Roadmap

Der aktuelle Stand des Repositories umfasst das technische Grundgerüst (Django-Projekt,
Docker-Setup, KERN-UX-Anbindung, Health-Check, konfigurierbarer App-Pfad). Die fachlichen
Funktionen werden entlang der Story Map aus dem Design-Thinking-Prozess umgesetzt.

Der laufende Fortschritt wird im
[GitHub Project](https://github.com/users/ChoosenMEME/projects/1) getrackt. Die geplanten
Funktionsschritte (Story Map) sind in [`docs/design-thinking.md`](docs/design-thinking.md)
dokumentiert.

## Lizenz

Dieses Projekt steht unter der **MIT-Lizenz** (siehe [`LICENSE`](LICENSE)). Die Lizenzen der
mitgelieferten bzw. genutzten Drittanbieter-Komponenten (Python, Django, KERN UX,
XGewerbesteuer u. a.) sind in [`THIRD-PARTY-NOTICES.md`](THIRD-PARTY-NOTICES.md) dokumentiert.

## Mitwirkende & Einsatz von KI-Tools
