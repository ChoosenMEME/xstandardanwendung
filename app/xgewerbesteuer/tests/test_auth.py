"""Tests fuer Login, Logout, Registrierung und Passwort-Reset."""

from django.contrib.auth.models import User
from django.core import mail
from django.test import TestCase, override_settings
from django.urls import reverse


# LOGIN_ENABLED haengt in den Settings von DEBUG bzw. EMAIL_HOST ab. Die
# Login-Tests setzen den Wert explizit, damit die Suite unabhaengig von
# Umgebungsvariablen laeuft.
@override_settings(LOGIN_ENABLED=True)
class LoginTests(TestCase):
    def create_user(self, username="nutzerin", password="Test-Passwort-1234"):
        return User.objects.create_user(username=username, password=password)

    def test_login_page_is_reachable(self):
        response = self.client.get(reverse("login"))

        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "registration/login.html")

    def test_login_with_valid_credentials_authenticates_and_redirects(self):
        self.create_user()

        response = self.client.post(
            reverse("login"),
            data={"username": "nutzerin", "password": "Test-Passwort-1234"},
        )

        self.assertEqual(response.status_code, 302)
        self.assertTrue(self.client.session.get("_auth_user_id"))

    def test_login_with_invalid_credentials_shows_generic_error(self):
        self.create_user()

        response = self.client.post(
            reverse("login"),
            data={"username": "nutzerin", "password": "falsches-passwort"},
        )

        self.assertEqual(response.status_code, 200)
        self.assertFalse(self.client.session.get("_auth_user_id"))
        self.assertTrue(response.context["form"].errors)

    def test_login_error_does_not_reveal_whether_username_exists(self):
        self.create_user()

        response_unknown_user = self.client.post(
            reverse("login"),
            data={"username": "unbekannt", "password": "irgendein-passwort"},
        )
        response_wrong_password = self.client.post(
            reverse("login"),
            data={"username": "nutzerin", "password": "falsches-passwort"},
        )

        self.assertEqual(
            response_unknown_user.context["form"].errors,
            response_wrong_password.context["form"].errors,
        )

    def test_logout_ends_session(self):
        self.create_user()
        self.client.login(username="nutzerin", password="Test-Passwort-1234")

        response = self.client.post(reverse("logout"))

        self.assertEqual(response.status_code, 302)
        self.assertFalse(self.client.session.get("_auth_user_id"))


