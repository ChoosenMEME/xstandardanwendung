# Designrichtlinie fuer die Anwendung

## 1. Ziel dieses Dokuments

Dieses Dokument beschreibt die verbindlichen Design- und UI-Regeln fuer die Anwendung.

Die Anwendung soll vollstaendig mit **KERN-UX** umgesetzt werden. Eigene CSS-Loesungen sind nur erlaubt, wenn KERN-UX fuer einen konkreten Fall keine passende Komponente, Utility-Klasse oder Gestaltungsvorgabe anbietet.

Ziel ist eine sachliche, moderne, barrierearme und konsistente Weboberflaeche, die fuer eine Verwaltungsanwendung geeignet ist.

---

## 2. Grundprinzipien

Die Anwendung soll:

* serioes und professionell wirken,
* klar strukturiert sein,
* auf unnoetige visuelle Spielereien verzichten,
* Informationen verstaendlich priorisieren,
* auch bei vielen Daten uebersichtlich bleiben,
* vollstaendig responsiv nutzbar sein,
* moeglichst barrierearm umgesetzt werden,
* einheitlich mit KERN-UX-Komponenten gestaltet sein.

Die Oberflaeche soll nicht wie ein technischer Prototyp wirken, sondern wie eine fertige Verwaltungsanwendung.

---

## 3. KERN-UX als verbindlicher Designstandard

KERN-UX (`@kern-ux/native` 2.6.2) wird lokal aus `app/static/vendor/kern/` in
`app/templates/base.html` eingebunden — bewusst ohne CDN (Datenschutz:
IP-Weitergabe an Dritte; Offline-/Intranet-Betrieb; keine Manipulationsgefahr
durch Dritte):

```html
<link href="{% static 'vendor/kern/kern.min.css' %}" rel="stylesheet"/>
<link href="{% static 'vendor/kern/fonts/fira-sans.css' %}" rel="stylesheet"/>
```

Fuer ein Versions-Update werden `kern.min.css`, `fonts/fira-sans.css` und die
`fonts/fira-sans/*.woff2`-Dateien aus dem npm-Paket `@kern-ux/native`
uebernommen und `THIRD-PARTY-NOTICES.md` aktualisiert.

Fuer Layout, Typografie, Buttons, Formulare, Hinweise, Navigation, Tabellen, Cards und Statusdarstellungen sind bevorzugt KERN-UX-Komponenten und KERN-UX-Klassen zu verwenden.

### Verbindliche Regel

Vor jeder eigenen HTML-/CSS-Loesung ist zu pruefen:

1. Gibt es eine passende KERN-UX-Komponente?
2. Gibt es eine passende KERN-UX-Utility-Klasse?
3. Gibt es ein bestehendes Projektmuster, das wiederverwendet werden kann?

Nur wenn alle drei Fragen verneint werden, darf eigenes CSS ergaenzt werden.

Eigenes CSS muss sparsam, nachvollziehbar und komponentennah sein.

---

## 4. Seitenlayout

Jede Seite folgt grundsaetzlich diesem Aufbau:

1. Kopfbereich mit Seitentitel
2. Optionaler Beschreibungstext
3. Optionaler Aktionsbereich
4. Hauptinhalt in Cards, Tabellen oder Formularbereichen
5. Optionaler Hinweis- oder Ergebnisbereich

### Beispielstruktur (Django-Template)

```html
{% extends "base.html" %}

{% block title %}Seitentitel{% endblock %}

{% block content %}
<section>
  <h1>Seitentitel</h1>
  <p>Kurze Beschreibung der Funktion.</p>

  <!-- Inhalt -->
</section>
{% endblock %}
```

Wenn KERN-UX eigene Container-, Grid- oder Section-Klassen bereitstellt, sind diese anstelle eigener Klassen zu verwenden.

---

## 5. Navigation

Die Navigation soll einfach, klar und vorhersehbar sein.

### Hauptnavigation

