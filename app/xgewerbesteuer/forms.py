"""Django-Formulare fuer Upload und Eingaben."""

from django import forms

from .validators import MAX_UPLOAD_SIZE_BYTES


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