@override_settings(LOGIN_ENABLED=True)
class SignupTests(TestCase):
    def test_signup_page_is_reachable(self):
        response = self.client.get(reverse("xgewerbesteuer_signup"))

        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "registration/signup.html")

    def test_signup_creates_user_and_logs_in(self):
        response = self.client.post(
            reverse("xgewerbesteuer_signup"),
            data={
                "username": "neue-nutzerin",
                "email": "neue-nutzerin@example.com",
                "password1": "Sicheres-Passwort-42",
                "password2": "Sicheres-Passwort-42",
            },
            follow=True,
        )

        self.assertEqual(response.status_code, 200)
        user = User.objects.filter(username="neue-nutzerin").first()
        self.assertIsNotNone(user)
        self.assertEqual(user.email, "neue-nutzerin@example.com")
        self.assertTrue(self.client.session.get("_auth_user_id"))

    def test_signup_with_mismatched_passwords_shows_error_and_creates_no_user(self):
        response = self.client.post(
            reverse("xgewerbesteuer_signup"),
            data={
                "username": "neue-nutzerin",
                "email": "neue-nutzerin@example.com",
                "password1": "Sicheres-Passwort-42",
                "password2": "anderes-passwort",
            },
        )

        self.assertEqual(response.status_code, 200)
        self.assertFalse(User.objects.filter(username="neue-nutzerin").exists())

    def test_signup_without_email_shows_error_and_creates_no_user(self):
        response = self.client.post(
            reverse("xgewerbesteuer_signup"),
            data={
                "username": "neue-nutzerin",
                "password1": "Sicheres-Passwort-42",
                "password2": "Sicheres-Passwort-42",
            },
        )

        self.assertEqual(response.status_code, 200)
        self.assertFalse(User.objects.filter(username="neue-nutzerin").exists())

    def test_signup_password_without_uppercase_letter_is_rejected(self):
        response = self.client.post(
            reverse("xgewerbesteuer_signup"),
            data={
                "username": "komplexitaet-nutzerin",
                "email": "komplexitaet@example.com",
                "password1": "kein-grossbuchstabe1",
                "password2": "kein-grossbuchstabe1",
            },
        )

        self.assertEqual(response.status_code, 200)
        self.assertFalse(User.objects.filter(username="komplexitaet-nutzerin").exists())

    def test_signup_password_without_lowercase_letter_is_rejected(self):
        response = self.client.post(
            reverse("xgewerbesteuer_signup"),
            data={
                "username": "komplexitaet-nutzerin",
                "email": "komplexitaet@example.com",
                "password1": "KEIN-KLEINBUCHSTABE1",
                "password2": "KEIN-KLEINBUCHSTABE1",
            },
        )

        self.assertEqual(response.status_code, 200)
        self.assertFalse(User.objects.filter(username="komplexitaet-nutzerin").exists())

    def test_signup_password_without_digit_is_rejected(self):
        response = self.client.post(
            reverse("xgewerbesteuer_signup"),
            data={
                "username": "komplexitaet-nutzerin",
                "email": "komplexitaet@example.com",
                "password1": "Keine-Zahl-Enthalten",
                "password2": "Keine-Zahl-Enthalten",
            },
        )

        self.assertEqual(response.status_code, 200)
        self.assertFalse(User.objects.filter(username="komplexitaet-nutzerin").exists())

    def test_signup_password_without_special_character_is_rejected(self):
        response = self.client.post(
            reverse("xgewerbesteuer_signup"),
            data={
                "username": "komplexitaet-nutzerin",
                "email": "komplexitaet@example.com",
                "password1": "KeinSonderzeichen1",
                "password2": "KeinSonderzeichen1",
            },
        )

        self.assertEqual(response.status_code, 200)
        self.assertFalse(User.objects.filter(username="komplexitaet-nutzerin").exists())

    def test_signup_password_containing_username_is_rejected(self):
        response = self.client.post(
            reverse("xgewerbesteuer_signup"),
            data={
                "username": "geheimnis",
                "email": "andere-adresse@example.com",
                "password1": "Geheimnis-Passwort1!",
                "password2": "Geheimnis-Passwort1!",
            },
        )

        self.assertEqual(response.status_code, 200)
        self.assertFalse(User.objects.filter(username="geheimnis").exists())

    def test_signup_with_already_used_email_is_rejected(self):
        """Regression fuer #322: keine zwei Konten mit derselben Adresse."""
        User.objects.create_user(
            username="bestehende-nutzerin",
            email="doppelt@example.com",
            password="Test-Passwort-1234",
        )

        response = self.client.post(
            reverse("xgewerbesteuer_signup"),
            data={
                "username": "neue-nutzerin",
                "email": "doppelt@example.com",
                "password1": "Sicheres-Passwort-42",
                "password2": "Sicheres-Passwort-42",
            },
        )

        self.assertEqual(response.status_code, 200)
        self.assertFalse(User.objects.filter(username="neue-nutzerin").exists())
        self.assertContains(response, "existiert bereits ein Konto")

    def test_signup_with_differently_cased_duplicate_email_is_rejected(self):
        User.objects.create_user(
            username="bestehende-nutzerin",
            email="doppelt@example.com",
            password="Test-Passwort-1234",
        )

        response = self.client.post(
            reverse("xgewerbesteuer_signup"),
            data={
                "username": "neue-nutzerin",
                "email": "Doppelt@Example.com",
                "password1": "Sicheres-Passwort-42",
                "password2": "Sicheres-Passwort-42",
            },
        )

        self.assertEqual(response.status_code, 200)
        self.assertFalse(User.objects.filter(username="neue-nutzerin").exists())
        self.assertContains(response, "existiert bereits ein Konto")

    def test_signup_password_containing_email_is_rejected(self):
        response = self.client.post(
            reverse("xgewerbesteuer_signup"),
            data={
                "username": "andere-nutzerin",
                "email": "vertraulich@example.com",
                "password1": "Vertraulich-Passwort1!",
                "password2": "Vertraulich-Passwort1!",
            },
        )

        self.assertEqual(response.status_code, 200)
        self.assertFalse(User.objects.filter(username="andere-nutzerin").exists())


