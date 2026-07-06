"""Versendet eine Test-E-Mail mit der konfigurierten Django-Mailanbindung."""

from django.conf import settings
from django.core.exceptions import ValidationError
from django.core.mail import send_mail
from django.core.management.base import BaseCommand, CommandError
from django.core.validators import validate_email


class Command(BaseCommand):
    help = "Versendet eine Test-E-Mail ueber die konfigurierte Mailanbindung."

    def add_arguments(self, parser):
        parser.add_argument("recipient", help="Empfaengeradresse fuer die Test-E-Mail")

    def handle(self, *args, **options):
        recipient = options["recipient"]
        try:
            validate_email(recipient)
        except ValidationError as exc:
            raise CommandError("Die Empfaengeradresse ist ungueltig.") from exc

        try:
            sent = send_mail(
                "XGewerbesteuer Test-E-Mail",
                "Die E-Mail-Anbindung der XGewerbesteuer-Anwendung funktioniert.",
                settings.DEFAULT_FROM_EMAIL,
                [recipient],
                fail_silently=False,
            )
        except Exception as exc:
            raise CommandError(
                f"Test-E-Mail konnte nicht versendet werden ({type(exc).__name__})."
            ) from exc

        if sent != 1:
            raise CommandError("Test-E-Mail wurde nicht versendet.")

        self.stdout.write(self.style.SUCCESS("Test-E-Mail erfolgreich versendet."))
