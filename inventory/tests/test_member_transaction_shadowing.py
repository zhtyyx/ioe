from decimal import Decimal
from unittest.mock import patch

from django.contrib.auth.models import User
from django.test import TestCase
from django.urls import reverse

from inventory.models import Member, MemberLevel, MemberTransaction, RechargeRecord
from inventory.services.member_service import apply_member_balance_change


class MemberBalanceTransactionTests(TestCase):
    @staticmethod
    def update_balance_then_fail(*args, **kwargs):
        apply_member_balance_change(*args, **kwargs)
        raise RuntimeError("synthetic failure after balance update")

    def setUp(self):
        self.user = User.objects.create_user(username="operator", password="secret")
        level = MemberLevel.objects.create(
            name="Standard", discount=Decimal("1.00"), points_threshold=0
        )
        self.member = Member.objects.create(
            name="Synthetic member",
            phone="5550000001",
            level=level,
            balance=Decimal("10.00"),
        )
        self.client.login(username="operator", password="secret")

    def test_recharge_updates_balance_and_creates_ledger_entry(self):
        response = self.client.post(
            reverse("member_recharge", args=[self.member.pk]),
            {
                "amount": "5.25",
                "actual_amount": "5.25",
                "payment_method": "cash",
                "remark": "synthetic recharge",
            },
        )

        self.assertRedirects(response, reverse("member_detail", args=[self.member.pk]))
        self.member.refresh_from_db()
        self.assertEqual(self.member.balance, Decimal("15.25"))
        self.assertTrue(self.member.is_recharged)
        self.assertEqual(RechargeRecord.objects.count(), 1)
        self.assertEqual(
            list(MemberTransaction.objects.values_list("transaction_type", flat=True)),
            ["RECHARGE"],
        )

    def test_balance_adjust_updates_balance_and_creates_ledger_entry(self):
        response = self.client.post(
            reverse("member_balance_adjust", args=[self.member.pk]),
            {"balance_change": "-2.50", "description": "synthetic adjustment"},
        )

        self.assertRedirects(response, reverse("member_detail", args=[self.member.pk]))
        self.member.refresh_from_db()
        self.assertEqual(self.member.balance, Decimal("7.50"))
        transaction = MemberTransaction.objects.get()
        self.assertEqual(transaction.transaction_type, "BALANCE_ADJUST")
        self.assertEqual(transaction.balance_change, Decimal("-2.50"))

    def test_recharge_rolls_back_ledger_and_balance_on_failure(self):
        with patch(
            "inventory.views.member.member_service.apply_member_balance_change",
            side_effect=self.update_balance_then_fail,
        ):
            with self.assertRaises(RuntimeError):
                self.client.post(
                    reverse("member_recharge", args=[self.member.pk]),
                    {
                        "amount": "5.25",
                        "actual_amount": "5.25",
                        "payment_method": "cash",
                    },
                )

        self.member.refresh_from_db()
        self.assertEqual(self.member.balance, Decimal("10.00"))
        self.assertFalse(self.member.is_recharged)
        self.assertEqual(RechargeRecord.objects.count(), 0)
        self.assertEqual(MemberTransaction.objects.count(), 0)

    def test_balance_adjust_rolls_back_ledger_and_balance_on_failure(self):
        with patch(
            "inventory.views.member.member_service.apply_member_balance_change",
            side_effect=self.update_balance_then_fail,
        ):
            with self.assertRaises(RuntimeError):
                self.client.post(
                    reverse("member_balance_adjust", args=[self.member.pk]),
                    {"balance_change": "2.50", "description": "synthetic failure"},
                )

        self.member.refresh_from_db()
        self.assertEqual(self.member.balance, Decimal("10.00"))
        self.assertEqual(MemberTransaction.objects.count(), 0)
