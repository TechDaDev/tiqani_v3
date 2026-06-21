"""
Tests for payment fixture determinism and reset idempotency.

These tests prove that:
- The seed command creates expected payment state.
- Two consecutive resets produce identical counts/IDs.
- A normal rerun (no --reset) creates no duplicates.
- Mutable contracts reset to clean unfunded state.
- Read-only fixtures (funded, pending) are recreated correctly.
"""

from django.test import TestCase
from django.core.management import call_command
from io import StringIO
from wallet.models import PaymentIntent, WalletTransaction
from contract.models import Contract


class PaymentFixtureResetTest(TestCase):
    """Verify payment fixture reset and idempotency."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        # Run reset+seed once so counts are available
        out = StringIO()
        call_command("seed_e2e_fixtures", "--reset", stdout=out)
        cls.reset_output = out.getvalue()

    def _get_pending_intents(self):
        return PaymentIntent.objects.filter(status=PaymentIntent.Status.PENDING)

    def _get_paid_intents(self):
        return PaymentIntent.objects.filter(status=PaymentIntent.Status.PAID)

    def _get_failed_intents(self):
        return PaymentIntent.objects.filter(status=PaymentIntent.Status.FAILED)

    def _get_all_intents(self):
        return PaymentIntent.objects.all()

    def _get_all_transactions(self):
        return WalletTransaction.objects.all()

    # ── 1. Count correctness ──────────────────────────────────────

    def test_fixture_contract_count(self):
        """There should be 11 total payment-related contracts (8 new + 3 legacy)."""
        from uuid import UUID
        contract_ids = [
            UUID("f872e161-f2a2-5925-a4d1-de4cc9d208d2"),  # success
            UUID("3430c009-26a6-573e-8725-836aa2426316"),  # failure
            UUID("92336219-bdc8-5cb6-bc95-b885381f835b"),  # double-click
            UUID("89a7e54e-3130-506f-9ee3-5c27c70e50eb"),  # duplicate-confirm
            UUID("3db4c549-571d-5973-818b-353b31f216b5"),  # pending-view
            UUID("36e7bd72-780f-527e-a888-93107709dd99"),  # funded-view
            UUID("fe961321-eb46-58a5-a322-f03553646b00"),  # logout
            UUID("d1dd0923-88bb-5244-8b91-74e97c6ed451"),  # localization
            UUID("85052d24-3508-5106-a685-4747e48aeb44"),  # responsive
            UUID("3c6503e0-df13-588b-9d77-a3e1dfc23749"),  # legacy unfunded
            UUID("02db5487-b48f-5eb9-8599-7cd477fea0e3"),  # legacy funded
        ]
        for cid in contract_ids:
            self.assertTrue(
                Contract.objects.filter(pk=cid).exists(),
                f"Expected contract {cid} not found",
            )

    def test_fixture_pending_intent_count(self):
        """Should have exactly 1 pending intent (pending-view contract)."""
        self.assertEqual(self._get_pending_intents().count(), 1)

    def test_fixture_paid_intent_count(self):
        """Should have exactly 3 paid intents (funded-view + legacy funded + execution activation)."""
        self.assertEqual(self._get_paid_intents().count(), 3)

    def test_fixture_failed_intent_count(self):
        """Should have exactly 1 failed intent (failure contract)."""
        self.assertEqual(self._get_failed_intents().count(), 1)

    def test_all_intents_total(self):
        """5 total: 1 pending + 3 paid + 1 failed."""
        self.assertEqual(self._get_all_intents().count(), 5)

    def test_wallet_transaction_count(self):
        """Exactly 2 wallet transactions (funded-view deposit + escrow)."""
        self.assertEqual(self._get_all_transactions().count(), 2)

    # ── 2. Mutable contract state ─────────────────────────────────
    # These contracts should have NO intent and 0 escrow after reset.

    def test_success_contract_is_unfunded(self):
        c = Contract.objects.get(pk="f872e161-f2a2-5925-a4d1-de4cc9d208d2")
        self.assertEqual(c.escrow_amount, 0)
        self.assertFalse(
            PaymentIntent.objects.filter(contract=c).exists(),
            "Success contract should have no intents after reset",
        )

    def test_failure_contract_has_failed_intent(self):
        c = Contract.objects.get(pk="3430c009-26a6-573e-8725-836aa2426316")
        self.assertEqual(c.escrow_amount, 0)
        failed = self._get_failed_intents().filter(contract=c)
        self.assertEqual(failed.count(), 1)

    def test_double_click_contract_is_unfunded(self):
        c = Contract.objects.get(pk="92336219-bdc8-5cb6-bc95-b885381f835b")
        self.assertEqual(c.escrow_amount, 0)
        self.assertFalse(PaymentIntent.objects.filter(contract=c).exists())

    def test_duplicate_confirm_contract_is_unfunded(self):
        c = Contract.objects.get(pk="89a7e54e-3130-506f-9ee3-5c27c70e50eb")
        self.assertEqual(c.escrow_amount, 0)
        self.assertFalse(PaymentIntent.objects.filter(contract=c).exists())

    def test_logout_contract_is_unfunded(self):
        c = Contract.objects.get(pk="fe961321-eb46-58a5-a322-f03553646b00")
        self.assertEqual(c.escrow_amount, 0)
        self.assertFalse(PaymentIntent.objects.filter(contract=c).exists())

    def test_localization_contract_is_unfunded(self):
        c = Contract.objects.get(pk="d1dd0923-88bb-5244-8b91-74e97c6ed451")
        self.assertEqual(c.escrow_amount, 0)
        self.assertFalse(PaymentIntent.objects.filter(contract=c).exists())

    def test_responsive_contract_is_unfunded(self):
        c = Contract.objects.get(pk="85052d24-3508-5106-a685-4747e48aeb44")
        self.assertEqual(c.escrow_amount, 0)
        self.assertFalse(PaymentIntent.objects.filter(contract=c).exists())

    # ── 3. Read-only fixture state ────────────────────────────────

    def test_pending_contract_has_one_pending_intent(self):
        c = Contract.objects.get(pk="3db4c549-571d-5973-818b-353b31f216b5")
        pending = self._get_pending_intents().filter(contract=c)
        self.assertEqual(pending.count(), 1)

    def test_funded_contract_has_one_paid_intent(self):
        c = Contract.objects.get(pk="36e7bd72-780f-527e-a888-93107709dd99")
        paid = self._get_paid_intents().filter(contract=c)
        self.assertEqual(paid.count(), 1)

    def test_funded_contract_has_escrow(self):
        c = Contract.objects.get(pk="36e7bd72-780f-527e-a888-93107709dd99")
        self.assertGreater(c.escrow_amount, 0)

    # ── 4. Legacy fixture state ───────────────────────────────────

    def test_legacy_funded_contract_exists(self):
        self.assertTrue(Contract.objects.filter(pk="02db5487-b48f-5eb9-8599-7cd477fea0e3").exists())

    def test_legacy_unfunded_contract_exists(self):
        self.assertTrue(Contract.objects.filter(pk="3c6503e0-df13-588b-9d77-a3e1dfc23749").exists())


class PaymentFixtureIdempotentTest(TestCase):
    """Two consecutive resets must produce identical state."""

    def _run_reset(self):
        out = StringIO()
        call_command("seed_e2e_fixtures", "--reset", stdout=out)
        return self._capture_state()

    def _capture_state(self):
        return {
            "intents": list(PaymentIntent.objects.values("id", "status", "contract_id").order_by("id")),
            "txns": list(WalletTransaction.objects.values("id", "amount", "contract_id").order_by("id")),
            "contracts": list(Contract.objects.filter(
                pk__in=[
                    "f872e161-f2a2-5925-a4d1-de4cc9d208d2",
                    "3430c009-26a6-573e-8725-836aa2426316",
                    "92336219-bdc8-5cb6-bc95-b885381f835b",
                    "89a7e54e-3130-506f-9ee3-5c27c70e50eb",
                    "3db4c549-571d-5973-818b-353b31f216b5",
                    "36e7bd72-780f-527e-a888-93107709dd99",
                ]
            ).values("pk", "escrow_amount").order_by("pk")),
        }

    def test_two_resets_produce_identical_state(self):
        state1 = self._run_reset()
        state2 = self._run_reset()
        self.assertEqual(state1, state2)

    def test_normal_rerun_creates_no_duplicates(self):
        """Running seed without --reset must not duplicate records."""
        self._run_reset()  # clean slate
        state_before = self._capture_state()

        out = StringIO()
        call_command("seed_e2e_fixtures", stdout=out)

        state_after = self._capture_state()
        # Normal rerun should create no NEW records (update_or_create is idempotent)
        self.assertEqual(
            len(state_before["intents"]),
            len(state_after["intents"]),
            "Normal rerun created duplicate intents",
        )
        self.assertEqual(
            len(state_before["txns"]),
            len(state_after["txns"]),
            "Normal rerun created duplicate transactions",
        )
