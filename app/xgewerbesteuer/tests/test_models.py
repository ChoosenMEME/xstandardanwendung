"""Model-Tests fuer die XGewerbesteuer-App."""

from django.contrib.auth.models import User
from django.test import TestCase

from xgewerbesteuer.models import SavedBescheidUpload


class SavedBescheidUploadUserFieldTests(TestCase):
    def test_user_field_is_optional_foreign_key(self):
        field = SavedBescheidUpload._meta.get_field("user")

        self.assertTrue(field.null)
        self.assertIs(field.remote_field.model, User)
        self.assertEqual(field.remote_field.related_name, "saved_bescheid_uploads")

    def test_saved_upload_can_be_created_without_user(self):
        saved_upload = SavedBescheidUpload.objects.create(
            session_key="legacy-session",
            file_name="bescheid.xml",
            file_size=10,
        )

        self.assertIsNone(saved_upload.user)

    def test_saved_upload_can_be_owned_by_a_user(self):
        user = User.objects.create_user(username="nutzerin", password="Test-Passwort-1234")

        saved_upload = SavedBescheidUpload.objects.create(
            session_key="irrelevant",
            user=user,
            file_name="bescheid.xml",
            file_size=10,
        )

        self.assertEqual(user.saved_bescheid_uploads.get(), saved_upload)

    def test_deleting_user_deletes_their_saved_uploads(self):
        user = User.objects.create_user(username="nutzerin", password="Test-Passwort-1234")
        SavedBescheidUpload.objects.create(
            session_key="irrelevant",
            user=user,
            file_name="bescheid.xml",
            file_size=10,
        )

        user.delete()

        self.assertEqual(SavedBescheidUpload.objects.count(), 0)
