"""App-Konfiguration und System-Checks der XGewerbesteuer-App."""

from pathlib import Path

from django.apps import AppConfig
from django.conf import settings
from django.core.checks import Warning, register


@register()
def check_sqlite_directory_exists(app_configs, **kwargs):
    """Warnt frueh, wenn das SQLite-Verzeichnis fehlt (xgewerbesteuer.W001).

    Ausserhalb von Docker zeigt der Standardpfad /data/... ins Leere und
    Django wuerde erst beim ersten DB-Zugriff mit einem unklaren
    "unable to open database file" scheitern. Nur eine Warnung, damit
    "manage.py check" und die Testsuite (In-Memory-SQLite) nicht brechen.
    """
    database_name = settings.DATABASES.get("default", {}).get("NAME", "")

    if not database_name or database_name == ":memory:":
        return []

    database_directory = Path(database_name).parent

    if database_directory.is_dir():
        return []

    return [
        Warning(
            f"Das Verzeichnis fuer die SQLite-Datenbank fehlt: {database_directory}",
            hint=(
                "Im Docker-Betrieb legt der Entrypoint das Verzeichnis an. "
                "Ausserhalb von Docker muss SQLITE_PATH auf einen "
                "existierenden, beschreibbaren Pfad zeigen."
            ),
            id="xgewerbesteuer.W001",
        )
    ]


class XGewerbesteuerConfig(AppConfig):
    """Django-App-Konfiguration der fachlichen XGewerbesteuer-App."""

    name = 'xgewerbesteuer'
