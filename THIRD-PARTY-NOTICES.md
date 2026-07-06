# Drittanbieter-Lizenzen (Third-Party Notices)

Der **GewSt-Bescheidassistent** selbst steht unter der MIT-Lizenz (siehe [`LICENSE`](LICENSE)).
Er nutzt bzw. liefert die folgenden Komponenten Dritter mit. Die jeweiligen Lizenzen und
Urheberrechtshinweise gelten unverändert weiter.

## Übersicht

| Komponente | Version | Lizenz (SPDX) | Einbindung |
| --- | --- | --- | --- |
| [Python](https://www.python.org/) | 3.12 | `PSF-2.0` (Python Software Foundation License) | Laufzeit / Basis-Image |
| [Django](https://www.djangoproject.com/) | 6.0.x | `BSD-3-Clause` | Abhängigkeit, im Docker-Image |
| [lxml](https://lxml.de/) | 5.x–6.x | `BSD-3-Clause` (siehe auch mitgelieferte `LICENSES.txt` des Pakets) | Abhängigkeit (`requirements.txt`), im Docker-Image |
| [defusedxml](https://github.com/tiran/defusedxml) | latest | `PSF-2.0` (Python Software Foundation License) | Abhängigkeit (`requirements.txt`), im Docker-Image |
| [reportlab](https://www.reportlab.com/) | 4.x | `BSD-3-Clause`-artige ReportLab Software License | Abhängigkeit (`requirements.txt`), im Docker-Image |
| [gunicorn](https://gunicorn.org/) | 23.x | `MIT` | Abhängigkeit (`requirements.txt`), im Docker-Image |
| [WhiteNoise](https://whitenoise.readthedocs.io/) | 6.x | `MIT` | Abhängigkeit (`requirements.txt`), im Docker-Image |
| [KERN UX (`@kern-ux/native`)](https://www.kern-ux.de/) | 2.6.2 | EUPL 1.2 | lokal mitgeliefert (`app/static/vendor/kern/`) |
| [Fira Sans](https://github.com/mozilla/Fira) | via `@kern-ux/native` 2.6.2 | `OFL-1.1` (SIL Open Font License) | lokal mitgeliefert (`app/static/vendor/kern/fonts/`) |

## Hinweise und Urheberrechte

- **Python** – Copyright © Python Software Foundation. Lizenz: PSF License Agreement,
  <https://docs.python.org/3/license.html>.
- **Django** – Copyright © Django Software Foundation and individual contributors.
  BSD-3-Clause, <https://github.com/django/django/blob/main/LICENSE>.
- **lxml** – Copyright © lxml-Entwicklungsteam (u. a. Infrae, Stefan Behnel). BSD-artige
  Lizenz, siehe <https://lxml.de/index.html#license>.
- **defusedxml** – Copyright © Christian Heimes. Python Software Foundation License,
  siehe <https://github.com/tiran/defusedxml/blob/main/LICENSE>.
- **reportlab** – Copyright © ReportLab Europe Ltd. ReportLab Software License
  (BSD-artig), siehe <https://www.reportlab.com/dist/rl-toolkit/licence.txt>.
- **gunicorn** – Copyright © Benoît Chesneau und Contributors. MIT-Lizenz,
  siehe <https://github.com/benoitc/gunicorn/blob/master/LICENSE>.
- **WhiteNoise** – Copyright © David Evans und Contributors. MIT-Lizenz,
  siehe <https://github.com/evansd/whitenoise/blob/main/LICENSE>.
- **KERN UX** – UI-/Designsystem; Version 2.6.2 wird lokal aus
  `app/static/vendor/kern/` ausgeliefert (kein CDN-Zugriff aus Datenschutz- und
  Verfügbarkeitsgründen). Lizenz: EUROPÄISCHE UNION PUBLIC LICENCE v. 1.2
- **Fira Sans** – Copyright © The Mozilla Foundation and Telefonica S.A.
  SIL Open Font License 1.1, siehe
  <https://github.com/mozilla/Fira/blob/master/LICENSE>. Die Schriftdateien
  stammen aus dem Paket `@kern-ux/native` 2.6.2 und liegen unter
  `app/static/vendor/kern/fonts/`.