Die Hauptnavigation enthaelt nur zentrale Bereiche:

* Startseite
* Upload
* Auswertung
* Bescheide
* Hilfe / Hinweise

Nicht jede Nebenfunktion erhaelt einen eigenen Hauptnavigationseintrag.

### Aktiver Zustand

Der aktuell aktive Bereich muss visuell eindeutig erkennbar sein.

### Navigationslogik

Navigationselemente muessen:

* verstaendlich benannt sein,
* konsistent sortiert sein,
* auf allen Seiten gleich funktionieren,
* auch per Tastatur erreichbar sein.

---

## 6. Startseite

Die Startseite soll den Zweck der Anwendung sofort erklaeren.

Sie enthaelt:

* eine kurze Einordnung der Anwendung,
* eine primaere Handlung, z. B. "Bescheid hochladen",
* eine zweite Handlung, z. B. "Beispieldaten ansehen",
* eine kurze Erklaerung der wichtigsten Funktionen,
* optional Hinweise zu Datenschutz oder Dateiformaten.

Die Startseite soll nicht ueberladen sein.

### Inhaltliche Prioritaet

Die wichtigste Aktion ist der Upload eines Bescheids. Diese Aktion muss auf der Startseite visuell hervorgehoben werden.

---

## 7. Upload-Seite

Die Upload-Seite ist ein zentraler Bestandteil der Anwendung und muss besonders verstaendlich gestaltet werden.

Sie enthaelt:

* eine klare Ueberschrift,
* eine kurze Erklaerung, welche Datei erwartet wird,
* ein gut sichtbares Upload-Feld,
* Hinweise zu erlaubten Dateitypen,
* Hinweise zu Datenschutz und Verarbeitung,
* verstaendliche Fehlermeldungen,
* einen klaren primaeren Button.

### Upload-Feld (Django-Template)

```html
<form method="post" enctype="multipart/form-data">
  {% csrf_token %}

  <p>
    <label for="bescheid">Aktuellen XGewerbesteuer-Bescheid auswaehlen (Pflicht):</label><br>
    <input type="file" id="bescheid" name="bescheid" accept=".xml">
  </p>

  <p>
    Beide Dateien werden nur fuer diese Anfrage verarbeitet und nicht dauerhaft gespeichert.
  </p>

  <p>
    <button type="submit">
      Bescheide hochladen
    </button>
  </p>
</form>
```

Es muss klar sein:

* welche Datei hochgeladen werden kann,
* ob der Upload erfolgreich war,
* ob ein Fehler aufgetreten ist,
* was der Nutzer als Naechstes tun soll.

---

## 8. Ergebnis- und Auswertungsseiten

Ergebnisse sollen nicht als reine Rohdaten dargestellt werden.

Stattdessen sollen wichtige Informationen priorisiert und visuell gegliedert werden.

### Empfohlene Struktur

1. Zusammenfassung der wichtigsten Werte
2. Detailinformationen
3. Vergleichswerte
4. Hinweise / Auffaelligkeiten
5. Export- oder Weiterverarbeitungsoptionen

### Wichtige Kennzahlen

Zentrale Werte sollen als uebersichtliche Kennzahlen-Cards dargestellt werden.

Beispiele:

* Gewerbesteuermessbetrag
* Hebesatz
* festgesetzte Gewerbesteuer
* Faelligkeit
* Zahlungsbetrag
* Abweichung zum Vorjahr

Jede Kennzahl soll eine verstaendliche Beschriftung haben. Abkuerzungen sind zu vermeiden oder zu erklaeren.

---

## 9. Tabellen

Tabellen muessen gut lesbar, sortierbar und visuell ruhig gestaltet sein.

### Tabellenregeln

* Tabellen haben klare Spaltenueberschriften.
* Zahlenwerte werden einheitlich ausgerichtet.
* Geldbetraege werden einheitlich formatiert.
* Datumswerte werden im deutschen Format dargestellt.
* Lange Tabellen erhalten ausreichend Abstand und Struktur.
* Leere Tabellen zeigen einen verstaendlichen Leerezustand.
* Fehlerhafte oder auffaellige Werte werden nicht nur ueber Farbe markiert.

