"""Serializers for admin dashboard APIs."""

import mimetypes
import os
from decimal import Decimal

from rest_framework import serializers
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError as DjangoValidationError

from accounts.models import TechnicianProfile, ClientProfile
from contract.models import Contract, ContractStage, TimeExtensionRequest
from wallet.models import (
    ContractPaymentBreakdown, ContractSettlement, PaymentIntent, PlatformEarning,
    PlatformWallet, PlatformWalletTransaction, WithdrawalRequest, Wallet,
    WalletTransaction,
)
from dispute.models import RefundRecord
from ratereview.models import Review, ReviewReport
from notification.models import ActivityLog

User = get_user_model()


TECHNICIAN_APPROVAL_FIELD_LABELS = {
    "phone_number": "phone_number",
    "governorate": "governorate",
    "address": "address",
    "gender": "gender",
    "date_of_birth": "date_of_birth",
    "profile_image": "profile_image",
    "job_title": "job_title",
    "about": "about",
    "years_of_expertise": "years_of_expertise",
    "identification_documents": "documents",
    "github": "github_url",
    "linkedin": "linkedin_url",
}


def _field_valid(tech, field_name):
    value = getattr(tech, field_name, None)
    if not value:
        return False
    field = tech._meta.get_field(field_name)
    try:
        field.run_validators(value)
    except DjangoValidationError:
        return False
    return True


def technician_approval_missing_requirements(tech):
    missing = [
        TECHNICIAN_APPROVAL_FIELD_LABELS.get(field, field)
        for field in tech.get_incomplete_fields()
    ]
    if not _field_valid(tech, "github"):
        missing.append("github_url")
    if not _field_valid(tech, "linkedin"):
        missing.append("linkedin_url")
    if not tech.identification_documents:
        missing.append("documents")
    if not tech.user.is_active:
        missing.append("active_account")
    if not tech.is_available:
        missing.append("not_suspended")
    return sorted(set(missing))


def technician_approval_checklist(tech):
    missing = set(technician_approval_missing_requirements(tech))
    return [
        {"key": "profile_exists", "passed": True},
        {"key": "profile_complete", "passed": not any(
            key in missing for key in [
                "phone_number", "governorate", "address", "gender", "date_of_birth",
                "profile_image", "job_title", "about", "years_of_expertise",
            ]
        )},
        {"key": "github_url", "passed": "github_url" not in missing},
        {"key": "linkedin_url", "passed": "linkedin_url" not in missing},
        {"key": "documents", "passed": "documents" not in missing},
        {"key": "active_account", "passed": "active_account" not in missing},
        {"key": "not_suspended", "passed": "not_suspended" not in missing},
    ]


def technician_document_items(tech):
    document = tech.identification_documents
    if not document:
        return []

    name = os.path.basename(document.name or "identification-document")
    content_type = mimetypes.guess_type(name)[0] or "application/octet-stream"
    size = None
    try:
        size = document.size
    except Exception:
        size = None

    return [{
        "id": "identification_documents",
        "name": name,
        "type": content_type,
        "status": "uploaded",
        "uploaded_at": tech.updated_at,
        "size": size,
        "download_url": f"/api/admin/technicians/{tech.id}/documents/identification_documents/",
    }]


# ------------------------------------------------------------------
# Dashboard summary (no model serializer needed — built manually)
# ------------------------------------------------------------------

class DashboardSummarySerializer(serializers.Serializer):
    users = serializers.DictField()
    technicians = serializers.DictField()
    contracts = serializers.DictField()
    finance = serializers.DictField()
    reviews = serializers.DictField()
    notifications = serializers.DictField()


# ------------------------------------------------------------------
# User management serializers
# ------------------------------------------------------------------

class AdminUserListSerializer(serializers.ModelSerializer):
    role_display = serializers.CharField(source='get_role_display', read_only=True)

    class Meta:
        model = User
        fields = [
            'id', 'username', 'email', 'role', 'role_display',
            'first_name', 'last_name', 'phone_number',
            'governorate', 'is_active', 'date_joined',
        ]


