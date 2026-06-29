"""Django-Formulare fuer Upload und Eingaben."""

from django import forms

from .validators import MAX_UPLOAD_SIZE_BYTES


class BescheidUploadForm(forms.Form):
    bescheid = forms.FileField(
        label="Aktuellen XGewerbesteuer-Bescheid auswählen (Pflicht)",
        required=True,
    )
    vorjahresbescheid = forms.FileField(
        label="Vorjahresbescheid optional auswählen",
        required=False,
    )
    vergleichsbescheide = forms.FileField(
        label="Mehrere Bescheide für den Vergleich optional auswählen",
        required=False,
    )
    save_upload = forms.BooleanField(
        label="Auswertung dieses Uploads speichern",
        required=False,
    )

    def clean_bescheid(self):
        uploaded_file = self.cleaned_data.get("bescheid")

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
