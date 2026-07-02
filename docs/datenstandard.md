# XGewerbesteuer-Datenstandard

Die Anwendung verarbeitet Datensätze nach dem
[XGewerbesteuer-Standard (Version 1.4)](https://www.xrepository.de/details/urn:xoev-de:xunternehmen:standard:gewerbesteuer_1.4#version),
einem XÖV-konformen Standard für den elektronischen Austausch von
Gewerbesteuer(mess)bescheiden zwischen Finanzverwaltung, Kommunen und Unternehmen. Im
XRepository sind dazu u. a. die XML-Schemas (XSD), zugehörige Codelisten und die
fachliche Spezifikation des Standards veröffentlicht.

Im Rahmen dieser Anwendung dient der Standard als verbindliches Datenformat für den
Bescheid-Upload. Neben dem regulären Gewerbesteuerbescheid (`bescheide.gewerbesteuer.0001`)
werden auch die verwandten Nachrichtenarten Zinsbescheid (`bescheide.zinsen.0002`),
Vorauszahlungsbescheid (`bescheide.vorauszahlung.0003`), ein generischer Bescheid
(`bescheide.gewerbesteuer.generisch.0010`) sowie die Berechnungsnachricht
(`berechnung.gewerbesteuer.0021`) erkannt und verarbeitet
(siehe `app/xgewerbesteuer/extractors.py: detect_message_type()`). Die enthaltenen Felder
zu Steuerjahr, Gemeinde, Messbetrag, Hebesatz, Steuerbetrag und Fälligkeiten werden
ausgelesen und für die nutzerfreundliche Aufbereitung verwendet.

Anonymisierte XGewerbesteuer-1.4-Beispieldateien (Musterdaten) werden für die Tests genutzt;
eine Übersicht der Testdaten steht in [`testdaten.md`](testdaten.md).
