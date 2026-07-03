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
        email = self.cleaned_data["email"]
        # NoUserInfoFragmentValidator prueft self.instance.email waehrend
        # der Passwort-Validierung, die vor save() laeuft.
        self.instance.email = email
        return email

    def save(self, commit=True):
        user = super().save(commit=False)
        if commit:
            user.save()
        return user