@override_settings(LOGIN_ENABLED=True)
class PasswordResetTests(TestCase):
    def test_password_reset_form_is_reachable(self):
        response = self.client.get(reverse("password_reset"))

        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "registration/password_reset_form.html")

    def test_password_reset_request_for_unknown_email_still_shows_success_page(self):
        response = self.client.post(
            reverse("password_reset"),
            data={"email": "unbekannt@example.com"},
            follow=True,
        )

        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "registration/password_reset_done.html")
        self.assertEqual(len(mail.outbox), 0)

    def test_password_reset_request_for_known_email_sends_mail(self):
        User.objects.create_user(
            username="nutzerin",
            email="nutzerin@example.com",
            password="Test-Passwort-1234",
        )

        response = self.client.post(
            reverse("password_reset"),
            data={"email": "nutzerin@example.com"},
            follow=True,
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(mail.outbox), 1)
        self.assertNotIn("Traceback", mail.outbox[0].body)


@override_settings(LOGIN_ENABLED=True)
class ProtectedSavedUploadViewsRequireLoginTests(TestCase):
    def test_load_saved_redirects_anonymous_to_login(self):
        response = self.client.post(
            reverse("xgewerbesteuer_load_saved"),
            data={"saved_upload_id": "1"},
        )

        self.assertEqual(response.status_code, 302)
        self.assertIn(reverse("login"), response.url)

    def test_delete_saved_redirects_anonymous_to_login(self):
        response = self.client.post(
            reverse("xgewerbesteuer_delete_saved"),
            data={"saved_upload_id": "1"},
        )

        self.assertEqual(response.status_code, 302)
        self.assertIn(reverse("login"), response.url)


class PublicPagesRemainAccessibleWithoutLoginTests(TestCase):
    """Regressionstests: das Login-Feature darf oeffentliche Seiten nicht sperren."""

    def test_upload_page_is_reachable_without_login(self):
        response = self.client.get(reverse("xgewerbesteuer_upload"))

        self.assertEqual(response.status_code, 200)

    def test_demo_route_resolves_without_login(self):
        response = self.client.get(reverse("xgewerbesteuer_demo"), follow=True)

        self.assertEqual(response.status_code, 200)

    def test_help_page_is_reachable_without_login(self):
        response = self.client.get(reverse("xgewerbesteuer_help"))

        self.assertEqual(response.status_code, 200)

    def test_dashboard_is_reachable_without_login(self):
        response = self.client.get(reverse("xgewerbesteuer_dashboard"))

        self.assertEqual(response.status_code, 200)


@override_settings(LOGIN_ENABLED=False)
class LoginDisabledWithoutEmailServerTests(TestCase):
    """Ohne konfigurierten Mailserver ist Login/Registrierung gesperrt."""

    def test_login_page_returns_not_found(self):
        response = self.client.get(reverse("login"))

        self.assertEqual(response.status_code, 404)

    def test_signup_page_returns_not_found(self):
        response = self.client.get(reverse("xgewerbesteuer_signup"))

        self.assertEqual(response.status_code, 404)

    def test_password_reset_page_returns_not_found(self):
        response = self.client.get(reverse("password_reset"))

        self.assertEqual(response.status_code, 404)

    def test_load_saved_returns_not_found(self):
        response = self.client.post(
            reverse("xgewerbesteuer_load_saved"),
            data={"saved_upload_id": "1"},
        )

        self.assertEqual(response.status_code, 404)

    def test_delete_saved_returns_not_found(self):
        response = self.client.post(
            reverse("xgewerbesteuer_delete_saved"),
            data={"saved_upload_id": "1"},
        )

        self.assertEqual(response.status_code, 404)

    def test_dashboard_hides_login_and_signup_links(self):
        response = self.client.get(reverse("xgewerbesteuer_dashboard"))

        self.assertEqual(response.status_code, 200)
        self.assertNotContains(response, reverse("login"))
        self.assertNotContains(response, reverse("xgewerbesteuer_signup"))
