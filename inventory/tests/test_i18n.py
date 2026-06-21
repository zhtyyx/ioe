from django.contrib.auth.models import User
from django.test import TestCase, override_settings
from django.urls import reverse


@override_settings(ALLOWED_HOSTS=['testserver'])
class LanguageSwitchTest(TestCase):
    def test_login_page_switches_to_english(self):
        response = self.client.post(
            reverse('set_language'),
            {'language': 'en', 'next': reverse('login')},
            follow=True,
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'User Login')
        self.assertContains(response, 'Username')
        self.assertContains(response, 'Inventory Management System')
        self.assertNotContains(response, '用户登录')

    def test_dashboard_uses_english_after_language_switch(self):
        User.objects.create_user(username='testuser', password='12345')
        self.client.login(username='testuser', password='12345')
        self.client.post(reverse('set_language'), {'language': 'en', 'next': reverse('index')})

        response = self.client.get(reverse('index'))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Today Sales')
        self.assertContains(response, 'Products')
        self.assertContains(response, 'Members')
        self.assertContains(response, 'Sales Trend')
        self.assertNotContains(response, '今日销售额')
