from django.conf import settings
from django.test import SimpleTestCase
from django.urls import resolve

from config.url_paths import normalize_route_prefix


class AppPathConfigurationTests(SimpleTestCase):
    def test_normalize_route_prefix_accepts_env_style_paths(self):
        self.assertEqual(normalize_route_prefix("/gewerbesteuer"), "gewerbesteuer/")
        self.assertEqual(normalize_route_prefix("gewerbesteuer"), "gewerbesteuer/")
        self.assertEqual(normalize_route_prefix(""), "")

    def test_configured_app_path_routes_to_xgewerbesteuer_view(self):
        route = "/" + normalize_route_prefix(settings.APP_PATH)

        match = resolve(route)

        self.assertEqual(match.url_name, "xgewerbesteuer_default")