class AdminUserDetailSerializer(serializers.ModelSerializer):
    role_display = serializers.CharField(source='get_role_display', read_only=True)
    profiles = serializers.SerializerMethodField()
    activity = serializers.SerializerMethodField()
    financial_summary = serializers.SerializerMethodField()
    recent_audit_events = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = [
            'id', 'username', 'email', 'role', 'role_display',
            'first_name', 'last_name', 'phone_number',
            'governorate', 'address', 'gender', 'date_of_birth',
            'is_active', 'is_staff', 'is_superuser',
            'date_joined', 'last_login',
            'profiles', 'activity', 'financial_summary', 'recent_audit_events',
        ]
        read_only_fields = ['id', 'username', 'role', 'is_superuser', 'date_joined', 'last_login']

    def get_profiles(self, obj):
        client = getattr(obj, 'client_profile', None)
        technician = getattr(obj, 'technician_profile', None)
        return {
            'client': {
                'exists': bool(client),
                'is_complete': bool(getattr(client, 'is_complete', False)) if client else False,
            },
            'technician': {
                'exists': bool(technician),
                'is_complete': bool(getattr(technician, 'is_complete', False)) if technician else False,
                'approved': bool(getattr(technician, 'approved', False)) if technician else False,
                'job_title': getattr(technician, 'job_title', '') if technician else '',
                'missing_fields': technician.get_incomplete_fields() if technician else [],
            },
        }

    def get_activity(self, obj):
        data = {
            'requests': 0,
            'offers': 0,
            'contracts': 0,
            'reviews': 0,
            'notifications': 0,
            'audit_events': 0,
        }
        client = getattr(obj, 'client_profile', None)
        technician = getattr(obj, 'technician_profile', None)
        try:
            from servicerequest.models import ServiceRequest
            if client:
                data['requests'] += ServiceRequest.objects.filter(client=client).count()
            if technician:
                data['requests'] += ServiceRequest.objects.filter(technician=technician).count()
        except Exception:
            pass
        try:
            from contract.offer_models import Offer
            if technician:
                data['offers'] += Offer.objects.filter(technician=technician).count()
            if client:
                data['offers'] += Offer.objects.filter(service_request__client=client).count()
        except Exception:
            pass
        try:
            if client:
                data['contracts'] += Contract.objects.filter(client=client).count()
            if technician:
                data['contracts'] += Contract.objects.filter(technician=technician).count()
        except Exception:
            pass
        try:
            data['reviews'] = Review.objects.filter(reviewer=obj).count()
            if technician:
                data['reviews'] += Review.objects.filter(technician=technician).count()
        except Exception:
            pass
        try:
            from notification.models import Notification
            data['notifications'] = Notification.objects.filter(user=obj).count()
            data['audit_events'] = ActivityLog.objects.filter(actor=obj).count()
        except Exception:
            pass
        return data

    def get_financial_summary(self, obj):
        wallet = getattr(obj, 'wallet', None)
        return {
            'wallet_exists': bool(wallet),
            'wallet_balance': str(wallet.balance) if wallet else None,
            'payment_intents': PaymentIntent.objects.filter(user=obj).count(),
            'withdrawals': WithdrawalRequest.objects.filter(user=obj).count(),
        }

    def get_recent_audit_events(self, obj):
        return [
            {
                'id': str(event.id),
                'verb': event.verb,
                'target_type': event.target_type,
                'target_id': str(event.target_id),
                'created_at': event.created_at,
            }
            for event in ActivityLog.objects.filter(actor=obj).order_by('-created_at')[:5]
        ]


class AdminUserUpdateSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ['is_active', 'first_name', 'last_name', 'phone_number', 'governorate', 'address']
        extra_kwargs = {f: {'required': False} for f in fields}


# ------------------------------------------------------------------
# Technician admin serializers
# ------------------------------------------------------------------

