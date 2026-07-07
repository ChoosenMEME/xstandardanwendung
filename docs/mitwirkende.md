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

**Eingesetzte KI-Tools:** ChatGPT/Codex 5.5

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

**Eingesetzte KI-Tools:** ChatGPT/Codex 5.5

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

**Eingesetzte KI-Tools:** ChatGPT/Codex 5.5 und Claude Code (Sonnet 4.6, Sonnet 5,
Opus 4.8, Fable 5)