### Beispiel (Django-Template)

```html
<table>
  <thead>
    <tr>
      <th scope="col">Information</th>
      <th scope="col">Wert</th>
    </tr>
  </thead>
  <tbody>
    {% for item in summary_items %}
      <tr>
        <th scope="row">{{ item.label }}</th>
        <td><strong>{{ item.value }}</strong></td>
      </tr>
    {% endfor %}
  </tbody>
</table>
```

### Keine Rohdaten-Optik

Tabellen sollen nicht wie ein Datenbank-Dump wirken. Spaltennamen wie `betrag_raw`, `id`, `created_at` oder interne technische Namen duerfen dem Nutzer nicht ungefiltert angezeigt werden.

---

## 10. Formulare

Formulare werden mit KERN-UX-Formularkomponenten umgesetzt.

### Pflichtregeln

Jedes Eingabefeld braucht:

* ein sichtbares Label,
* bei Bedarf einen Hilfetext,
* verstaendliche Fehlermeldungen,
* passende Eingabetypen,
* eine erkennbare Pflichtfeldmarkierung, falls erforderlich.

### Button-Anordnung

Primaere Aktionen stehen visuell im Vordergrund.

Sekundaere Aktionen duerfen nicht staerker wirken als primaere Aktionen.

Beispiel:

* Primaer: "Speichern"
* Sekundaer: "Abbrechen"
* Destruktiv: "Loeschen"

---

## 11. Buttons und Aktionen

Buttons muessen konsistent eingesetzt werden.

### Primaerer Button

Der primaere Button wird nur fuer die wichtigste Aktion auf einer Seite verwendet.

Beispiele:

* "Bescheid hochladen"
* "Auswertung starten"
* "Speichern"

### Sekundaere Buttons

Sekundaere Buttons werden fuer unterstuetzende Aktionen verwendet.

Beispiele:

* "Zurueck"
* "Abbrechen"
* "Weitere Details anzeigen"

### Destruktive Aktionen

Loesch- oder Zuruecksetz-Aktionen muessen visuell und textlich eindeutig sein.

Beispiel:

Nicht:
`OK`

Sondern:
`Bescheid endgueltig loeschen`

---

## 12. Cards und Inhaltsbloecke

Cards sollen verwendet werden, um zusammengehoerige Informationen zu gruppieren.

Geeignete Einsatzbereiche:

* Kennzahlen
* Ergebniszusammenfassungen
* Uploadbereiche
* Hinweise
* Funktionsuebersichten
* Detailinformationen

Cards duerfen nicht uebermaessig verschachtelt werden.

Jede Card benoetigt eine klare inhaltliche Funktion.

---

## 13. Statusmeldungen und Hinweise

Statusmeldungen muessen mit KERN-UX-Hinweis- oder Alert-Komponenten umgesetzt werden.

### Arten von Meldungen

* Erfolg
* Hinweis
* Warnung
* Fehler

### Beispiel (Django-Template)

Fehlermeldungen verwenden `role="alert"` und werden per `{% if %}` bedingt eingeblendet:

```html
{% if validation_error %}
  <div role="alert">
    <h2>Validierungsfehler</h2>
    <p>
      <strong>{{ validation_error }}</strong>
    </p>
    <p>
      Bitte waehlen Sie eine gueltige XML-Datei im XGewerbesteuer-Format aus.
    </p>
  </div>
{% endif %}
```

### Anforderungen

Meldungen muessen:

* verstaendlich formuliert sein,
* konkrete naechste Schritte nennen,
* nicht nur technisch beschreiben, was passiert ist,
* nicht ausschliesslich ueber Farbe verstaendlich sein.

### Beispiel

Schlecht:

```text
XML parsing failed.
```