class AdminTechnicianListSerializer(serializers.ModelSerializer):
    username = serializers.CharField(source='user.username', read_only=True)
    email = serializers.EmailField(source='user.email', read_only=True)
    phone_number = serializers.CharField(source='user.phone_number', read_only=True)
    incomplete_fields = serializers.SerializerMethodField()
    has_documents = serializers.SerializerMethodField()
    has_github = serializers.SerializerMethodField()
    has_linkedin = serializers.SerializerMethodField()

    class Meta:
        model = TechnicianProfile
        fields = [
            'id', 'username', 'email', 'phone_number',
            'job_title', 'rate', 'approved', 'is_available',
            'years_of_expertise', 'governorate', 'is_complete',
            'incomplete_fields', 'has_documents', 'has_github', 'has_linkedin',
            'created_at',
        ]

    governorate = serializers.CharField(source='user.governorate', read_only=True)

    def get_incomplete_fields(self, obj):
        return obj.get_incomplete_fields()

    def get_has_documents(self, obj):
        return bool(obj.identification_documents)

    def get_has_github(self, obj):
        return bool(obj.github)

    def get_has_linkedin(self, obj):
        return bool(obj.linkedin)


class AdminTechnicianDetailSerializer(serializers.ModelSerializer):
    user = AdminUserDetailSerializer(read_only=True)
    incomplete_fields = serializers.SerializerMethodField()
    approval_requirements = serializers.SerializerMethodField()
    documents = serializers.SerializerMethodField()
    images = serializers.SerializerMethodField()
    skill_sets = serializers.SerializerMethodField()
    governorate = serializers.CharField(source='user.governorate', read_only=True)
    gender = serializers.CharField(source='user.gender', read_only=True)
    profile_image = serializers.CharField(source='user.profile_image', read_only=True)

    class Meta:
        model = TechnicianProfile
        fields = [
            'id', 'user', 'job_title', 'rate', 'approved', 'is_available',
            'years_of_expertise', 'governorate', 'is_complete',
            'incomplete_fields', 'has_documents', 'has_github', 'has_linkedin',
            'github', 'linkedin', 'about', 'last_active', 'gender',
            'profile_image', 'documents', 'images', 'skill_sets',
            'approval_requirements', 'created_at', 'updated_at',
        ]

    def get_incomplete_fields(self, obj):
        return obj.get_incomplete_fields()

    def get_has_documents(self, obj):
        return bool(obj.identification_documents)

    def get_has_github(self, obj):
        return bool(obj.github)

    def get_has_linkedin(self, obj):
        return bool(obj.linkedin)

    has_documents = serializers.SerializerMethodField()
    has_github = serializers.SerializerMethodField()
    has_linkedin = serializers.SerializerMethodField()

    def get_documents(self, obj):
        return technician_document_items(obj)

    def get_images(self, obj):
        request = self.context.get('request')
        items = []
        for image in obj.portfolio_images.all():
            url = ''
            if image.image:
                try:
                    url = request.build_absolute_uri(image.image.url) if request else image.image.url
                except Exception:
                    url = ''
            items.append({
                'id': image.id,
                'image': url,
                'description': image.description or '',
            })
        return items

    def get_skill_sets(self, obj):
        skill_set = getattr(obj, 'skill_set', None)
        if not skill_set:
            return {'categories_detail': [], 'skills_detail': [], 'sub_skills_detail': []}
        return {
            'categories_detail': [{'id': item.id, 'name': item.name} for item in skill_set.categories.all()],
            'skills_detail': [{'id': item.id, 'name': item.name} for item in skill_set.skills.all()],
            'sub_skills_detail': [{'id': item.id, 'name': item.name} for item in skill_set.sub_skills.all()],
        }

    def get_approval_requirements(self, obj):
        missing = technician_approval_missing_requirements(obj)
        return {
            'can_approve': not missing,
            'missing': missing,
            'checklist': technician_approval_checklist(obj),
        }


class TechnicianRejectSerializer(serializers.Serializer):
    reason = serializers.CharField(required=False, allow_blank=True)


# ------------------------------------------------------------------
# Contract admin serializers
# ------------------------------------------------------------------

class AdminContractListSerializer(serializers.ModelSerializer):
    client_name = serializers.SerializerMethodField()
    technician_name = serializers.SerializerMethodField()

    class Meta:
        model = Contract
        fields = [
            'id', 'contract_reference', 'status',
            'client_name', 'technician_name',
            'agreed_amount', 'stage_number',
            'client_accepted', 'technician_accepted',
            'created_at',
        ]

    def get_client_name(self, obj):
        return str(obj.client) if obj.client else None

    def get_technician_name(self, obj):
        return str(obj.technician) if obj.technician else None


