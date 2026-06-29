from django.conf import settings
from django.test import SimpleTestCase
from django.urls import resolve

from config.url_paths import normalize_route_prefix


class AppPathConfigurationTests(SimpleTestCase):
    def test_normalize_route_prefix_accepts_env_style_paths(self):
        self.assertEqual(normalize_route_prefix("/gewerbesteuer"), "gewerbesteuer/")
        self.assertEqual(normalize_route_prefix("gewerbesteuer"), "gewerbesteuer/")
        self.assertEqual(normalize_route_prefix(""), "")

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

    def test_help_page_is_reachable(self):
        route = "/" + normalize_route_prefix(settings.APP_PATH) + "hilfe/"

        response = self.client.get(route)

        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "xgewerbesteuer/help.html")

    def test_results_page_redirects_without_session_data(self):
        route = "/" + normalize_route_prefix(settings.APP_PATH) + "ergebnis/"

        response = self.client.get(route)

        self.assertEqual(response.status_code, 302)
