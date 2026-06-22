# Mitwirken am GewSt-Bescheidassistent

Diese Anleitung führt Schritt für Schritt durch einen Beitrag zum Projekt – vom lokalen
Start bis zum fertigen Pull Request. Tiefe Vorkenntnisse mit Git, Docker oder Django sind
nicht erforderlich; am besten werden die Abschnitte der Reihe nach von oben nach unten
durchgegangen.

> **Wichtigste Regel:** Es kann **nicht direkt** auf `main` committet werden. Jede Änderung
> läuft über einen eigenen Branch und einen **Pull Request (PR)**. Das ist bewusst so
> eingestellt – siehe [Branch-Schutz](#7-was-passiert-im-hintergrund-branch-schutz).

## Inhaltsverzeichnis

- [0. Voraussetzungen](#0-voraussetzungen)
- [VS Code als empfohlene IDE](#vs-code-als-empfohlene-ide)
- [1. Projekt holen (klonen)](#1-projekt-holen-klonen)
- [2. Entwicklungsumgebung starten](#2-entwicklungsumgebung-starten)
  - [Variante A: Mit Docker (empfohlen)](#variante-a-mit-docker-empfohlen)
  - [Variante B: Ohne Docker (Bare-Metal)](#variante-b-ohne-docker-bare-metal)
- [3. Aufgabe wählen und Branch anlegen](#3-aufgabe-wählen-und-branch-anlegen)
- [4. Änderung machen und prüfen](#4-änderung-machen-und-prüfen)
- [5. Änderung committen und hochladen (push)](#5-änderung-committen-und-hochladen-push)
- [6. Pull Request erstellen](#6-pull-request-erstellen)
- [7. Was passiert im Hintergrund? (Branch-Schutz)](#7-was-passiert-im-hintergrund-branch-schutz)
- [8. Wenn die Prüfungen rot sind](#8-wenn-die-prüfungen-rot-sind)
- [9. Mergen und aufräumen](#9-mergen-und-aufräumen)
- [Fehler gefunden? Issue erstellen](#fehler-gefunden-issue-erstellen)
- [Spickzettel](#spickzettel)
- [Häufige Fehler & Lösungen](#häufige-fehler--lösungen)

---

## 0. Voraussetzungen

Benötigt werden in jedem Fall:

- **[Git](https://git-scm.com/downloads)** – zum Verwalten der Änderungen.
- Ein **[GitHub](https://github.com/)-Konto** – ohne Konto lässt sich kein Pull Request erstellen.

Falls Git noch nicht installiert ist, zeigt VS Code das meist direkt an: links auf das
**Git-Symbol** („Source Control") klicken. Wenn dort ein Hinweis erscheint, dass Git fehlt,
den angebotenen Link **Install Git** öffnen, Git installieren und VS Code danach neu starten.

Dazu **eine** der beiden Entwicklungsvarianten (Details in [Schritt 2](#2-entwicklungsumgebung-starten)):

- **Docker** (empfohlen): [Docker](https://docs.docker.com/get-docker/) inkl. Docker
  Compose. Lokales Python ist dann nicht erforderlich.
- **Bare-Metal** (ohne Docker): **Python 3.12 oder neuer**.

Kurzer Funktionstest im Terminal (PowerShell; unter macOS / Linux: Bash):

```powershell
git --version
docker --version        # nur für Variante A
python --version        # nur für Variante B (macOS / Linux: ggf. python3 --version)
```

---

## VS Code als empfohlene IDE

Als Editor wird **[Visual Studio Code](https://code.visualstudio.com/)** (kurz „VS Code")
empfohlen. Er bringt Git mit grafischer Oberfläche mit, sodass sich die Git-Schritte dieser
Anleitung anklicken statt im Terminal eingeben lassen. Die konkreten Bedienhinweise stehen
direkt bei den betroffenen Schritten ([Klonen](#1-projekt-holen-klonen),
[Branch](#3-aufgabe-wählen-und-branch-anlegen),
[Commit & Push](#5-änderung-committen-und-hochladen-push)). Dieser Abschnitt beschreibt nur
die einmalige Einrichtung und kann übersprungen werden, wenn das Terminal bevorzugt wird.

### Installieren und einrichten

1. **VS Code herunterladen** von <https://code.visualstudio.com/> und installieren.
2. **Empfohlene Erweiterungen installieren:** Das Projekt liefert eine Liste empfohlener
   Erweiterungen in [`.vscode/extensions.json`](.vscode/extensions.json) mit. Beim ersten
   Öffnen des Projektordners blendet VS Code unten rechts die Frage *„Do you want to install
   the recommended extensions?"* ein – dort auf **Install** klicken. Alternativ links auf das
   Quadrat-Symbol („Extensions") klicken, `@recommended` in das Suchfeld eingeben und die
   Erweiterungen installieren. Enthalten sind u. a.:
   - **Python**, **Pylance**, **Python Debugger** (von Microsoft) – für die
     Bare-Metal-Entwicklung, Tests, Code-Vervollständigung und venv-Auswahl.
   - **Black Formatter** (von Microsoft) – formatiert Python-Code beim Speichern.
   - **Django** – Syntax-Hervorhebung für Django-Templates (`django-html`).
   - **EditorConfig**, **YAML** und **markdownlint** – für konsistente Formatierung von
     Code-, YAML- und Markdown-Dateien.
   - **Container** / **Docker** – optional, für die Arbeit mit der Docker-Variante.
3. **Bei GitHub anmelden** (einmalig): unten links auf das Personen-Symbol („Accounts")
   klicken → **Sign in with GitHub** wählen → im Browser bestätigen. Danach kann VS Code
   ohne erneute Anmeldung zu GitHub pushen.

> **Automatische Formatierung:** Über die EditorConfig-Erweiterung und die mitgelieferten
> Workspace-Einstellungen ([`.editorconfig`](.editorconfig),
> [`.vscode/settings.json`](.vscode/settings.json)) stellt sich VS Code von selbst auf die
> Projektkonventionen ein: 4 Leerzeichen Einrückung in Python (2 in YAML/JSON/Templates),
> LF-Zeilenenden, eine abschließende Leerzeile und das Entfernen überflüssiger Leerzeichen am
> Zeilenende. Formatierung beim Speichern und Black als Python-Formatter sind bereits
> voreingestellt – so entsprechen Beiträge ohne weiteres Zutun dem Projektstil. Diese
> Einstellungen gelten nur innerhalb dieses Projektordners.

---

## 1. Projekt holen (klonen)

„Klonen" lädt eine Kopie des Projekts auf den lokalen Rechner:

```powershell
git clone https://github.com/ChoosenMEME/xstandardanwendung.git
cd xstandardanwendung
```

Alle weiteren Befehle werden in diesem Ordner ausgeführt.

> **In VS Code:** **Strg+Umschalt+P** drücken, `Git: Clone` auswählen, die URL
> `https://github.com/ChoosenMEME/xstandardanwendung.git` einfügen, einen Zielordner wählen
> und das Projekt öffnen. Ein bereits geklontes Projekt lässt sich über
> **File → Open Folder…** öffnen.

---

## 2. Entwicklungsumgebung starten

Es genügt **eine** der beiden Varianten – danach bei der gewählten bleiben:

| | Docker (Variante A) | Bare-Metal (Variante B) |
| --- | --- | --- |
| **Einrichtung** | `.env` kopieren, ein Befehl | Python-venv, pip, Umgebungsvariablen |
| **Voraussetzung** | Docker + Compose | Python 3.12+ |
| **Vorteil** | Alles vorkonfiguriert, identisch zur CI | Kein Docker nötig, direkter Zugriff |
| **Empfohlen für** | Die meisten Beitragenden | Wenn Docker nicht installiert werden kann/soll |

### Variante A: Mit Docker (empfohlen)

Zuerst die lokale Konfiguration aus der Vorlage anlegen:

```powershell
cp .env.example .env
```

Anschließend die Entwicklungs-Variante starten. Sie baut das Image lokal und spiegelt den
Quellcode live in den Container – Codeänderungen wirken sofort:

```powershell
docker compose -f compose.dev.yaml up -d --build
```

Die Variable `IMAGE_TAG` betrifft nur die produktive `compose.yaml`. Die
Entwicklungs-Compose baut lokal und taggt das Image fest als
`choosenmeme/xstandardanwendung:dev`. `SQLITE_PATH` ist optional und zeigt
in der Entwicklungs-Compose standardmäßig auf `/app/dev.db.sqlite3`; durch den
Mount `./app:/app` landet die Datei lokal als `./app/dev.db.sqlite3`.
Ohne gesetztes `SQLITE_PATH` nutzt Django im Debug-Modus ebenfalls
`app/dev.db.sqlite3`; im Nicht-Debug-Modus ist der Fallback `/data/db.sqlite3`.

Im Browser **[http://localhost:8000/](http://localhost:8000/)** öffnen. Erscheint die
Startseite, läuft die Anwendung.

Nützliche Befehle während der Arbeit:

```powershell
docker compose -f compose.dev.yaml logs -f   # Logs live ansehen (Strg+C beendet die Ansicht)
docker compose -f compose.dev.yaml ps        # Läuft der Container?
docker compose -f compose.dev.yaml down      # Umgebung stoppen
```

> Bitte `docker compose down -v` nicht verwenden und keine lokalen SQLite-Datenbankdateien
> wie `app/dev.db.sqlite3` oder `data/db.sqlite3` löschen, sonst können lokale Daten
> verloren gehen. Siehe auch die verbotenen Befehle in
> [`AGENTS.md`](AGENTS.md#verbotene-oder-gefaehrliche-befehle).

### Variante B: Ohne Docker (Bare-Metal)

Hier wird die Anwendung direkt mit Python betrieben. Erforderlich ist **Python 3.12 oder
neuer**.

**1. Virtuelle Umgebung im Projekt anlegen und aktivieren.** Alle folgenden Befehle laufen
im Projekt-Wurzelordner `xstandardanwendung`. Die virtuelle Umgebung liegt dort als
`.venv/`, hält die Projekt-Pakete vom System getrennt und wird durch `.gitignore` nicht
committet:

```powershell
python -m venv .venv
```

Aktivieren – je nach Betriebssystem:

```powershell
# Windows (PowerShell)
.\.venv\Scripts\Activate.ps1
```

```bash
# macOS / Linux
source .venv/bin/activate
```

Bei erfolgreicher Aktivierung steht `(.venv)` am Anfang der Eingabezeile.

**2. Abhängigkeiten in die Projekt-venv installieren** (die `requirements.txt` liegt im
Projekt-Wurzelordner):

```powershell
pip install -r requirements.txt
```

**3. Konfiguration setzen.** Django liest die Einstellungen aus *Umgebungsvariablen*. Für
die lokale Entwicklung werden ein Debug-Modus und ein lokaler Secret Key gesetzt – dann
lässt der Entwicklungsserver `localhost` automatisch zu:

```powershell
# Windows (PowerShell)
$env:DEBUG = "1"
$env:SECRET_KEY = "dev-secret-key"
$env:SQLITE_PATH = "dev.db.sqlite3"
```

```bash
# macOS / Linux
export DEBUG=1
export SECRET_KEY=dev-secret-key
export SQLITE_PATH=dev.db.sqlite3
```

> Diese Variablen gelten nur für das **aktuelle Terminalfenster**. In einem neuen Fenster
> müssen sie einfach erneut gesetzt werden. (Die `.env`-Datei wird im Bare-Metal-Betrieb
> **nicht** automatisch geladen – sie ist nur für Docker gedacht.)

**4. Datenbank vorbereiten und Server starten** (alle `manage.py`-Befehle laufen im
Unterordner `app/`):

```powershell
cd app
python manage.py migrate
python manage.py runserver
```

Im Browser **[http://localhost:8000/](http://localhost:8000/)** öffnen. Mit `Strg+C` wird
der Server gestoppt. Für einen späteren Neustart genügt es, die venv zu aktivieren,
`DEBUG=1`, `SECRET_KEY=dev-secret-key` sowie `SQLITE_PATH=dev.db.sqlite3` zu setzen und
`python manage.py runserver` auszuführen.

---

## 3. Aufgabe wählen und Branch anlegen

Alle offenen Aufgaben sind im
[GitHub Project](https://github.com/users/ChoosenMEME/projects/1) gesammelt. Bevor es mit dem Code losgeht:

1. Im GitHub Project in der Spalte **Backlog** eine offene Aufgabe aussuchen.
2. Die Aufgabe **sich selbst zuweisen** (Feld „Assignees" → eigener Account). So ist für
   alle sichtbar, dass sie gerade bearbeitet wird, und Doppelarbeit lässt sich vermeiden.
3. Die Aufgabe auf dem Board nach **In Progress** ziehen.

> Das Board hat die Spalten **Backlog**, **In Progress**, **In Review** und **Done**. Die
> Aufgabe wandert mit dem Fortschritt mit: beim Start nach *In Progress*, beim Öffnen des
> Pull Requests nach *In Review* ([Schritt 6](#6-pull-request-erstellen)) und nach dem
> Merge nach *Done* ([Schritt 9](#9-mergen-und-aufräumen)).

Anschließend einen eigenen Branch anlegen. Ein Branch ist eine eigene „Arbeitsspur", damit
`main` sauber bleibt; direkt auf `main` kann nicht gearbeitet werden – das verhindert der
Branch-Schutz.

```powershell
git checkout main
git pull
git checkout -b feature/kurze-beschreibung
```

Empfohlen wird ein sprechender Name, z. B.:

- `feature/bescheid-upload` – neue Funktion
- `fix/fehlende-faelligkeit` – Fehlerbehebung
- `docs/readme-tippfehler` – reine Dokumentation

> **In VS Code:** unten links in der Statusleiste auf den aktuellen Branch-Namen klicken →
> **Create new branch…** → Namen eingeben (z. B. `feature/...`).

---

## 4. Änderung machen und prüfen

Die Dateien im Editor bearbeiten. Dabei gelten die Konventionen in [`AGENTS.md`](AGENTS.md)
(Django-Struktur, Kommentare, Sicherheit, Tests).

**Vor dem Hochladen sollten dieselben Prüfungen wie in der CI lokal grün sein** – andernfalls
schlagen sie später im Pull Request fehl.

**Docker:**

```powershell
docker compose -f compose.dev.yaml exec web python manage.py check
docker compose -f compose.dev.yaml exec web python manage.py test
```

**Bare-Metal** (im Ordner `app/` mit aktiver venv):

```powershell
python manage.py check
python manage.py test
```

Bei Codeänderungen sollten passende **Tests** ergänzt oder aktualisiert werden (siehe
Abschnitt „Tests und Qualitaetspruefung" in [`AGENTS.md`](AGENTS.md)). Eine Übersicht der
XGewerbesteuer-Beispieldateien (Testdaten) steht in [`docs/testdaten.md`](docs/testdaten.md).
Nach einer **Model**-Änderung wird zusätzlich die Migration erzeugt (`makemigrations`, dann
`migrate`).

---

## 5. Änderung committen und hochladen (push)

Ein Commit ist ein gespeicherter Zwischenstand mit kurzer Beschreibung:

```powershell
git add .
git status                       # zeigt, was gespeichert wird – kurz kontrollieren
git commit -m "Kurz und klar beschreiben, was die Änderung tut"
```

> Bitte nicht committen: die echte `.env`, Passwörter, Tokens, Secrets,
> Datenbankdateien oder Agent-Testdateien. Im Zweifel vorab `git status` prüfen.

Den Branch zu GitHub hochladen:

```powershell
git push -u origin feature/kurze-beschreibung
```

Beim ersten Push fragt Git ggf. nach dem GitHub-Login.

> **In VS Code:** im Bereich **Source Control** (**Strg+Umschalt+G**) geänderte Dateien mit
> dem **+** stagen, oben eine Commit-Nachricht eingeben und auf **Commit** klicken;
> anschließend mit **Sync Changes** pushen. Beim ersten Mal den Branch auf GitHub
> veröffentlichen.

---

## 6. Pull Request erstellen

Ein **Pull Request (PR)** ist die Anfrage, den eigenen Branch in `main` zu übernehmen.

1. Das Repository öffnen: <https://github.com/ChoosenMEME/xstandardanwendung>
2. GitHub zeigt nach dem Push meist einen Hinweis **„Compare & pull request"** – darauf
   klicken. (Alternativ: Tab **Pull requests** → **New pull request** → den eigenen Branch wählen.)
3. Sicherstellen, dass das Ziel **`base: main`** und die Quelle der eigene Branch ist.
4. Einen aussagekräftigen **Titel** und eine kurze **Beschreibung** eingeben: *Was* wurde
   geändert und *warum*?
5. Auf **Create pull request** klicken.

Danach starten **automatisch** die Prüfungen – jetzt heißt es kurz warten, bis sie
durchgelaufen sind.

Die zugehörige Aufgabe im GitHub Project nach **In Review** ziehen.

---

## 7. Was passiert im Hintergrund? (Branch-Schutz)

Der `main`-Branch ist geschützt. Diese Regeln greifen automatisch:

| Regel | Bedeutung |
| --- | --- |
| **Kein direkter Push auf `main`** | Beiträge laufen über Branch + Pull Request (Schritte 3–6). |
| **`main` kann nicht gelöscht / überschrieben** werden | Kein `git push --force` auf `main` – im Normalfall nicht nötig. |
| **Status-Check `docker-ci` muss grün sein** | Build, `manage.py check`, Tests und ein Health-Check müssen erfolgreich durchlaufen – genau die Prüfungen aus [Schritt 4](#4-änderung-machen-und-prüfen), die bereits lokal ausgeführt wurden. |
| **CodeQL Code-Scanning** | Automatische Sicherheitsprüfung. PRs mit Sicherheitslücken der Stufe **hoch (oder höher)** werden blockiert. |
| **Pull Request erforderlich** | Es sind **0 Reviews** vorgeschrieben – der eigene PR darf gemergt werden, **sobald alle Prüfungen grün sind**. Eine zweite Person ist nicht zwingend, aber willkommen. |

Der Status wird unten im Pull Request angezeigt:

- **gelber Punkt** = Prüfungen laufen noch → kurz warten.
- **grüner Haken** = alles bestanden → mergen ist möglich.
- **rotes Kreuz** = etwas ist fehlgeschlagen → weiter mit [Abschnitt 8](#8-wenn-die-prüfungen-rot-sind).

---

## 8. Wenn die Prüfungen rot sind

Fehlgeschlagene Prüfungen kommen vor und sind kein Grund zur Sorge. Die Ursache lässt sich
meist schnell eingrenzen:

1. Im PR neben dem roten Kreuz auf **Details** klicken.
2. Ablesen, **welcher Schritt** fehlgeschlagen ist (z. B. „Run Django tests").
3. Den Fehler lokal mit demselben Befehl reproduzieren, z. B. `python manage.py test`
   (bzw. die Docker-Variante).
4. Das Problem beheben, dann erneut **auf denselben Branch** committen und pushen:

   ```powershell
   git add .
   git commit -m "Fehler XY behoben"
   git push
   ```

Der Pull Request aktualisiert sich automatisch und die Prüfungen laufen erneut. Ein neuer
PR ist **nicht** nötig.

---

## 9. Mergen und aufräumen

Sobald **alle Prüfungen grün** sind:

1. Im Pull Request auf **Merge pull request** klicken und bestätigen. Erlaubt sind **Merge**,
   **Squash** und **Rebase** – im Zweifel **Squash**, das die Commits zu einem zusammenfasst.
2. Anschließend auf **Delete branch** klicken, um den Arbeits-Branch auf GitHub aufzuräumen.
3. Die Aufgabe im GitHub Project nach **Done** ziehen.
4. Den neuen Stand holen und den lokalen Branch löschen:

   ```powershell
   git checkout main
   git pull
   git branch -d feature/kurze-beschreibung
   ```

Geschafft – die Änderung ist nun in `main`. Für die nächste Änderung geht es wieder bei
[Schritt 3](#3-aufgabe-wählen-und-branch-anlegen) los.

---

## Fehler gefunden? Issue erstellen

Fällt beim Entwickeln oder Testen ein Fehler auf, der nicht zur aktuellen Aufgabe gehört,
wird dafür ein **GitHub Issue** angelegt. Aus solchen Issues werden neue Aufgaben im
[GitHub Project](https://github.com/users/ChoosenMEME/projects/1) – so geht nichts verloren.

1. Im Repository auf den Tab **Issues** → **New issue** klicken.
2. Einen klaren Titel und eine kurze Beschreibung angeben: Was passiert, was wäre erwartet,
   und wie lässt sich der Fehler nachstellen?
3. Das Issue dem **GitHub Project** hinzufügen (Feld „Projects" rechts), damit es in der
   Spalte **Backlog** landet und später eingeplant werden kann.

Auf diese Weise werden gefundene Fehler zu nachvollziehbaren, planbaren Aufgaben, die später
wie in [Schritt 3](#3-aufgabe-wählen-und-branch-anlegen) übernommen werden können.

---

## Spickzettel

**Einmalig – Repository klonen:**

```powershell
git clone https://github.com/ChoosenMEME/xstandardanwendung.git
cd xstandardanwendung
```

**Einmalig – Umgebung einrichten (eine Variante wählen):**

Docker:

```powershell
cp .env.example .env
docker compose -f compose.dev.yaml up -d --build
```

Bare-Metal:

```powershell
python -m venv .venv
# Projekt-venv aktivieren (siehe Schritt 2), dann:
pip install -r requirements.txt
$env:DEBUG = "1"                    # macOS / Linux: export DEBUG=1
$env:SECRET_KEY = "dev-secret-key"  # macOS / Linux: export SECRET_KEY=dev-secret-key
$env:SQLITE_PATH = "dev.db.sqlite3" # macOS / Linux: export SQLITE_PATH=dev.db.sqlite3
cd app && python manage.py migrate && python manage.py runserver
```

**Pro Änderung:**

```powershell
# im GitHub Project eine Aufgabe auswählen und sich selbst zuweisen
git checkout main && git pull
git checkout -b feature/meine-aenderung
# ... Dateien bearbeiten ...
```

Lokal prüfen – Docker:

```powershell
docker compose -f compose.dev.yaml exec web python manage.py check
docker compose -f compose.dev.yaml exec web python manage.py test
```

Lokal prüfen – Bare-Metal (im Ordner `app/`):

```powershell
python manage.py check
python manage.py test
```

Committen und pushen:

```powershell
git add .
git commit -m "Beschreibung der Änderung"
git push -u origin feature/meine-aenderung
# auf GitHub Pull Request erstellen, grüne Prüfungen abwarten, mergen
```

---

## Häufige Fehler & Lösungen

| Problem | Lösung |
| --- | --- |
| `git push` wird auf `main` abgelehnt | Das ist beabsichtigt: Direkte Pushes auf `main` sind gesperrt. Stattdessen einen Branch anlegen ([Schritt 3](#3-aufgabe-wählen-und-branch-anlegen)) und diesen pushen. |
| Bare-Metal: Seite zeigt „Bad Request (400)" | `DEBUG=1` wurde nicht gesetzt. Variable im aktuellen Terminal setzen und Server neu starten. |
| Bare-Metal: `SECRET_KEY must be set` | `SECRET_KEY=dev-secret-key` wurde nicht gesetzt. Variable im aktuellen Terminal setzen und Server neu starten. |
| Bare-Metal: `python` nicht gefunden | `python3` statt `python` verwenden. Unter Windows ggf. Python über den Installer mit „Add to PATH" installieren. |
| venv-Aktivierung in PowerShell scheitert | Einmalig erlauben: `Set-ExecutionPolicy -Scope CurrentUser RemoteSigned`, dann erneut aktivieren. |
| Port 8000 ist belegt | Docker: `WEB_PORT` in der `.env` ändern. Bare-Metal: `python manage.py runserver 8001`. |
| Docker: Codeänderungen wirken nicht | Läuft die **Dev**-Compose (`-f compose.dev.yaml`)? Nur sie spiegelt den Code live. Ggf. mit `--build` neu starten. |
| Docker: „No such service: web" | Umgebung läuft nicht – erst `docker compose -f compose.dev.yaml up -d --build`. |
| Versehentlich `.env` committet | Vor dem Push rückgängig machen: `git rm --cached .env`, neu committen. Keine echten Secrets hochladen. |

Bei Unsicherheiten geben [`AGENTS.md`](AGENTS.md) (technische Konventionen) und die
[`README.md`](README.md) (Projektüberblick und Setup) weitere Hinweise.
</content>