class AdminContractDetailSerializer(serializers.ModelSerializer):
    stages = serializers.SerializerMethodField()
    payment_breakdown = serializers.SerializerMethodField()
    payment_intents = serializers.SerializerMethodField()
    platform_earnings = serializers.SerializerMethodField()
    extension_requests = serializers.SerializerMethodField()

    class Meta:
        model = Contract
        fields = '__all__'

    def get_stages(self, obj):
        stages = obj.stages.all().order_by('stage_number')
        return [
            {
                'id': str(s.id), 'stage_number': s.stage_number,
                'amount': str(s.amount), 'is_approved_by_client': s.is_approved_by_client,
                'completed_at': s.completed_at, 'created_at': s.created_at,
            }
            for s in stages
        ]

    def get_payment_breakdown(self, obj):
        if hasattr(obj, 'payment_breakdown'):
            pb = obj.payment_breakdown
            return {
                'id': str(pb.id), 'contract_amount': str(pb.contract_amount),
                'technician_commission_amount': str(pb.technician_commission_amount),
                'client_service_fee_amount': str(pb.client_service_fee_amount),
                'total_platform_fee': str(pb.total_platform_fee),
                'client_total_amount': str(pb.client_total_amount),
                'technician_net_amount': str(pb.technician_net_amount),
            }
        return None

    def get_payment_intents(self, obj):
        return list(obj.payment_intents.values('id', 'amount', 'status', 'purpose', 'created_at'))

    def get_platform_earnings(self, obj):
        return list(obj.platform_earnings.values('id', 'earning_type', 'amount', 'status'))

    def get_extension_requests(self, obj):
        return list(obj.extension_requests.values('id', 'requested_days', 'status', 'reason', 'created_at'))


class AdminContractForceCancelSerializer(serializers.Serializer):
    reason = serializers.CharField(required=True)


# ------------------------------------------------------------------
# Review admin serializers
# ------------------------------------------------------------------

class AdminReviewListSerializer(serializers.ModelSerializer):
    reviewer_name = serializers.SerializerMethodField()
    technician_name = serializers.SerializerMethodField()

    class Meta:
        model = Review
        fields = [
            'id', 'reviewer_name', 'technician_name',
            'rating', 'is_public', 'is_verified',
            'helpful_count', 'reported_count', 'flagged_at',
            'created_at',
        ]

    def get_reviewer_name(self, obj):
        return obj.reviewer.get_full_name() or obj.reviewer.username if obj.reviewer else None

    def get_technician_name(self, obj):
        return str(obj.technician) if obj.technician else None


class AdminReviewDetailSerializer(serializers.ModelSerializer):
    reviewer_name = serializers.SerializerMethodField()
    technician_name = serializers.SerializerMethodField()
    reports = serializers.SerializerMethodField()

    class Meta:
        model = Review
        fields = '__all__'

    def get_reviewer_name(self, obj):
        return obj.reviewer.get_full_name() or obj.reviewer.username if obj.reviewer else None

    def get_technician_name(self, obj):
        return str(obj.technician) if obj.technician else None

    def get_reports(self, obj):
        return list(obj.reports.values('reporter', 'reason', 'comment', 'created_at'))


# ------------------------------------------------------------------
# Finance serializers
# ------------------------------------------------------------------

class AdminPlatformEarningSerializer(serializers.ModelSerializer):
    class Meta:
        model = PlatformEarning
        fields = '__all__'


class AdminPaymentIntentSerializer(serializers.ModelSerializer):
    class Meta:
        model = PaymentIntent
        fields = '__all__'


class AdminWithdrawalSerializer(serializers.ModelSerializer):
    class Meta:
        model = WithdrawalRequest
        fields = '__all__'


class AdminWithdrawalActionSerializer(serializers.Serializer):
    note = serializers.CharField(required=True, allow_blank=False, max_length=2000)


class AdminPaymentIntentMarkPaidSerializer(serializers.Serializer):
    pass


def _money(value):
    return str(value or Decimal("0.00"))


def _user_label(user):
    if not user:
        return ""
    return user.get_full_name() or user.username


