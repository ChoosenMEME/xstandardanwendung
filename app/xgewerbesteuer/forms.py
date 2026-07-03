"""Django-Formulare fuer Registrierung und Eingaben."""

from django import forms
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.models import User


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
