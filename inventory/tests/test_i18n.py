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
        self.assertContains(response, 'ioe')
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

    def test_report_language_switch_updates_labels_titles_and_choices(self):
        user = User.objects.create_superuser('report-language', 'report@example.com', 'password')
        self.client.force_login(user)
        for language, title, label, period in (
            ('en', 'Inventory turnover report', 'Category', 'Daily'),
            ('zh-hans', '库存周转报表', '分类', '按日'),
        ):
            with self.subTest(language=language):
                self.client.post(reverse('set_language'), {'language': language, 'next': reverse('inventory_turnover_report')})
                response = self.client.get(reverse('inventory_turnover_report'))
                self.assertContains(response, '<title>' + title + '</title>')
                self.assertEqual(str(response.context['form'].fields['category'].label), label)
                self.assertEqual(str(dict(response.context['form'].fields['period'].choices)['day']), period)

    def test_english_report_validation_and_product_form_labels(self):
        from django.utils import translation
        from inventory.forms import DateRangeForm, ProductForm
        with translation.override('en'):
            form = DateRangeForm({'start_date': '2026-10-07', 'end_date': '2026-10-01', 'period': 'day'})
            self.assertFalse(form.is_valid())
            self.assertIn('Start date must not be after end date', form.errors['start_date'])
            self.assertEqual(ProductForm().fields['category'].label, 'Category')