def _mask_reference(value):
    value = str(value or "")
    if not value:
        return ""
    if len(value) <= 8:
        return "****"
    return f"{value[:4]}...{value[-4:]}"


class AdminFinancialPaymentSerializer(serializers.ModelSerializer):
    payer = serializers.SerializerMethodField()
    contract_reference = serializers.CharField(source="contract.contract_reference", read_only=True)
    amount = serializers.SerializerMethodField()
    provider_reference_masked = serializers.SerializerMethodField()

    class Meta:
        model = PaymentIntent
        fields = [
            "id", "contract", "contract_reference", "payer", "amount", "currency",
            "purpose", "provider", "provider_reference_masked", "status",
            "paid_at", "created_at", "updated_at",
        ]
        read_only_fields = fields

    def get_payer(self, obj):
        return {"id": str(obj.user_id), "name": _user_label(obj.user)}

    def get_amount(self, obj):
        return _money(obj.amount)

    def get_provider_reference_masked(self, obj):
        return _mask_reference(obj.provider_reference)


class AdminFinancialRefundSerializer(serializers.ModelSerializer):
    client = serializers.SerializerMethodField()
    technician = serializers.SerializerMethodField()
    contract_reference = serializers.CharField(source="contract.contract_reference", read_only=True)
    dispute_id = serializers.UUIDField(source="dispute.id", read_only=True)
    amount = serializers.SerializerMethodField()
    provider_reference_masked = serializers.SerializerMethodField()
    reconciliation = serializers.SerializerMethodField()

    class Meta:
        model = RefundRecord
        fields = [
            "id", "contract", "contract_reference", "dispute_id", "client", "technician",
            "amount", "currency", "source_type", "status", "refund_method",
            "provider_reference_masked", "reconciliation", "initiated_at",
            "completed_at", "failed_at", "created_at", "updated_at",
        ]
        read_only_fields = fields

    def get_client(self, obj):
        return {"id": str(obj.client_id), "name": _user_label(obj.client)}

    def get_technician(self, obj):
        user = getattr(getattr(obj.contract, "technician", None), "user", None)
        return {"id": str(user.id), "name": _user_label(user)} if user else None

    def get_amount(self, obj):
        return _money(obj.amount)

    def get_provider_reference_masked(self, obj):
        return _mask_reference(obj.provider_reference)

    def get_reconciliation(self, obj):
        return {
            "has_wallet_transaction": bool(obj.wallet_transaction_id),
            "is_completed": obj.status == "completed",
            "source_type": obj.source_type,
        }


class AdminFinancialWithdrawalSerializer(serializers.ModelSerializer):
    user = serializers.SerializerMethodField()
    amount = serializers.SerializerMethodField()
    requested_method_masked = serializers.SerializerMethodField()

    class Meta:
        model = WithdrawalRequest
        fields = [
            "id", "user", "amount", "currency", "status", "requested_method_masked",
            "notes", "admin_note", "reviewed_at", "paid_at", "created_at", "updated_at",
        ]
        read_only_fields = fields

    def get_user(self, obj):
        return {"id": str(obj.user_id), "name": _user_label(obj.user)}

    def get_amount(self, obj):
        return _money(obj.amount)

    def get_requested_method_masked(self, obj):
        return _mask_reference(obj.requested_method) or obj.requested_method


class AdminFinancialLedgerSerializer(serializers.ModelSerializer):
    user = serializers.SerializerMethodField()
    amount = serializers.SerializerMethodField()
    source_object = serializers.SerializerMethodField()
    direction = serializers.SerializerMethodField()

    class Meta:
        model = WalletTransaction
        fields = [
            "id", "user", "wallet", "contract", "transaction_type", "direction",
            "amount", "amount_usd", "exchange_rate", "source_object",
            "description", "created_at", "updated_at",
        ]
        read_only_fields = fields

    def get_user(self, obj):
        user = getattr(obj.wallet, "user", None)
        return {"id": str(user.id), "name": _user_label(user)} if user else None

    def get_amount(self, obj):
        return _money(obj.amount)

    def get_source_object(self, obj):
        if obj.contract_id:
            return {"type": "contract", "id": str(obj.contract_id)}
        return {"type": "wallet", "id": str(obj.wallet_id)}

    def get_direction(self, obj):
        if obj.transaction_type in {"deposit", "refund", "release"}:
            return "credit"
        return "debit"


