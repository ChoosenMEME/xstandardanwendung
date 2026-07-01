"""Django-Formulare fuer Upload und Eingaben."""

from django import forms
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.models import User

from .validators import MAX_UPLOAD_SIZE_BYTES


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


class BescheidUploadForm(forms.Form):
    bescheide = forms.FileField(
        label="Gewerbesteuerbescheide auswählen",
        required=True,
    )
    save_upload = forms.BooleanField(
        label="Auswertung dieses Uploads speichern",
        required=False,
    )

    def clean_bescheide(self):
        uploaded_file = self.cleaned_data.get("bescheide")

        if not uploaded_file:
            return uploaded_file

        if not uploaded_file.name.lower().endswith(".xml"):
            raise forms.ValidationError(
                "Die hochgeladene Datei muss eine XML-Datei sein."
            )

        if uploaded_file.size > MAX_UPLOAD_SIZE_BYTES:
            raise forms.ValidationError(
                "Die hochgeladene Datei ist zu groß."
            )

        return uploaded_file
