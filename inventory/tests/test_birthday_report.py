from datetime import date, datetime, timezone
from unittest.mock import patch

from django.contrib.auth.models import User
from django.test import TestCase
from django.urls import reverse

from inventory.models import Member, MemberLevel


class BirthdayReportTest(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.user = User.objects.create_user(username='birthday-report-test')
        cls.level = MemberLevel.objects.create(
            name='Birthday test', discount='1.00', points_threshold=0,
        )
        cls.member = Member.objects.create(
            name='Leap birthday', phone='10000000000',
            level=cls.level, birthday=date(2000, 2, 29),
        )

    def report_on(self, today, month=2):
        now = datetime.combine(today, datetime.min.time(), tzinfo=timezone.utc)
        with patch('inventory.views.sales.timezone.now', return_value=now):
            self.client.force_login(self.user)
            return self.client.get(reverse('birthday_members_report'), {'month': month})

    def test_leap_birthday_does_not_break_non_leap_year_report(self):
        response = self.report_on(date(2026, 2, 25))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(list(response.context['members']), [self.member])
        self.assertEqual(response.context['upcoming_birthdays'], [])

    def test_leap_birthday_after_leap_day_does_not_construct_invalid_next_year(self):
        response = self.report_on(date(2028, 3, 1))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context['upcoming_birthdays'], [])

    def test_leap_day_is_included_within_seven_days(self):
        response = self.report_on(date(2028, 2, 22))
        upcoming = response.context['upcoming_birthdays']
        self.assertEqual(len(upcoming), 1)
        self.assertEqual(upcoming[0]['birthday_date'], date(2028, 2, 29))
        self.assertEqual(upcoming[0]['days_until_birthday'], 7)

    def test_today_is_included(self):
        response = self.report_on(date(2028, 2, 29))
        self.assertEqual(response.context['upcoming_birthdays'][0]['days_until_birthday'], 0)

    def test_more_than_seven_days_is_excluded(self):
        response = self.report_on(date(2028, 2, 21))
        self.assertEqual(response.context['upcoming_birthdays'], [])

    def test_ordinary_birthday_across_year_boundary(self):
        self.member.birthday = date(2000, 1, 2)
        self.member.save(update_fields=['birthday'])
        response = self.report_on(date(2026, 12, 30), month=1)
        upcoming = response.context['upcoming_birthdays']
        self.assertEqual(upcoming[0]['birthday_date'], date(2027, 1, 2))
        self.assertEqual(upcoming[0]['days_until_birthday'], 3)