class AdminFinancialEscrowSerializer(serializers.ModelSerializer):
    client = serializers.SerializerMethodField()
    technician = serializers.SerializerMethodField()
    contract_reference = serializers.CharField(source="contract.contract_reference", read_only=True)
    title = serializers.CharField(source="contract.work_description", read_only=True)
    escrow_amount = serializers.SerializerMethodField()
    settled_at = serializers.DateTimeField(source="completed_at", read_only=True)
    dispute_state = serializers.SerializerMethodField()
    refund_state = serializers.SerializerMethodField()

    class Meta:
        model = ContractSettlement
        fields = [
            "id", "contract", "contract_reference", "title", "client", "technician",
            "escrow_amount", "released_principal", "technician_net_amount",
            "total_platform_fee", "currency", "status", "initiated_at",
            "settled_at", "dispute_state", "refund_state", "created_at", "updated_at",
        ]
        read_only_fields = fields

    def get_client(self, obj):
        user = getattr(getattr(obj.contract, "client", None), "user", None)
        return {"id": str(user.id), "name": _user_label(user)} if user else None

    def get_technician(self, obj):
        user = getattr(getattr(obj.contract, "technician", None), "user", None)
        return {"id": str(user.id), "name": _user_label(user)} if user else None

    def get_escrow_amount(self, obj):
        return _money(getattr(obj.contract, "escrow_amount", None))

    def get_dispute_state(self, obj):
        dispute = obj.contract.disputes.order_by("-created_at").first()
        return dispute.status if dispute else ""

    def get_refund_state(self, obj):
        refund = obj.contract.refunds.order_by("-created_at").first()
        return refund.status if refund else ""


class AdminFinancialAuditSerializer(serializers.ModelSerializer):
    actor = serializers.SerializerMethodField()
    amount = serializers.SerializerMethodField()
    reason = serializers.SerializerMethodField()
    previous_state = serializers.SerializerMethodField()
    new_state = serializers.SerializerMethodField()
    source_service = serializers.SerializerMethodField()

    class Meta:
        model = ActivityLog
        fields = [
            "id", "verb", "actor", "target_type", "target_id", "target_repr",
            "amount", "reason", "previous_state", "new_state", "source_service",
            "created_at",
        ]
        read_only_fields = fields

    def _metadata(self, obj):
        return obj.metadata if isinstance(obj.metadata, dict) else {}

    def get_actor(self, obj):
        return {"id": str(obj.actor_id), "name": _user_label(obj.actor)} if obj.actor else None

    def get_amount(self, obj):
        amount = self._metadata(obj).get("amount")
        return str(amount) if amount is not None else ""

    def get_reason(self, obj):
        return str(self._metadata(obj).get("reason") or "")

    def get_previous_state(self, obj):
        return self._metadata(obj).get("previous_state") or {}

    def get_new_state(self, obj):
        return self._metadata(obj).get("new_state") or {}

    def get_source_service(self, obj):
        return str(self._metadata(obj).get("source_service") or "admin")


class AdminFinancialUserWalletSerializer(serializers.ModelSerializer):
    user = serializers.SerializerMethodField()
    balance = serializers.SerializerMethodField()
    recent_transactions = serializers.SerializerMethodField()

    class Meta:
        model = Wallet
        fields = ["user", "balance", "transaction_id", "updated_at", "recent_transactions"]
        read_only_fields = fields

    def get_user(self, obj):
        return {"id": str(obj.user_id), "name": _user_label(obj.user)}

    def get_balance(self, obj):
        return _money(obj.balance)

    def get_recent_transactions(self, obj):
        return AdminFinancialLedgerSerializer(obj.transactions.all()[:10], many=True).data


# ------------------------------------------------------------------
# Activity serializers
# ------------------------------------------------------------------

class AdminActivitySerializer(serializers.ModelSerializer):
    actor_name = serializers.SerializerMethodField()

    class Meta:
        model = ActivityLog
        fields = '__all__'

    def get_actor_name(self, obj):
        if obj.actor:
            return obj.actor.get_full_name() or obj.actor.username
        return None
