from django.test import Client, SimpleTestCase, override_settings
from django.urls import reverse


@override_settings(
    ALLOWED_HOSTS=['testserver'],
    SESSION_ENGINE='django.contrib.sessions.backends.signed_cookies',
)
class LogoutRedirectTest(SimpleTestCase):
    def test_logout_redirects_to_absolute_login_path(self):
        response = Client().post(reverse('logout'))

        self.assertRedirects(
            response,
            reverse('login'),
            fetch_redirect_response=False,
        )