Besser:

```text
Die XML-Datei konnte nicht gelesen werden. Bitte pruefen Sie, ob es sich um einen gueltigen XGewerbesteuer-Bescheid handelt.
```

---

## 14. Fehlerzustaende

Fehlerseiten und Fehlermeldungen muessen nutzerfreundlich gestaltet sein.

Bei Fehlern soll erklaert werden:

* was passiert ist,
* warum die Aktion nicht abgeschlossen werden konnte,
* was der Nutzer tun kann,
* ob Daten verloren gegangen sind oder nicht.

Technische Stacktraces duerfen niemals in der Nutzeroberflaeche angezeigt werden.

---

## 15. Leerezustaende

Leere Zustaende muessen aktiv gestaltet werden.

Beispiele:

* Noch keine Bescheide hochgeladen
* Keine Auswertung vorhanden
* Keine Vergleichsdaten verfuegbar
* Keine Treffer gefunden

Ein Leerezustand soll nach Moeglichkeit eine sinnvolle naechste Aktion anbieten.

Beispiel:

```text
Es wurden noch keine Bescheide hochgeladen.
Laden Sie einen Gewerbesteuerbescheid hoch, um eine Auswertung zu starten.
```

---

## 16. Barrierearmut

Die Anwendung soll moeglichst barrierearm umgesetzt werden.

### Mindestanforderungen

* Semantisches HTML verwenden
* Ueberschriftenhierarchie einhalten
* Buttons als `<button>` umsetzen, Links als `<a>`
* Formulare mit Labels versehen
* Ausreichende Kontraste sicherstellen
* Fokuszustaende sichtbar lassen
* Keine Information ausschliesslich ueber Farbe vermitteln
* Tastaturbedienung ermoeglichen
* Alternativtexte fuer relevante Bilder verwenden

---

## 17. Sprache und Tonalitaet

Die Anwendung verwendet eine sachliche, verstaendliche und verwaltungsnahe Sprache.

### Sprachregeln

* Keine unnoetigen Fachbegriffe
* Keine Umgangssprache
* Keine technischen Fehlermeldungen fuer Endnutzer
* Kurze, klare Saetze
* Aktive Formulierungen
* Einheitliche Begriffe

### Beispiel

Nicht:

```text
Bescheid wurde geparsed.
```

Sondern:

```text
Der Bescheid wurde erfolgreich ausgewertet.
```

---

## 18. Datenformatierung

Daten muessen einheitlich formatiert werden.

### Geldbetraege

Geldbetraege werden im deutschen Format dargestellt.

Beispiel:

```text
1.234,56 EUR
```

### Datumswerte

Datumswerte werden im deutschen Format dargestellt.

Beispiel:

```text
26.06.2026
```

### Prozentwerte

Prozentwerte werden einheitlich dargestellt.

Beispiel:

```text
12,5 %
```

### Fehlende Werte

Fehlende Werte duerfen nicht als `null`, `None`, `undefined` oder leerer technischer Wert angezeigt werden.

Stattdessen:

```text
Nicht verfuegbar
```

oder kontextabhaengig:

```text
Keine Angabe im Bescheid vorhanden
```

---

## 19. Responsive Design

Die Anwendung muss auf Desktop, Tablet und Smartphone nutzbar sein.

### Desktop

Auf Desktop duerfen mehrspaltige Layouts verwendet werden.

### Tablet

Inhalte sollen weiterhin strukturiert und lesbar bleiben.

### Smartphone

Auf kleinen Bildschirmen muessen Inhalte untereinander dargestellt werden.

Tabellen muessen responsiv geloest werden, z. B. durch horizontales Scrollen oder alternative kompakte Darstellungen.

---

## 20. Eigene CSS-Regeln

Eigene CSS-Regeln sind nur ergaenzend erlaubt.

### Erlaubt

* kleine Layoutkorrekturen,
* projektspezifische Abstaende,
* spezifische Darstellung von Ergebnisbereichen,
* Ergaenzungen, die KERN-UX nicht abdeckt.

