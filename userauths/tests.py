from unittest.mock import Mock

from django.test import SimpleTestCase
from django.urls import reverse

from userauths.redirects import redirect_after_login


class RedirectAfterLoginTests(SimpleTestCase):
    def test_absolute_url_next_does_not_open_redirect(self):
        request = Mock()
        request.get_host = Mock(return_value="testserver")
        request.is_secure = Mock(return_value=False)
        request.build_absolute_uri = lambda path: f"http://testserver{path}"

        response = redirect_after_login(
            request, "https://evil.example/phish", fallback="store:index"
        )
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.headers["Location"], reverse("store:index"))

    def test_named_route_next_works(self):
        request = Mock()
        request.get_host = Mock(return_value="testserver")
        request.is_secure = Mock(return_value=False)
        request.build_absolute_uri = lambda path: f"http://testserver{path}"

        response = redirect_after_login(request, "store:cart", fallback="store:index")
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.headers["Location"], reverse("store:cart"))
