"""Django-Formulare fuer Registrierung und Eingaben."""

import logging

from django import forms
from django.contrib.auth.forms import PasswordResetForm, UserCreationForm
from django.contrib.auth.models import User
from django.core.mail import EmailMultiAlternatives
from django.template import loader

logger = logging.getLogger(__name__)


class LoggingPasswordResetForm(PasswordResetForm):
    """Protokolliert den Mailversand ohne personenbezogene Daten."""

    def send_mail(
        self,
        subject_template_name,
        email_template_name,
        context,
        from_email,
        to_email,
        html_email_template_name=None,
    ):
        subject = "".join(
            loader.render_to_string(subject_template_name, context).splitlines()
        )
        body = loader.render_to_string(email_template_name, context)
        message = EmailMultiAlternatives(subject, body, from_email, [to_email])
        if html_email_template_name:
            message.attach_alternative(
                loader.render_to_string(html_email_template_name, context),
                "text/html",
            )

        try:
            message.send()
        except Exception as exc:
            # SMTP-Fehler koennen Empfaengeradressen enthalten; nur den Typ loggen.
            logger.error(
                "Passwort-Reset-Mail konnte nicht versendet werden (%s).",
                type(exc).__name__,
            )
        else:
            logger.info("Passwort-Reset-Mail wurde versendet.")


class SignupForm(UserCreationForm):
    email = forms.EmailField(
        label="E-Mail-Adresse",
        required=True,
        help_text="Wird für den Passwort-Reset benötigt.",
    )

    class Meta(UserCreationForm.Meta):
        model = User
        fields = ("username", "email")

    def clean_email(self):
        email = self.cleaned_data["email"].strip()

        # Djangos User-Modell erzwingt keine eindeutige E-Mail-Adresse. Ohne
        # diese Pruefung wuerde der Passwort-Reset mehrdeutig, weil fuer jede
        # Uebereinstimmung eine eigene Reset-Mail verschickt wird. Der
        # Vergleich ist case-insensitiv, damit "Foo@..." und "foo@..." nicht
        # als verschiedene Adressen durchgehen.
        if User.objects.filter(email__iexact=email).exists():
            raise forms.ValidationError(
                "Für diese E-Mail-Adresse existiert bereits ein Konto."
            )

        # NoUserInfoFragmentValidator prueft self.instance.email waehrend
        # der Passwort-Validierung, die vor save() laeuft.
        self.instance.email = email
        return email

    def save(self, commit=True):
        user = super().save(commit=False)
        if commit:
            user.save()
        return user
