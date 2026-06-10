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
├── Dockerfile
├── docker-entrypoint.sh
├── requirements.txt
├── README.md
├── AGENTS.md
└── app/
    ├── manage.py
    ├── config/
    │   ├── settings.py
    │   ├── urls.py
    │   ├── asgi.py
    │   └── wsgi.py
    ├── static/
    ├── staticfiles/
    ├── templates/
    │   └── base.html
    └── xgewerbesteuer/
        ├── models.py
        ├── views.py
        ├── urls.py
        ├── tests.py
        ├── admin.py
        ├── migrations/
        └── templates/
```

Falls sich die Struktur aendert, soll sich der Agent an der tatsaechlich vorhandenen Struktur im Repository orientieren.

## Docker Compose

Das Projekt wird primaer ueber Docker Compose gestartet. Die Compose-Datei heisst `compose.yaml`.

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

Nach Model-Aenderungen ausfuehren:

```bash
docker compose exec web python manage.py makemigrations
docker compose exec web python manage.py migrate
docker compose exec web python manage.py check
```

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

Das Projekt verwendet SQLite. Die Entwicklungsdatenbank liegt standardmaessig unter `app/db.sqlite3`.

* Bestehende Migrationen nicht nachtraeglich veraendern, wenn sie bereits verwendet wurden.
* Neue Schemaaenderungen immer ueber neue Migrationen abbilden.
* Keine produktiven Daten loeschen.
* Keine Testdaten fest in produktiven Migrationscode schreiben.
* Datenmigrationen muessen nachvollziehbar und reversibel sein, soweit sinnvoll.
* Lokale SQLite-Datenbanken nicht loeschen, ausser der Nutzer fordert dies ausdruecklich.

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
DEBUG=1
SECRET_KEY=change-me
DJANGO_ALLOWED_HOSTS=localhost 127.0.0.1
WEB_HOST=0.0.0.0
WEB_PORT=8000
LANGUAGE_CODE=de-de
TZ=Europe/Berlin
PUID=1000
PGID=1000
```

Die echte `.env` darf nicht committet werden.

## Tests und Qualitaetspruefung

Zu Codeaenderungen sollen passende Tests erstellt oder angepasst werden.

* Neue Models, Views, Forms, Services, Parser, Importfunktionen und fachliche Berechnungen brauchen Tests.
* Bugfixes sollen einen Regressionstest enthalten, der den behobenen Fehler abdeckt.
* Bei XGewerbesteuer-Importen sollen gueltige und ungueltige XML-Beispiele getestet werden.
* Bei fachlichen Berechnungen sollen typische Faelle, Grenzfaelle und Rundungsverhalten getestet werden.
* Bei Views sollen Statuscode, verwendetes Template und wichtige Kontextdaten geprueft werden.
* Wenn fuer eine Aenderung kein Test sinnvoll ist, soll der Grund kurz dokumentiert werden.

Tests liegen aktuell in `app/xgewerbesteuer/tests.py`. Falls die Tests umfangreicher werden, kann innerhalb der App ein Testpaket angelegt werden:

```text
app/xgewerbesteuer/tests/
├── __init__.py
├── test_models.py
├── test_views.py
├── test_services.py
└── test_imports.py
```

Vor Abschluss einer Aenderung moeglichst ausfuehren:

```bash
docker compose exec web python manage.py check
docker compose exec web python manage.py test
```

Falls der Container nicht laeuft, kann lokal im App-Verzeichnis geprueft werden, sofern Abhaengigkeiten installiert sind:

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
* Kleine, fokussierte Commits oder Aenderungsbloecke bevorzugen.
* Bestehende Nutzerarbeit nicht zuruecksetzen.
* Keine generierten Dateien manuell anfassen, wenn die Quelle bearbeitet werden kann.
* Zu neuen oder geaenderten Funktionen passende Tests erstellen oder bestehende Tests aktualisieren.
* Sinnvolle Kommentare oder Docstrings ergaenzen, wenn Logik, Fachregeln oder Sicherheitsentscheidungen sonst schwer nachvollziehbar sind.
* Nach Aenderungen die passenden Checks ausfuehren oder klar dokumentieren, warum sie nicht ausgefuehrt wurden.
* Bei fachlichen Steuerfragen vorsichtig formulieren und keine verbindliche Beratung geben.