### Nicht erlaubt

* vollstaendige eigene Button-Systeme,
* eigene Formularsysteme,
* eigene Farbpaletten ohne Bezug zu KERN-UX,
* globale Ueberschreibungen von KERN-UX ohne zwingenden Grund,
* Inline-Styles in Templates.

---

## 21. Template-Regeln

Django-Templates muessen uebersichtlich und wartbar bleiben.

### Vererbung und Bloecke

Alle Seiten-Templates erweitern `base.html` ueber `{% extends "base.html" %}` und fuellen die definierten Bloecke:

* `{% block title %}` fuer den Seitentitel
* `{% block extra_head %}` fuer zusaetzliche Stylesheets oder Meta-Tags
* `{% block content %}` fuer den Seiteninhalt

### Einrueckung

Django-HTML-Templates verwenden 2 Leerzeichen Einrueckung (siehe `.editorconfig`).

### Vorgaben

* Wiederverwendbare UI-Bestandteile werden als `{% include %}`-Partials ausgelagert.
* Wiederkehrende Cards, Tabellenbereiche und Hinweise werden nicht mehrfach kopiert.
* Templates enthalten moeglichst wenig Logik.
* Komplexere Datenaufbereitung erfolgt in Views, Services oder Template-Tags.
* Klassennamen und Komponentenstruktur bleiben konsistent.

### Bedingte Abschnitte

Optionale Seitenbereiche werden mit `{% if %}` gesteuert:

```html
{% if summary_items %}
  <h2>Zusammenfassung des Bescheids</h2>
  <!-- Inhalte -->
{% endif %}
```

### Schleifen

Listen und Tabellenzeilen werden mit `{% for %}` gerendert:

```html
{% for item in summary_items %}
  <tr>
    <th scope="row">{{ item.label }}</th>
    <td><strong>{{ item.value }}</strong></td>
  </tr>
{% endfor %}
```

### Empfohlene Struktur

```text
app/
  templates/
    base.html
    partials/
      header.html
      navigation.html
      messages.html
      footer.html
      card_metric.html
      alert.html
  xgewerbesteuer/
    templates/
      (weitere Seiten-Templates)
```

Projektweite Partials liegen unter `app/templates/partials/`. App-spezifische Templates liegen unter `app/xgewerbesteuer/templates/`.

---

## 22. Wiederverwendbare Komponenten

Fuer wiederkehrende UI-Muster sollen eigene Template-Partials als `{% include %}`-Dateien erstellt werden.

Geeignete Komponenten:

* Kennzahlen-Card
* Hinweisbox
* Upload-Box
* Ergebnis-Card
* Tabellenkopf
* Leerezustand
* Status-Badge
* Button-Gruppe

### Beispiel (Partial mit Kontext)

`app/templates/partials/card_metric.html`:

```html
<div>
  <p>{{ label }}</p>
  <p><strong>{{ value }}</strong></p>
</div>
```

Einbindung im Seiten-Template:

```html
{% include "partials/card_metric.html" with label="Gewerbesteuermessbetrag" value=messbetrag %}
```

Diese Partials muessen KERN-UX verwenden und duerfen nicht als eigenes konkurrierendes Designsystem aufgebaut werden.

---

## 23. Icons

Icons duerfen verwendet werden, wenn sie die Verstaendlichkeit erhoehen.

### Regeln

* Icons sind unterstuetzend, nicht ersetzend.
* Ein Icon ersetzt keinen Text.
* Icons muessen konsistent verwendet werden.
* Dekorative Icons brauchen keine fachliche Bedeutung.
* Bedeutungsvolle Icons benoetigen zugaengliche Beschriftungen.

---

## 24. Logo und Favicon

Logo und Favicon liegen als versionierte Quelldateien unter `app/static/branding/`
(projektweites `STATICFILES_DIRS`, nicht das generierte `app/staticfiles/`):

