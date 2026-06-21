"""
Financial reconciliation service.

Read-only analysis of contract financial state.
Returns per-contract reconciliation status.

Statuses:
    BALANCED  — All financial records match.
    UNSETTLED — Contract is not yet settled.
    MISMATCH  — One or more discrepancies found.

Rules:
    - Does not auto-repair.
    - Uses Decimal throughout.
    - Quantizes consistently to 2 decimal places.
    - Uses structured relationships and transaction types.
"""

from __future__ import annotations

from decimal import Decimal, ROUND_HALF_UP
from dataclasses import dataclass, field
from typing import Optional, Literal

from contract.models import Contract
from wallet.models import (
    ContractSettlement, ContractPaymentBreakdown,
    PlatformEarning, Wallet, WalletTransaction,
    PlatformWallet, PlatformWalletTransaction,
    PaymentIntent,
)

PRECISION = Decimal("0.01")
ReconciliationStatus = Literal["BALANCED", "UNSETTLED", "MISMATCH"]


def _q(val: Decimal) -> Decimal:
    return val.quantize(PRECISION, rounding=ROUND_HALF_UP)


@dataclass
class ContractReconciliation:
    """Per-contract reconciliation result."""

    contract_id: str
    contract_reference: str
    contract_status: str
    funded_client_total: str
    contract_principal: str
    escrow_remaining: str
    released_principal: str
    technician_net_expected: str
    technician_wallet_release_total: str
    technician_commission_expected: str
    client_service_fee_expected: str
    platform_earnings_total: str
    platform_wallet_credit_total: str
    settlement_status: str | None
    reconciliation_status: ReconciliationStatus
    discrepancies: list[str] = field(default_factory=list)


def reconcile_contract(contract_id: str) -> ContractReconciliation:
    """
    Reconcile financial state for a single contract.

    Returns a ContractReconciliation with structured discrepancy codes.
    """
    contract = Contract.objects.get(id=contract_id)
    discrepancies: list[str] = []

    # --- Funding ---
    funded_intents = PaymentIntent.objects.filter(
        contract=contract,
        purpose=PaymentIntent.Purpose.CONTRACT_FUNDING,
        status=PaymentIntent.Status.PAID,
    )
    funded_total = _q(sum((i.amount for i in funded_intents), Decimal("0")))

    agreed = _q(contract.agreed_amount or Decimal("0"))
    escrow = _q(contract.escrow_amount or Decimal("0"))
    total_paid = _q(contract.total_paid or Decimal("0"))

    # --- Settlement ---
    settlement = ContractSettlement.objects.filter(
        contract=contract,
        status=ContractSettlement.Status.COMPLETED,
    ).first()

    settlement_status = settlement.status if settlement else None
    released_principal = _q(settlement.released_principal) if settlement else Decimal("0")

    # --- Breakdown ---
    breakdown = getattr(contract, "payment_breakdown", None)
    if breakdown is None:
        breakdown = ContractPaymentBreakdown.objects.filter(contract=contract).first()

    if breakdown:
        expected_tech_net = _q(breakdown.technician_net_amount)
        expected_tech_comm = _q(breakdown.technician_commission_amount)
        expected_client_fee = _q(breakdown.client_service_fee_amount)
    else:
        expected_tech_net = Decimal("0")
        expected_tech_comm = Decimal("0")
        expected_client_fee = Decimal("0")

    # --- Technician wallet releases ---
    tech_releases = WalletTransaction.objects.filter(
        contract=contract,
        transaction_type=WalletTransaction.Type.RELEASE,
    )
    tech_release_total = _q(sum((t.amount for t in tech_releases), Decimal("0")))

    # --- Platform earnings ---
    earnings = PlatformEarning.objects.filter(contract=contract)
    platform_earnings_total = _q(sum((e.amount for e in earnings), Decimal("0")))

    # --- Platform wallet credits ---
    platform_txns = PlatformWalletTransaction.objects.filter(contract=contract)
    platform_credit_total = _q(sum((t.amount for t in platform_txns), Decimal("0")))

    # --- Checks ---
    if not settlement:
        reconciliation_status: ReconciliationStatus = "UNSETTLED"
    else:
        reconciliation_status = "BALANCED"

        # 1. Technician net matches breakdown
        if settlement and _q(settlement.technician_net_amount) != expected_tech_net:
            discrepancies.append("TECHNICIAN_NET_MISMATCH")

        # 2. Technician release total matches expected net
        if tech_release_total != expected_tech_net:
            discrepancies.append("TECHNICIAN_RELEASE_TOTAL_MISMATCH")

        # 3. Earnings platform total matches expected
        if platform_earnings_total != _q(expected_tech_comm + expected_client_fee):
            discrepancies.append("PLATFORM_EARNINGS_TOTAL_MISMATCH")

        # 4. Platform credit matches earnings
        if platform_credit_total != platform_earnings_total:
            discrepancies.append("PLATFORM_CREDIT_MISMATCH")

        # 6. No duplicate earnings
        earning_types = list(earnings.values_list("earning_type", flat=True))
        if earning_types.count("technician_commission") > 1:
            discrepancies.append("DUPLICATE_TECHNICIAN_COMMISSION")
        if earning_types.count("client_service_fee") > 1:
            discrepancies.append("DUPLICATE_CLIENT_SERVICE_FEE")

        # 7. No duplicate release transactions
        if tech_releases.count() > 1:
            discrepancies.append("DUPLICATE_RELEASE_TRANSACTION")

        # 8. No duplicate completed settlements
        completed_count = ContractSettlement.objects.filter(
            contract=contract, status=ContractSettlement.Status.COMPLETED,
        ).count()
        if completed_count > 1:
            discrepancies.append("DUPLICATE_COMPLETED_SETTLEMENT")

        if discrepancies:
            reconciliation_status = "MISMATCH"

    return ContractReconciliation(
        contract_id=str(contract.id),
        contract_reference=contract.contract_reference,
        contract_status=contract.status,
        funded_client_total=str(funded_total),
        contract_principal=str(agreed),
        escrow_remaining=str(escrow),
        released_principal=str(released_principal),
        technician_net_expected=str(expected_tech_net),
        technician_wallet_release_total=str(tech_release_total),
        technician_commission_expected=str(expected_tech_comm),
        client_service_fee_expected=str(expected_client_fee),
        platform_earnings_total=str(platform_earnings_total),
        platform_wallet_credit_total=str(platform_credit_total),
        settlement_status=settlement_status,
        reconciliation_status=reconciliation_status,
        discrepancies=discrepancies,
    )


def reconcile_all_settled_contracts() -> list[ContractReconciliation]:
    """Reconcile all contracts that have at least one settlement."""
    settled_ids = (
        ContractSettlement.objects.filter(status=ContractSettlement.Status.COMPLETED)
        .values_list("contract_id", flat=True)
        .distinct()
    )
    return [reconcile_contract(cid) for cid in settled_ids]
