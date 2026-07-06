"""Model-Tests fuer die XGewerbesteuer-App."""

from django.contrib.auth.models import User
from django.db import IntegrityError
from django.test import TestCase

from xgewerbesteuer.models import SavedBescheidUpload


class SavedBescheidUploadUserFieldTests(TestCase):
    def make_user(self):
        return User.objects.create_user(
            username="nutzerin",
            password="Test-Passwort-1234",
        )

    def test_user_field_is_required_foreign_key(self):
        field = SavedBescheidUpload._meta.get_field("user")

        self.assertFalse(field.null)
        self.assertIs(field.remote_field.model, User)
        self.assertEqual(field.remote_field.related_name, "saved_bescheid_uploads")

    def test_saved_upload_without_user_is_rejected(self):
        with self.assertRaises(IntegrityError):
            SavedBescheidUpload.objects.create(
                file_name="bescheid.xml",
                file_size=10,
            )

    def test_saved_upload_can_be_owned_by_a_user(self):
        user = self.make_user()

        saved_upload = SavedBescheidUpload.objects.create(
            user=user,
            file_name="bescheid.xml",
            file_size=10,
        )

        self.assertEqual(user.saved_bescheid_uploads.get(), saved_upload)

    def test_deleting_user_deletes_their_saved_uploads(self):
        user = self.make_user()
        SavedBescheidUpload.objects.create(
            user=user,
            file_name="bescheid.xml",
            file_size=10,
        )

        user.delete()

        self.assertEqual(SavedBescheidUpload.objects.count(), 0)


class SavedBescheidUploadToBescheidDictTests(TestCase):
    def make_user(self):
        return User.objects.create_user(
            username="nutzerin",
            password="Test-Passwort-1234",
        )

    def test_to_bescheid_dict_maps_db_fields_to_bescheid_structure(self):
        saved_upload = SavedBescheidUpload.objects.create(
            user=self.make_user(),
            file_name="bescheid.xml",
            file_size=10,
            municipality="Stadt Musterhausen",
            tax_period="2023",
            amount_due="630.00",
            payment_type="Nachzahlung",
            trade_tax_assessment_amount="150.00",
            assessment_rate="420",
            due_dates="2025-02-15",
            advance_payments=[{"amount": "147.00"}],
            summary_items=[{"label": "Zahlbetrag", "value": "630.00"}],
            result_data={"calculation_explanation": {"can_calculate": True}},
        )

        bescheid = saved_upload.to_bescheid_dict()

        self.assertEqual(bescheid["file_name"], "bescheid.xml")
        self.assertEqual(bescheid["municipality"], "Stadt Musterhausen")
        self.assertEqual(bescheid["tax_period"], "2023")
        self.assertEqual(bescheid["amount_due"], "630.00")
        self.assertEqual(bescheid["payment_classification"]["type"], "Nachzahlung")
        self.assertEqual(
            bescheid["calculation_explanation"],
            {"can_calculate": True},
        )

    def test_to_bescheid_dict_normalizes_empty_values_to_none(self):
        saved_upload = SavedBescheidUpload.objects.create(
            user=self.make_user(),
            file_name="bescheid.xml",
            file_size=10,
        )

        bescheid = saved_upload.to_bescheid_dict()

        self.assertIsNone(bescheid["municipality"])
        self.assertIsNone(bescheid["tax_period"])
        self.assertIsNone(bescheid["amount_due"])
        self.assertIsNone(bescheid["due_dates"])
        self.assertEqual(bescheid["advance_payments"], [])
        self.assertEqual(bescheid["summary_items"], [])
        self.assertEqual(bescheid["calculation_explanation"], {})
        self.assertIsNone(bescheid["payment_classification"]["type"])