* `logo.svg` – Logo, eingebunden im Header (`partials/header.html`) neben dem
  Anwendungsnamen. Da der Anwendungsname direkt daneben steht, bekommt das Bild
  `alt=""`.
* `favicon.svg` – bevorzugtes Favicon fuer moderne Browser (`base.html`,
  `rel="icon"`).
* `favicon.ico` – Mehrgroessen-ICO (16/32/48 px) als Fallback fuer Browser ohne
  SVG-Favicon-Unterstuetzung (`rel="alternate icon"`).
* `apple-touch-icon.png` – 180×180 px PNG mit deckendem Hintergrund fuer
  iOS-Home-Bildschirm und Lesezeichen (`rel="apple-touch-icon"`).

Alle Dateien werden ausschliesslich ueber Django Static Files ausgeliefert, es
werden keine extern nachgeladenen Bildressourcen verwendet.

---

## 25. Farben

Farben werden grundsaetzlich durch KERN-UX vorgegeben.

Eigene Farben sind nur in Ausnahmefaellen erlaubt.

Statusfarben muessen semantisch eindeutig verwendet werden:

* Erfolg
* Warnung
* Fehler
* Information
* Neutral

Wichtige Informationen duerfen nicht ausschliesslich ueber Farbe vermittelt werden.

---

## 26. Abstaende und visuelle Hierarchie

Die Oberflaeche muss mit klaren Abstaenden arbeiten.

### Regeln

* Zusammengehoerige Inhalte stehen nah beieinander.
* Unterschiedliche Inhaltsgruppen sind sichtbar getrennt.
* Ueberschriften strukturieren die Seite.
* Cards und Sections geben Orientierung.
* Seiten duerfen nicht ueberladen wirken.

---

## 27. Akzeptanzkriterien fuer UI-Aenderungen

Eine UI-Aenderung gilt nur als fertig, wenn folgende Punkte erfuellt sind:

* KERN-UX wurde bevorzugt verwendet.
* Die Seite ist optisch konsistent mit dem Rest der Anwendung.
* Die Seite funktioniert auf Desktop und Smartphone.
* Texte sind verstaendlich und sachlich.
* Fehlermeldungen sind nutzerfreundlich.
* Leerezustaende sind vorhanden.
* Tastaturbedienung wurde nicht verschlechtert.
* Keine technischen Rohdaten werden unnoetig angezeigt.
* Eigene CSS-Regeln sind minimal und nachvollziehbar.
* Die Aenderung wirkt wie Teil einer fertigen Verwaltungsanwendung.

---

## 28. Konkrete Anweisung fuer KI-Agenten

Wenn ein KI-Agent an dieser Anwendung arbeitet, muss er diese Designrichtlinie beachten.

Der Agent soll bei jeder UI-Aenderung:

1. Bestehende Templates und Komponenten pruefen.
2. KERN-UX-Komponenten bevorzugt verwenden.
3. Keine unnoetigen eigenen CSS-Systeme erstellen.
4. Wiederverwendbare Bestandteile als `{% include %}`-Partial auslagern.
5. Nutzertexte verstaendlich formulieren.
6. Fehler-, Leer- und Ladezustaende beruecksichtigen.
7. Die Darstellung auf kleinen Bildschirmen mitdenken.
8. Aenderungen so umsetzen, dass sie optisch zum bestehenden Projekt passen.

Wenn bestehende Seiten uneinheitlich oder unfertig wirken, soll der Agent sie konsistent nach dieser Richtlinie verbessern.

---

## 29. Zielbild

Die Anwendung soll am Ende wirken wie eine sachliche, moderne und verlaessliche Verwaltungssoftware.

Sie soll nicht wie eine lose Sammlung von HTML-Seiten wirken, sondern wie ein konsistentes Produkt mit klarer Nutzerfuehrung, verstaendlichen Ergebnissen und professioneller Gestaltung auf Basis von KERN-UX.
