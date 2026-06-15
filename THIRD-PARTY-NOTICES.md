# Drittanbieter-Lizenzen (Third-Party Notices)

Der **GewSt-Bescheidassistent** selbst steht unter der MIT-Lizenz (siehe [`LICENSE`](LICENSE)).
Er nutzt bzw. liefert die folgenden Komponenten Dritter mit. Die jeweiligen Lizenzen und
Urheberrechtshinweise gelten unverändert weiter.

## Übersicht

| Komponente | Version | Lizenz (SPDX) | Einbindung |
| --- | --- | --- | --- |
| [Python](https://www.python.org/) | 3.12 | `PSF-2.0` (Python Software Foundation License) | Laufzeit / Basis-Image |
| [Django](https://www.djangoproject.com/) | 6.0.x | `BSD-3-Clause` | Abhängigkeit, im Docker-Image |
| [KERN UX (`@kern-ux/native`)](https://www.kern-ux.de/) | latest (CDN) | EUPL 1.2 | via jsDelivr-CDN (nicht mitausgeliefert) |

## Hinweise und Urheberrechte

- **Python** – Copyright © Python Software Foundation. Lizenz: PSF License Agreement,
  <https://docs.python.org/3/license.html>.
- **Django** – Copyright © Django Software Foundation and individual contributors.
  BSD-3-Clause, <https://github.com/django/django/blob/main/LICENSE>.
- **KERN UX** – UI-/Designsystem; wird per CDN eingebunden (nicht im Repository/Image
  enthalten). Lizenz: EUROPÄISCHE UNION PUBLIC LICENCE v. 1.2

## Python-Abhängigkeiten neu erzeugen

Die obige Liste der Python-Pakete lässt sich automatisch aktualisieren:

```bash
pip install pip-licenses
pip-licenses --format=markdown --with-urls --with-license-file
# im Container:
# docker compose -f compose.dev.yaml exec web sh -c "pip install pip-licenses && pip-licenses --format=markdown --with-urls"
```
