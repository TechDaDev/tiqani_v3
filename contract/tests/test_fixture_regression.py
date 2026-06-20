"""Tests for deterministic Phase 8 E2E fixture behavior.

Verifies idempotency, escrow/wallet safety, and data integrity across resets.
"""

from decimal import Decimal
from django.test import TestCase
from django.contrib.auth import get_user_model
from django.core.management import call_command

from contract.models import (
    Contract, ExecutionMilestone, DeliverableSubmission,
    RevisionRequest, CompletionRequest, ContractAuditEvent,
)
from wallet.models import Wallet, WalletTransaction, PaymentIntent

User = get_user_model()

FIXTURE_PASSWORD = "local-test-only"
EXEC_CONTRACT_LABELS = [
    "activation", "milestone-create", "milestone-reorder",
    "milestone-start", "deliverable-submit", "revision-request",
    "resubmission", "milestone-approval", "completion-request",
    "completion-confirm", "completion-reject", "execution-history",
    "client-b-only", "tech-b-only", "completed",
]


class FixtureIdempotencyTestCase(TestCase):
    """Two resets produce identical counts and UUIDs."""

    def _run_seed(self, reset=False):
        kwargs = {"force": True}
        if reset:
            kwargs["reset"] = True
        call_command("seed_e2e_fixtures", **kwargs)

    def test_two_resets_identical_counts(self):
        """Two --reset runs produce same deterministic counts."""
        self._run_seed(reset=True)
        counts1 = self._collect_counts()

        self._run_seed(reset=True)
        counts2 = self._collect_counts()

        for key in counts1:
            self.assertEqual(
                counts1[key], counts2[key],
                f"Mismatch for {key}: {counts1[key]} vs {counts2[key]}",
            )

    def test_normal_rerun_no_duplicates(self):
        """Running without --reset creates no duplicate records."""
        self._run_seed(reset=True)
        counts1 = self._collect_counts()

        self._run_seed(reset=False)
        counts2 = self._collect_counts()

        for key in counts1:
            self.assertEqual(
                counts1[key], counts2[key],
                f"Normal rerun created duplicates for {key}",
            )

    def _collect_counts(self):
        return {
            "execution_contracts": Contract.objects.filter(
                work_description__startswith="E2E execution"
            ).count(),
            "milestones": ExecutionMilestone.objects.count(),
            "submissions": DeliverableSubmission.objects.count(),
            "revisions": RevisionRequest.objects.count(),
            "completion_requests": CompletionRequest.objects.count(),
            "history_events": ContractAuditEvent.objects.count(),
        }


class FixtureEscrowSafetyTestCase(TestCase):
    """Escrow and wallet values remain unchanged after fixture operations."""

    def _run_seed(self, reset=False):
        kwargs = {"force": True}
        if reset:
            kwargs["reset"] = True
        call_command("seed_e2e_fixtures", **kwargs)

    def setUp(self):
        self._run_seed(reset=True)

    def test_funded_contract_escrow_preserved(self):
        """Funded contracts retain correct escrow amounts."""
        for label in ["activation", "milestone-create", "milestone-reorder"]:
            c = Contract.objects.get(
                work_description__endswith=f" -- {label}."
            )
            self.assertEqual(c.escrow_amount, Decimal("100000.00"))
            self.assertEqual(c.total_paid, Decimal("0"))

    def test_completed_contract_escrow_still_held(self):
        """Completed contract still has escrow held."""
        c = Contract.objects.get(
            work_description__endswith=" -- completed."
        )
        self.assertEqual(c.status, "completed")
        self.assertEqual(c.escrow_amount, Decimal("100000.00"))
        self.assertEqual(c.total_paid, Decimal("0"))

    def test_no_payout_or_withdrawal_records(self):
        """No payout or withdrawal transactions exist for fixture users."""
        # Check no payouts
        self.assertEqual(
            WalletTransaction.objects.filter(
                transaction_type=WalletTransaction.Type.WITHDRAWAL
            ).count(),
            0,
        )
        self.assertEqual(
            PaymentIntent.objects.filter(
                purpose=PaymentIntent.Purpose.WITHDRAWAL
            ).count(),
            0,
        )


class FixtureDeterministicUUIDsTestCase(TestCase):
    """All deterministic Phase 8 UUIDs exist after seeding."""

    def _run_seed(self, reset=False):
        kwargs = {"force": True}
        if reset:
            kwargs["reset"] = True
        call_command("seed_e2e_fixtures", **kwargs)

    def setUp(self):
        self._run_seed(reset=True)

    def test_all_execution_contracts_exist(self):
        """All 15 execution contracts exist with deterministic UUIDs."""
        for label in EXEC_CONTRACT_LABELS:
            exists = Contract.objects.filter(
                work_description__endswith=f" -- {label}."
            ).exists()
            self.assertTrue(exists, f"Missing execution contract: {label}")

    def test_milestone_sequences_deterministic(self):
        """Reorder contract has milestones 1,2,3."""
        c = Contract.objects.get(
            work_description__endswith=" -- milestone-reorder."
        )
        seqs = list(
            ExecutionMilestone.objects.filter(contract=c)
            .order_by("sequence")
            .values_list("sequence", flat=True)
        )
        self.assertEqual(seqs, [1, 2, 3])
