# Design Thinking: GewSt-Bescheidassistent

Diese Dokumentation beschreibt den Design-Thinking-Prozess, der der Konzeption des
GewSt-Bescheidassistenten vorgeschaltet wurde. Sie bildet die fachliche Grundlage für die
technische Umsetzung in diesem Repository (siehe [README.md](../README.md)).

## 1. Ausgangslage / Einleitung

Digitale Gewerbesteuerbescheide enthalten strukturierte Daten nach dem Standard
[XGewerbesteuer](https://www.xrepository.de/details/urn:xoev-de:xunternehmen:standard:gewerbesteuer_1.4#version).
Diese Daten sind technisch gut weiterverarbeitbar, für viele kleine Unternehmen jedoch
fachlich schwer verständlich. Besonders problematisch sind die Einordnung des
Zahlbetrags, die Erkennung von Fälligkeiten, die Nachvollziehbarkeit der Berechnung sowie
der Vergleich mit früheren Bescheiden.

Der GewSt-Bescheidassistent verfolgt daher das Ziel, digitale Gewerbesteuerbescheide
nutzerfreundlich aufzubereiten. Die Anwendung soll zentrale Informationen automatisch
auslesen, verständlich darstellen und dadurch Unsicherheit sowie manuellen Suchaufwand
reduzieren.

## 2. Empathize: Persona

| Merkmal | Ausprägung |
| --- | --- |
| Name | Sabine Keller |
| Alter | 42 Jahre |
| Rolle | Inhaberin eines kleinen Cafés |
| Vorkenntnisse | Grundverständnis für Buchhaltung, aber keine steuerliche Fachausbildung |
| Digitale Kompetenz | durchschnittlich; nutzt Online-Banking, ELSTER und einfache Buchhaltungssoftware |

**Ziel der Nutzerin:**
Sabine möchte nach Erhalt ihres digitalen Gewerbesteuerbescheids schnell verstehen,

- wie viel sie zahlen muss,
- wann die Zahlung fällig ist,
- warum sich der Betrag gegenüber dem Vorjahr verändert hat,
- ob Vorauszahlungen oder zusätzliche Kosten enthalten sind.

**Nutzungskontext:**
Sabine erhält einen digitalen Gewerbesteuerbescheid. Der Bescheid enthält zwar
strukturierte Daten, ist für sie aber fachlich schwer zugänglich. Sie nutzt deshalb eine
Webanwendung, um den Bescheid hochzuladen und eine verständliche Auswertung zu erhalten.

## 3. Customer Journey

| Schritt | Handlung | Emotion | Problem |
| --- | --- | --- | --- |
| 1 | Sabine erhält den digitalen Gewerbesteuerbescheid | angespannt, unsicher | Der Bescheid wirkt formal und schwer verständlich. |
| 2 | Sie öffnet den Bescheid und sucht den Zahlbetrag | konzentriert, leicht überfordert | Der wichtigste Betrag ist nicht sofort eindeutig erkennbar. |
| 3 | Sie sucht nach Fälligkeiten und Vorauszahlungen | gestresst | Zahlungsfristen sind über den Bescheid verteilt. |
| 4 | Sie versucht die Berechnung nachzuvollziehen | frustriert | Begriffe wie Messbetrag, Hebesatz und Festsetzung sind nicht intuitiv. |
| 5 | Sie vergleicht den Bescheid mit dem Vorjahr | unsicher | Änderungen sind nicht direkt sichtbar. |
| 6 | Sie schätzt die finanzielle Auswirkung ein | besorgt | Die Liquiditätswirkung bleibt unklar. |
| 7 | Sie überlegt, die Steuerberatung zu kontaktieren | abhängig, genervt | Es entsteht zusätzlicher Abstimmungsaufwand. |

## 4. Pain Points

| Priorität | Pain Point | Begründung |
| --- | --- | --- |
| 1 | Fällige Zahlungen und Fristen sind nicht sofort ersichtlich | Kann zu Unsicherheit, Planungsproblemen oder verspäteten Zahlungen führen. |
| 2 | Änderungen zum Vorjahr sind schwer nachvollziehbar | Sabine versteht nicht, warum sie mehr oder weniger zahlen muss. |
| 3 | Die Berechnungslogik ist schwer verständlich | Steuerliche Fachbegriffe erschweren die Einordnung. |
| 4 | Relevante Informationen sind über den Bescheid verteilt | Die Suche kostet Zeit und erhöht die Fehlerwahrscheinlichkeit. |
| 5 | Die finanzielle Auswirkung bleibt unklar | Sabine kann ihre Liquidität schlechter planen. |
| 6 | Rückfragen an Steuerberatung oder Verwaltung werden wahrscheinlicher | Zusätzlicher Zeit- und Kommunikationsaufwand entsteht. |

**Ableitung für den Prototyp:**
Der Prototyp muss Betrag, Frist, Vorjahresvergleich und finanzielle Auswirkung auf einen
Blick darstellen.

## 5. Define: Problem Statement

> Sabine Keller hat das Problem, dass sie digitale Gewerbesteuerbescheide nicht schnell
> und sicher versteht, weil zentrale Informationen wie Zahlbetrag, Fälligkeit,
> Berechnungsgrundlage und Veränderungen zum Vorjahr fachlich komplex und verteilt
> dargestellt werden. Das führt dazu, dass sie unsicher bei der Finanzplanung ist, mehr
> Zeit für die Auswertung benötigt und häufiger externe Hilfe durch Steuerberatung oder
> Verwaltung in Anspruch nehmen muss.

## 6. Design Challenge

> Wie können wir kleinen Unternehmen ermöglichen, digitale Gewerbesteuerbescheide
> schneller zu verstehen, damit sie fällige Zahlungen sicher planen, Änderungen
> nachvollziehen und finanzielle Risiken besser einschätzen können?

## 7. OKR

**Objective:**
Kleine Unternehmen können Gewerbesteuerbescheide schneller verstehen, relevante
Änderungen besser nachvollziehen und fällige Zahlungen sicherer planen.

**Key Results:**

| Key Result | Zielwert | Beschreibung |
| --- | --- | --- |
| KR1 | 90 % | der Testnutzer:innen finden den fälligen Zahlbetrag ohne zusätzliche Hilfe. |
| KR2 | 95 % | der Testnutzer:innen erkennen die wichtigste Änderung gegenüber dem Vorjahr korrekt. |
| KR3 | −70 % | weniger Suchzeit bis zum Finden der nächsten Zahlungsfrist. |
| KR4 | 80 % | der Testnutzer:innen können erklären, warum sich der Betrag verändert hat. |

## 8. Ideate: Lösungsidee

Der GewSt-Bescheidassistent ist eine Webanwendung, die digitale
Gewerbesteuerbescheide nutzerfreundlich aufbereitet.

Die Anwendung ermöglicht:

- Upload eines XGewerbesteuer-Bescheids,
- automatische Zusammenfassung zentraler Informationen,
- Anzeige von Zahlbetrag, Gemeinde, Steuerjahr und Fälligkeiten,
- verständliche Erklärung von Messbetrag, Hebesatz und Gewerbesteuer,
- Vergleich mit einem Vorjahresbescheid,
- Übersicht über Vorauszahlungen und kommende Zahlungen,
- Ausgabe eines kompakten Analyseberichts.

## 9. Prototype: Funktionskonzept

| Bereich | Funktion | Nutzen |
| --- | --- | --- |
| Startseite | Kurze Erklärung der Anwendung | Nutzer:innen verstehen sofort, wofür die Anwendung gedacht ist. |
| Upload | XML-Bescheid hochladen | Digitale Bescheiddaten werden automatisch eingelesen. |
| Zusammenfassung | Zahlbetrag, Jahr, Gemeinde, Fälligkeit | Wichtigste Informationen erscheinen auf einen Blick. |
| Fristenübersicht | Zahlungen chronologisch darstellen | Zahlungsfristen werden nicht übersehen. |
| Berechnungserklärung | Messbetrag, Hebesatz und Steuerbetrag erklären | Fachbegriffe werden verständlicher. |
| Änderungsvergleich | Vergleich mit Vorjahresbescheid | Veränderungen werden transparent. |
| Hinweisbogen | Auffälligkeiten verständlich erklären | Nutzer:innen erhalten Orientierung. |
| Export | Bericht als PDF/CSV | Ergebnisse können gespeichert oder weitergegeben werden. |

## 10. Story Map

| Schritt | Nutzerziel | Funktion im System |
| --- | --- | --- |
| 1 | Bescheid erhalten | Einstieg mit kurzer Erklärung und Nutzungshinweis |
| 2 | Bescheid hochladen | Upload des digitalen XGewerbesteuer-Bescheids |
| 3 | Bescheid verstehen | Automatische Zusammenfassung zentraler Informationen |
| 4 | Fristen erkennen | Übersicht über Zahlungen und Fälligkeiten |
| 5 | Berechnung nachvollziehen | Erklärung von Messbetrag, Hebesatz und Gewerbesteuer |
| 6 | Änderungen vergleichen | Vergleich mit Vorjahresbescheid |
| 7 | Ergebnis sichern | Ausgabe eines kompakten Analyseberichts |

**Ziel der Story Map:**
Die Anwendung unterstützt Nutzer:innen dabei, einen Gewerbesteuerbescheid digital
hochzuladen, automatisch auszuwerten und verständlich darzustellen. Zusätzlich werden
Fristen, Berechnungen und Veränderungen gegenüber Vorjahren transparent gemacht.

## 11. Test: Evaluation des Prototyps

Der Prototyp kann mit kurzen Usability-Tests geprüft werden. Testpersonen erhalten
typische Aufgaben, zum Beispiel:

- Finden Sie den fälligen Zahlbetrag.
- Finden Sie die nächste Zahlungsfrist.
- Erklären Sie, warum sich der Betrag gegenüber dem Vorjahr verändert hat.
- Entscheiden Sie, ob eine Vorauszahlung enthalten ist.
- Exportieren Sie einen Analysebericht.

**Messgrößen:**

- benötigte Zeit pro Aufgabe,
- Anzahl der Fehlklicks,
- Anteil korrekt gelöster Aufgaben,
- subjektive Verständlichkeit,
- wahrgenommene Sicherheit bei der Finanzplanung.
