# Mitwirkende & Einsatz von KI-Tools

Diese Seite ordnet die Pull Requests und Issues des Projekts den drei Mitwirkenden
thematisch zu und dokumentiert, welche KI-Tools dabei jeweils zum Einsatz kamen. Jede
Person hat eine eigene Beiträge-Tabelle; die referenzierten Nummern verweisen auf die
zugehörigen [Pull Requests](https://github.com/ChoosenMEME/xstandardanwendung/pulls?q=is%3Apr)
bzw. [Issues](https://github.com/ChoosenMEME/xstandardanwendung/issues?q=is%3Aissue) im
GitHub-Repository.

> Das Register ist als Ableitung aus der Git-/GitHub-Historie (Autorschaft, verlinkte
> Issues) entstanden – siehe Issue
> [#300](https://github.com/ChoosenMEME/xstandardanwendung/issues/300) zum Stand der
> Verifizierung durch die Mitwirkenden selbst.

## Alexander Bahlmann

Schwerpunkt: Kernfunktionen der Bescheidauswertung – von Upload und Datenextraktion über
Vorjahres- und Mehrjahresvergleich bis zu Export und KI-Assistent.

| Thema | Zusammenfassung | PRs | Issues |
| --- | --- | --- | --- |
| Startseite, Upload & Datenextraktion | Startseite, Upload-Formular, Datei-/XSD-Validierung, Auslesen der zentralen Bescheiddaten (Gemeinde, Steuerjahr, Messbetrag, Hebesatz) sowie Unterscheidung der Nachrichtentypen beim Import | #236, #238, #239, #241, #243, #244, #245, #246, #251, #286 | #13, #14, #15, #16, #17, #18, #19, #20, #21, #22, #25, #26, #285 |
| Berechnung & Plausibilität | Zusammenfassungsseite, verständliche Erklärung der Berechnungslogik und Plausibilitätsprüfung der Bescheiddaten | #247, #250, #279 | #23, #24, #44 |
| Vorjahres- & Mehrjahresvergleich | Vorauszahlungen, Unterscheidung Nachzahlung/Vorauszahlung, optionaler Vorjahresupload, Änderungsvergleich inkl. Hervorhebung wichtiger Änderungen sowie Mehrjahresvergleich und historische Entwicklung | #252, #253, #256, #257, #267, #277, #278 | #27, #28, #29, #30, #31, #42, #43 |
| Fälligkeiten & Hinweise | Hinweisbereich, Ampel-Statusanzeige, Liquiditätswirkung, Fälligkeitskalender und Download der Fristdatei | #268, #269, #274, #275, #276 | #32, #33, #38, #39, #40 |
| Export & Layout | PDF-Bericht, CSV-Export, responsives Design, KERN-UX-konformes Layout, Druckansicht und Speichern der Upload-Historie | #270, #271, #272, #273, #280, #281 | #34, #35, #36, #45, #46 |
| KI-Assistent | Auswertungsbezogener KI-Assistent, globales Assistenten-Panel, modusspezifische Beispielfragen sowie Anpassungen an Navigation und Beispielfragen-Sichtbarkeit | #294, #297, #309, #327, #328 | #287, #296, #306, #326 |

### Alexander Bahlmann

*Eingesetzte KI-Tools:* ChatGPT/Codex 5.5 sowie Ollama im Rahmen des lokalen KI-Assistenten der Anwendung.

Die KI-Tools wurden ergänzend und unterstützend eingesetzt. Sie dienten vor allem dazu, Arbeitsschritte zu strukturieren, Lösungsansätze zu prüfen, Fehlermeldungen besser einzuordnen und Formulierungen bzw. Codevorschläge vorzubereiten. Die fachliche Bewertung, Auswahl der passenden Lösung, Prüfung der Ergebnisse sowie die abschließende Umsetzung erfolgten eigenständig.

- *Projektplanung und Aufgabenstrukturierung:* Unterstützung bei der Strukturierung von Anforderungen, User Stories, GitHub-Issues, Akzeptanzkriterien und Arbeitsschritten. Die daraus entstandenen Aufgaben wurden anschließend fachlich geprüft, angepasst und in den Projektkontext eingeordnet.

- *Implementierungsunterstützung:* Unterstützung bei einzelnen Codevorschlägen, Bugfixes, Refactorings und der Erweiterung bestehender Funktionen. Die Vorschläge wurden nicht ungeprüft übernommen, sondern lokal getestet, angepasst und über die Projektstruktur eingeordnet.

- *Fehlersuche und Debugging:* Unterstützung beim Einordnen von Fehlermeldungen aus Docker, Django, Git, PowerShell und der Webanwendung. Dazu gehörten unter anderem Probleme bei Migrationen, Tests, Routing, Konfigurationen und lokalen Entwicklungsumgebungen.

- *Test und Qualitätssicherung:* Unterstützung beim Ableiten zusätzlicher Testfälle, beim Verstehen fehlgeschlagener Tests und bei der Überprüfung, ob neue Änderungen bestehende Funktionen beeinflussen. Die technische Absicherung erfolgte über lokale Testläufe und Django-Checks.

- *Dokumentation:* Unterstützung bei der Formulierung und Strukturierung von README-Inhalten, technischen Beschreibungen, Reflexionsinhalten, Präsentationsbausteinen und Projektzusammenfassungen. Die Inhalte wurden fachlich geprüft und an die tatsächlich umgesetzten Projektbestandteile angepasst.

- *KI-Assistent innerhalb der Anwendung:* Unterstützung bei der Konzeption und Umsetzung des lokalen KI-Assistenten. Dabei wurde Ollama als lokaler KI-Dienst eingebunden, um Fragen zur Auswertung verständlich zu beantworten. Der Assistent wurde bewusst fachlich begrenzt, um keine Steuerberatung zu ersetzen.

- *Demo- und Infrastrukturunterstützung:* Unterstützung bei der Planung und Fehleranalyse der Live-Demo-Umgebung. Dazu gehörten die Domain-Anbindung über IONOS, die DNS-Konfiguration über Cloudflare, die Einrichtung eines Cloudflare Tunnels, der geschützte Zugriff über Cloudflare Access sowie die Anpassung lokaler Django-Konfigurationen wie ALLOWED_HOSTS und CSRF_TRUSTED_ORIGINS.

- *Git- und Deployment-Unterstützung:* Unterstützung beim Umgang mit Branches, Pull Requests, lokalen Pulls, Docker-Neustarts, .env-Konfigurationen und der Vorbereitung einer stabilen Demo-Umgebung.

*Weitere eingesetzte technische Dienste und Werkzeuge:* Docker, Django, Git/GitHub, Visual Studio Code, PowerShell, IONOS, Cloudflare, Cloudflare Tunnel, Cloudflare Access und Ollama.

Die KI-Unterstützung hatte unterstützenden Charakter. Alle übernommenen Inhalte, Codeänderungen und Konfigurationen wurden geprüft, getestet und an die Anforderungen des Projekts angepasst.

## Sören Schulzke

Schwerpunkt: Datenschutz- und Demo-Funktionen, Validierungsdetails sowie Bedienbarkeit
und Barrierefreiheit.

| Thema | Zusammenfassung | PRs | Issues |
| --- | --- | --- | --- |
| Validierungsdetails bei fehlgeschlagenem Upload | Ausführlichere Anzeige der Validierungsfehler, wenn ein XML-Import fehlschlägt | #288 | #260 |
| Datenschutz-/Anonymisierungsmodus | Optionaler Modus zur Anonymisierung von Anzeige und Export | #289 | #259 |
| STATIC_URL an APP_PATH anpassen | Korrekte Auslieferung statischer Dateien hinter konfigurierbarem URL-Präfix | #290 | #262 |
| Demo-Beispielfall | Laden eines fiktiven Beispielfalls zum Ausprobieren ohne eigenen Upload | #292 | #258 |
| Fehlerbehandlung verbessern | Ersetzen des „Nicht gefunden“-Sentinels durch `None` sowie supportfreundliche Fehler-IDs ohne sensible Daten | #293, #295 | #261, #263 |
| Drag-and-drop-Upload | Datei-Upload per Drag-and-drop, in einer Folge-PR robuster gemacht | #307, #332 | #299 |
| Begriffserklärungen | Tooltips/Erklärungen für Fachbegriffe, später barrierearm platziert | #308, #330 | #41 |

### Sören Schulzke

*Eingesetzte KI-Tools:* ChatGPT/Codex 5.5.

Die KI-Tools wurden ergänzend und unterstützend eingesetzt. Sie dienten vor allem dazu,
Arbeitsschritte zu strukturieren, Lösungsansätze zu prüfen, Fehlermeldungen besser
einzuordnen und Formulierungen bzw. Codevorschläge vorzubereiten. Die fachliche
Bewertung, Auswahl der passenden Lösung, Prüfung der Ergebnisse sowie die abschließende
Umsetzung erfolgten eigenständig.

- *Projektplanung und Aufgabenstrukturierung:* Unterstützung bei der Strukturierung von
  Anforderungen, Akzeptanzkriterien und Arbeitsschritten. Die daraus entstandenen
  Aufgaben wurden anschließend fachlich geprüft und in den Projektkontext eingeordnet.

- *Implementierungsunterstützung:* Unterstützung bei Codevorschlägen für den
  Datenschutz- und Anonymisierungsmodus, den Demo-Beispielfall, die Fehlerbehandlung,
  den Drag-and-drop-Upload und die Begriffserklärungen. Die Vorschläge wurden lokal
  geprüft und an die bestehende Projektstruktur angepasst.

- *Fehlersuche und Debugging:* Unterstützung beim Einordnen von Fehlern im XML-Import,
  bei der Auslieferung statischer Dateien und beim Datei-Upload sowie bei der Entwicklung
  verständlicher, supportfreundlicher Fehlermeldungen ohne sensible Daten.

- *Test und Qualitätssicherung:* Unterstützung beim Ableiten zusätzlicher Testfälle,
  beim Verstehen fehlgeschlagener Tests und beim Absichern der Änderungen durch lokale
  Testläufe und Django-Checks.

- *Bedienbarkeit und Barrierefreiheit:* Unterstützung bei der robusten Umsetzung des
  Drag-and-drop-Uploads sowie bei der verständlichen und barrierearmen Platzierung von
  Erklärungen zu Fachbegriffen.

- *Dokumentation:* Unterstützung bei der Formulierung und Strukturierung technischer
  Beschreibungen und nutzerverständlicher Texte. Die Inhalte wurden fachlich geprüft
  und an die tatsächlich umgesetzten Projektbestandteile angepasst.

*Weitere eingesetzte technische Dienste und Werkzeuge:* Docker, Django, Git/GitHub,
Visual Studio Code und PowerShell.

Die KI-Unterstützung hatte unterstützenden Charakter. Alle übernommenen Inhalte,
Codeänderungen und Konfigurationen wurden geprüft, getestet und an die Anforderungen
des Projekts angepasst.

## Tim Jankowski

Schwerpunkt: Projekt-Setup und Betrieb (Django/Docker/CI), KERN-UX-Einbindung sowie
laufende Pflege von Dokumentation und Benutzeranmeldung.

| Thema | Zusammenfassung | PRs | Issues |
| --- | --- | --- | --- |
| Projekt-Setup & Konfiguration | Initiales Django-/Docker-Projektgerüst, Editor-/Tooling-Konfiguration (PyCharm, VS Code, EditorConfig) sowie Konfigurations- und Internationalisierungsanpassungen | #1, #6, #7, #8, #9, #10, #11, #12, #51, #54, #232 | – |
| CI/CD & Docker-Betrieb | GitHub-Actions-Workflows, Docker-Entrypoint-Logging, Docker-Hub-Publish für Pre-Releases sowie erweiterte Upload-Tests | #4, #230, #231, #234, #248 | – |
| KERN-UX-Einbindung & UI/Design | Einbindung von KERN-UX, verbindliche Designrichtlinie, Multi-Page-Architektur mit modernem Design sowie Logo-/Favicon-Branding | #3, #5, #266, #284, #310 | #255, #303 |
| XGewerbesteuer-Datenstandard & Testdaten | Offizielle XGewerbesteuer-XSD-Schemas, zugehörige Testdateien für alle Nachrichtentypen und deren Dokumentation | #50, #235, #237, #240 | – |
| Architektur & Code-Qualität | Architekturdokumentation, Aufteilung der View-Logik in eigene Module und Entfernen ungenutzter Altlasten | #282, #283, #305 | #37, #264, #265, #301 |
| Benutzeranmeldung & E-Mail-Versand | Login/Benutzerkonto für gespeicherte Auswertungen sowie Verbesserungen an SMTP-Versand und -Diagnose | #298, #333 | #47 |
| Fehlerbehebungen, Sicherheit & Härtung | Behebung produktiver Bugs (u. a. Datenschutz-Leak, Demo-500, fehlende statische Dateien), umgesetzte Härtungs-Issues sowie Sicherheits-/Robustheitsfindings aus dem Code-Review | #324, #325, #329 | #311, #312, #313, #314, #315, #316, #317, #318, #319, #320, #321, #322, #323 |
| Dokumentation & Mitwirkenden-Register | Laufende Pflege von README, CONTRIBUTING und weiteren Dokumenten sowie des Mitwirkenden- und KI-Tools-Registers | #48, #49, #52, #53, #233, #249, #302, #331, #334, #335 | #304 |

**Eingesetzte KI-Tools:** ChatGPT/Codex 5.5 sowie Claude Code mit Sonnet 4.6,
Sonnet 5, Opus 4.8 und Fable 5. Beide Werkzeuge wurden je nach Aufgabe ergänzend
und im Wechsel als Pair-Programming-Unterstützung eingesetzt für:

- **Implementierung und Refactoring:** Projekt-Setup, Bugfixes, kleinere Features,
  Aufteilung der View-Logik und Entfernen ungenutzter Altlasten.
- **Code- und Security-Reviews:** Erkennen und Beheben von Sicherheits- und
  Robustheitsproblemen, darunter Markup-/CSV-Injection, fehlendes Rate-Limiting und
  eine zu lange Speicherung von Bescheiddaten in Sessions (#311–#323).
- **Tests und Fehlersuche:** Ableiten von Regressionstests, Ausführen der Testsuite und
  Eingrenzen fehlgeschlagener Tests.
- **Dokumentation:** Pflege von README, Architektur- und Testdaten-Dokumentation,
  Docstrings sowie dieses Mitwirkenden-Registers (#334, #335), einschließlich des
  Abgleichs mit bestehenden Beiträgen und der lokalen Git-Historie.

Die vorgeschlagenen Änderungen wurden jeweils anhand der Diffs und automatisierten Tests
geprüft; die fachliche Entscheidung und Freigabe lagen bei Tim Jankowski.
