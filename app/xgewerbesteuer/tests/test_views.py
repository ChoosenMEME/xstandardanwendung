from django.conf import settings
from django.test import SimpleTestCase
from django.urls import resolve

from config.settings import build_static_url
from config.url_paths import normalize_route_prefix


class AppPathConfigurationTests(SimpleTestCase):
    def test_normalize_route_prefix_accepts_env_style_paths(self):
        self.assertEqual(normalize_route_prefix("/gewerbesteuer"), "gewerbesteuer/")
        self.assertEqual(normalize_route_prefix("gewerbesteuer"), "gewerbesteuer/")
        self.assertEqual(normalize_route_prefix(""), "")

    def test_static_url_without_app_path_stays_default(self):
        self.assertEqual(build_static_url(""), "/static/")

    def test_static_url_uses_normalized_app_path_prefix(self):
        self.assertEqual(build_static_url("gewerbesteuer"), "/gewerbesteuer/static/")
        self.assertEqual(build_static_url("/gewerbesteuer/"), "/gewerbesteuer/static/")

    def test_configured_app_path_routes_to_dashboard_view(self):
        route = "/" + normalize_route_prefix(settings.APP_PATH)

        match = resolve(route)

        self.assertEqual(match.url_name, "xgewerbesteuer_dashboard")

    def test_configured_app_path_renders_dashboard_view(self):
        route = "/" + normalize_route_prefix(settings.APP_PATH)

        response = self.client.get(route)

        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "xgewerbesteuer/dashboard.html")

    def test_configured_app_path_routes_to_healthz_view(self):
        route = "/" + normalize_route_prefix(settings.APP_PATH) + "healthz/"

        match = resolve(route)

        self.assertEqual(match.url_name, "healthz")

    def test_healthz_endpoint_returns_ok_status(self):
        route = "/" + normalize_route_prefix(settings.APP_PATH) + "healthz/"

        response = self.client.get(route)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), {"status": "ok"})

    def test_upload_page_is_reachable(self):
        route = "/" + normalize_route_prefix(settings.APP_PATH) + "upload/"

        response = self.client.get(route)

        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "xgewerbesteuer/upload.html")

    def test_upload_page_offers_drag_and_drop_file_selection(self):
        route = "/" + normalize_route_prefix(settings.APP_PATH) + "upload/"

        response = self.client.get(route)

        self.assertContains(response, 'data-upload-dropzone')
        self.assertContains(response, 'data-upload-file-input')
        self.assertContains(response, 'data-upload-file-list')
        self.assertContains(response, 'data-empty-text="Noch keine Datei ausgewählt."')
        self.assertContains(response, 'data-selected-text="Ausgewählt"')
        self.assertContains(response, "Nur XML-Dateien können hier abgelegt werden.")
        self.assertContains(response, "filter(isXmlFile)")
        self.assertContains(response, "new DataTransfer()")
        self.assertContains(response, 'name="bescheide"')
        self.assertContains(response, "multiple")
        self.assertContains(
            response,
            'aria-labelledby="bescheide-label upload-dropzone-title"',
        )
        self.assertNotContains(response, "ausgewaehlt")
        self.assertNotContains(response, 'role="button"')
        self.assertNotContains(response, 'tabindex="0"')

    def test_demo_page_route_redirects_to_results_or_upload(self):
        route = "/" + normalize_route_prefix(settings.APP_PATH) + "demo/"

        match = resolve(route)

        self.assertEqual(match.url_name, "xgewerbesteuer_demo")

    def test_help_page_is_reachable(self):
        route = "/" + normalize_route_prefix(settings.APP_PATH) + "hilfe/"

        response = self.client.get(route)

        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "xgewerbesteuer/help.html")

    def test_results_page_redirects_without_session_data(self):
        route = "/" + normalize_route_prefix(settings.APP_PATH) + "ergebnis/"

        response = self.client.get(route)

        self.assertEqual(response.status_code, 302)
