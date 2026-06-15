# XGewerbesteuer-Datenstandard

Die Anwendung verarbeitet Datensätze nach dem
[XGewerbesteuer-Standard (Version 1.4)](https://www.xrepository.de/details/urn:xoev-de:xunternehmen:standard:gewerbesteuer_1.4#version),
einem XÖV-konformen Standard für den elektronischen Austausch von
Gewerbesteuer(mess)bescheiden zwischen Finanzverwaltung, Kommunen und Unternehmen. Im
XRepository sind dazu u. a. die XML-Schemas (XSD), zugehörige Codelisten und die
fachliche Spezifikation des Standards veröffentlicht.

Im Rahmen dieser Anwendung dient der Standard als verbindliches Datenformat für den
Bescheid-Upload: Die enthaltenen Felder zu Steuerjahr, Gemeinde, Messbetrag, Hebesatz,
Steuerbetrag und Fälligkeiten werden ausgelesen und für die nutzerfreundliche Aufbereitung
verwendet.

Anonymisierte XGewerbesteuer-1.4-Beispieldateien (Musterdaten) werden für die Tests genutzt;
eine Übersicht der Testdaten steht in [`testdaten.md`](testdaten.md).
