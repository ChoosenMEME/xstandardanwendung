# GewSt-Bescheidassistent

Prüfungsleistung im Modul **Digitale Transformation** (6. Semester DSWVI, SoSe 2026).

> 📎 **Design Thinking Prozess:** Die Konzeption dieser Anwendung basiert auf einem
> vorgeschalteten Design-Thinking-Prozess (Empathize, Define, Ideate, Prototype, Test).
> Die vollständige Dokumentation findet sich unter
> [`docs/design-thinking.md`](docs/design-thinking.md).

## Inhaltsverzeichnis

- [Über das Projekt](#über-das-projekt)
- [Problemstellung & Zielsetzung](#problemstellung--zielsetzung)
- [Lösungskonzept](#lösungskonzept)
- [Technologie-Stack](#technologie-stack)
- [Projektstruktur](#projektstruktur)
- [Voraussetzungen](#voraussetzungen)
- [Installation & Start](#installation--start)
- [Konfiguration](#konfiguration)
- [Nutzung](#nutzung)
- [XGewerbesteuer-Datenstandard](#xgewerbesteuer-datenstandard)
- [Tests](#tests)
- [Status & Roadmap](#status--roadmap)
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

## Problemstellung & Zielsetzung

Die Persona **Sabine Keller**, Inhaberin eines kleinen Cafés, steht stellvertretend für
viele kleine Unternehmen: Sie erhält einen digitalen Gewerbesteuerbescheid, kann den
fälligen Betrag, die Fälligkeit, die Berechnung und die Veränderung zum Vorjahr aber nicht
ohne Aufwand nachvollziehen.

**Design Challenge:**

> Wie können wir kleinen Unternehmen ermöglichen, digitale Gewerbesteuerbescheide
> schneller zu verstehen, damit sie fällige Zahlungen sicher planen, Änderungen
> nachvollziehen und finanzielle Risiken besser einschätzen können?

Die zugehörigen OKRs und der vollständige Problemraum sind in
[`docs/design-thinking.md`](docs/design-thinking.md) beschrieben.

## Lösungskonzept

Auf Basis des Design-Thinking-Prozesses ist folgendes Funktionskonzept vorgesehen:

| Bereich | Funktion | Nutzen |
| --- | --- | --- |
| Startseite | Kurze Erklärung der Anwendung | Nutzer:innen verstehen sofort, wofür die Anwendung gedacht ist |
| Upload | XGewerbesteuer-Bescheid (XML) hochladen | Digitale Bescheiddaten werden automatisch eingelesen |
| Zusammenfassung | Zahlbetrag, Jahr, Gemeinde, Fälligkeit | Wichtigste Informationen erscheinen auf einen Blick |
| Fristenübersicht | Zahlungen chronologisch darstellen | Zahlungsfristen werden nicht übersehen |
| Berechnungserklärung | Messbetrag, Hebesatz und Steuerbetrag erklären | Fachbegriffe werden verständlicher |
| Änderungsvergleich | Vergleich mit Vorjahresbescheid | Veränderungen werden transparent |
| Hinweisbogen | Auffälligkeiten verständlich erklären | Nutzer:innen erhalten Orientierung |
| Export | Bericht als PDF/CSV | Ergebnisse können gespeichert oder weitergegeben werden |

## Technologie-Stack

- **[Django](https://www.djangoproject.com/)** als Webframework (Python)
- **SQLite** als Datenbank
- **Docker** / **Docker Compose** für Build, Betrieb und lokale Entwicklung
- **[KERN UX](https://www.kern-ux.de/)** als UI-/Designsystem für Verwaltungsanwendungen
  (eingebunden über `base.html`)
- **[XGewerbesteuer 1.4](https://www.xrepository.de/details/urn:xoev-de:xunternehmen:standard:gewerbesteuer_1.4#version)**
  als zu verarbeitender XÖV-Datenstandard

## Projektstruktur

```text
.
├── compose.yaml                # Docker-Compose-Definition des web-Service
├── Dockerfile                  # Image-Definition (Python/Django)
├── docker-entrypoint.sh        # Migrationen, collectstatic, Start des Dev-Servers
├── requirements.txt            # Python-Abhängigkeiten
├── .env.example                # Beispiel-Konfiguration (siehe Konfiguration)
├── docs/
│   └── design-thinking.md      # Dokumentation des Design-Thinking-Prozesses
├── README.md
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
        └── tests.py
```

## Voraussetzungen

- [Docker](https://docs.docker.com/get-docker/) und [Docker Compose](https://docs.docker.com/compose/)

## Installation & Start

1. Repository klonen und in das Projektverzeichnis wechseln.
2. `.env`-Datei aus der Vorlage erstellen und bei Bedarf anpassen:

   ```bash
   cp .env.example .env
   ```

3. Anwendung bauen und starten:

   ```bash
   docker compose up -d --build
   ```

4. Die Anwendung ist anschließend unter [http://localhost:8000/](http://localhost:8000/)
   erreichbar (Port konfigurierbar über `WEB_PORT`).

Weitere nützliche Befehle:

```bash
docker compose logs -f      # Logs verfolgen
docker compose ps            # Status der Container anzeigen
docker compose down          # Anwendung stoppen
```

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
| `LANGUAGE_CODE` | Django-Sprachcode | `en-us` |
| `TZ` | Zeitzone des Containers | `UTC` |
| `PUID` / `PGID` | UID/GID, unter der der Container-Prozess läuft | `1000` |

## Nutzung

Nach dem Start stehen folgende Routen zur Verfügung (jeweils relativ zu einem optionalen
`APP_PATH`-Präfix):

- `/` – Startseite der `xgewerbesteuer`-App
- `/healthz/` – Health-Check-Endpunkt (liefert `{"status": "ok"}`), wird auch vom
  Docker-`HEALTHCHECK` verwendet

Die Bescheid-Upload- und Auswertungsfunktionen aus dem [Lösungskonzept](#lösungskonzept)
befinden sich in Entwicklung, siehe [Status & Roadmap](#status--roadmap).

## XGewerbesteuer-Datenstandard

Die Anwendung verarbeitet Datensätze nach dem
[XGewerbesteuer-Standard (Version 1.4)](https://www.xrepository.de/details/urn:xoev-de:xunternehmen:standard:gewerbesteuer_1.4#version),
einem XÖV-konformen Standard für den elektronischen Austausch von
Gewerbesteuer(mess)bescheiden zwischen Finanzverwaltung, Kommunen und Unternehmen. Im
XRepository sind dazu u. a. die XML-Schemas (XSD), zugehörige Codelisten und die
fachliche Spezifikation des Standards veröffentlicht.

Im Rahmen dieser Anwendung dient der Standard als verbindliches Datenformat für den
Bescheid-Upload (siehe [Lösungskonzept](#lösungskonzept)): Die enthaltenen Felder zu
Steuerjahr, Gemeinde, Messbetrag, Hebesatz, Steuerbetrag und Fälligkeiten werden
ausgelesen und für die nutzerfreundliche Aufbereitung verwendet.

## Tests

Tests liegen in `app/xgewerbesteuer/tests.py` und werden über die
Django-Testumgebung ausgeführt:

```bash
docker compose exec web python manage.py test
```

Zusätzlich kann die Projektkonfiguration geprüft werden:

```bash
docker compose exec web python manage.py check
```

## Status & Roadmap

Der aktuelle Stand des Repositories umfasst das technische Grundgerüst (Django-Projekt,
Docker-Setup, KERN-UX-Anbindung, Health-Check, konfigurierbarer App-Pfad). Die fachlichen
Funktionen werden entlang der Story Map aus dem Design-Thinking-Prozess umgesetzt.

Der laufende Fortschritt wird im
[GitHub Project](https://github.com/users/ChoosenMEME/projects/1) getrackt.

| Schritt | Nutzerziel | Funktion im System |
| --- | --- | --- | --- |
| 1 | Bescheid erhalten | Einstieg mit kurzer Erklärung und Nutzungshinweis |
| 2 | Bescheid hochladen | Upload des digitalen XGewerbesteuer-Bescheids |
| 3 | Bescheid verstehen | Automatische Zusammenfassung zentraler Informationen |
| 4 | Fristen erkennen | Übersicht über Zahlungen und Fälligkeiten |
| 5 | Berechnung nachvollziehen | Erklärung von Messbetrag, Hebesatz und Gewerbesteuer |
| 6 | Änderungen vergleichen | Vergleich mit Vorjahresbescheid |
| 7 | Ergebnis sichern | Ausgabe eines kompakten Analyseberichts |
