"""Serializers for contract app - contract management and payment workflows."""

from rest_framework import serializers
from django.conf import settings
from django.utils import timezone
from decimal import Decimal

from .models import (
    Contract,
    ContractStage,
    TimeExtensionRequest,
    ContractVersion,
    ContractSignature,
    ContractDocument,
    PlatformAttestation,
)
from accounts.models import ClientProfile, TechnicianProfile


class ClientProfileBasicSerializer(serializers.ModelSerializer):
    """Basic client profile info for contract context (no sensitive fields)."""
    
    user_id = serializers.CharField(source='user.id', read_only=True)
    username = serializers.CharField(source='user.username', read_only=True)
    full_name = serializers.CharField(source='user.get_full_name', read_only=True)
    profile_image = serializers.SerializerMethodField()
    
    class Meta:
        model = ClientProfile
        fields = ('user_id', 'username', 'full_name', 'profile_image')
        read_only_fields = fields
    
    def get_profile_image(self, obj):
        if obj.user.profile_image:
            request = self.context.get('request')
            if request:
                return request.build_absolute_uri(obj.user.profile_image.url)
            return obj.user.profile_image.url
        return None


class TechnicianProfileBasicSerializer(serializers.ModelSerializer):
    """Basic technician profile info for contract context (no sensitive fields)."""
    
    user_id = serializers.CharField(source='user.id', read_only=True)
    username = serializers.CharField(source='user.username', read_only=True)
    full_name = serializers.CharField(source='user.get_full_name', read_only=True)
    profile_image = serializers.SerializerMethodField()
    job_title = serializers.CharField(read_only=True)
    
    class Meta:
        model = TechnicianProfile
        fields = ('user_id', 'username', 'full_name', 'profile_image', 'job_title')
        read_only_fields = fields
    
    def get_profile_image(self, obj):
        if obj.user.profile_image:
            request = self.context.get('request')
            if request:
                return request.build_absolute_uri(obj.user.profile_image.url)
            return obj.user.profile_image.url
        return None


class ContractStageSerializer(serializers.ModelSerializer):
    """Serializer for individual contract stages with payment tracking."""
    
    contract_reference = serializers.CharField(source='contract.contract_reference', read_only=True)
    
    class Meta:
        model = ContractStage
        fields = (
            'id', 'contract', 'contract_reference', 'stage_number', 'stage_description',
            'amount', 'deadline', 'is_approved_by_client', 'completed_at', 'created_at', 'updated_at'
        )
        read_only_fields = ('id', 'contract', 'contract_reference', 'completed_at', 'created_at', 'updated_at')


class TimeExtensionRequestSerializer(serializers.ModelSerializer):
    """Serializer for time extension requests with approval/rejection tracking."""
    
    contract_reference = serializers.CharField(source='contract.contract_reference', read_only=True)
    requested_by_name = serializers.CharField(
        source='requested_by.user.get_full_name',
        read_only=True
    )
    
    class Meta:
        model = TimeExtensionRequest
        fields = (
            'id', 'contract', 'contract_reference', 'requested_days', 'reason',
            'status', 'requested_by', 'requested_by_name', 'client_response',
            'created_at', 'updated_at', 'responded_at'
        )
        read_only_fields = (
            'id', 'contract', 'contract_reference', 'status', 'requested_by_name',
            'client_response', 'responded_at', 'created_at', 'updated_at'
        )


class ContractListSerializer(serializers.ModelSerializer):
    """Serializer for contract list view (summary information)."""
    
    client = ClientProfileBasicSerializer(read_only=True)
    technician = TechnicianProfileBasicSerializer(read_only=True)
    can_be_accepted = serializers.SerializerMethodField()
    
    class Meta:
        model = Contract
        fields = (
            'id', 'contract_reference', 'client', 'technician', 'work_description',
            'agreed_amount', 'amount_usd', 'currency',
            'escrow_amount', 'total_paid', 'start_date', 'duration_days', 'contract_duration', 'stage_number',
            'status', 'client_accepted', 'technician_accepted', 'created_at',
            'updated_at', 'can_be_accepted'
        )
        read_only_fields = (
            'id', 'contract_reference', 'client', 'technician', 'amount_usd',
            'currency', 'escrow_amount', 'total_paid', 'contract_duration',
            'created_at', 'updated_at'
        )
    
    def get_can_be_accepted(self, obj):
        return obj.can_be_accepted()


class ContractDetailSerializer(serializers.ModelSerializer):
    """Serializer for contract detail view with nested stages."""
    
    client = ClientProfileBasicSerializer(read_only=True)
    technician = TechnicianProfileBasicSerializer(read_only=True)
    stages = ContractStageSerializer(many=True, read_only=True)
    can_be_accepted = serializers.SerializerMethodField()
    incomplete_fields = serializers.SerializerMethodField()
    allowed_actions = serializers.SerializerMethodField()
    extension_requests = serializers.SerializerMethodField()
    platform_fee_rate = serializers.SerializerMethodField()
    
    class Meta:
        model = Contract
        fields = (
            'id', 'contract_reference', 'client', 'technician', 'work_description',
            'agreed_amount', 'amount_usd', 'currency', 'client_platform_fee', 'technician_platform_fee',
            'escrow_amount', 'total_paid', 'start_date', 'duration_days', 'contract_duration', 'stage_number',
            'status', 'client_accepted', 'technician_accepted', 'stages', 'extension_requests',
            'created_at', 'updated_at', 'can_be_accepted', 'incomplete_fields', 'allowed_actions',
            'platform_fee_rate',
        )
        read_only_fields = (
            'id', 'contract_reference', 'client', 'technician', 'stages', 'extension_requests',
            'amount_usd', 'currency', 'escrow_amount', 'client_platform_fee', 'technician_platform_fee',
            'total_paid', 'contract_duration', 'created_at', 'updated_at',
            'can_be_accepted', 'incomplete_fields', 'allowed_actions', 'platform_fee_rate',
        )
    
    def get_can_be_accepted(self, obj):
        return obj.can_be_accepted()
    
    def get_incomplete_fields(self, obj):
        if obj.status == 'draft':
            return obj.get_incomplete_fields()
        return []

    def get_platform_fee_rate(self, obj):
        return float(obj.PLATFORM_FEE_RATE)

    def get_extension_requests(self, obj):
        qs = obj.extension_requests.all()
        return TimeExtensionRequestSerializer(qs, many=True).data

    def get_allowed_actions(self, obj):
        """Return list of allowed actions for the requesting user."""
        request = self.context.get("request")
        if not request or not request.user.is_authenticated:
            return []
        user = request.user
        actions = []
        is_client = hasattr(user, "client_profile") and obj.client.user == user
        is_technician = hasattr(user, "technician_profile") and obj.technician.user == user
        is_admin = user.is_staff

        if obj.status == "draft":
            if is_technician:
                actions.append("submit_proposal")
            if is_client or is_admin:
                actions.append("cancel")
        elif obj.status == "pending_acceptance":
            if is_client and not obj.client_accepted:
                actions.append("accept")
            if is_technician and not obj.technician_accepted:
                actions.append("accept")
            if (is_client or is_technician) or is_admin:
                actions.append("cancel")
        elif obj.status == "pending_signatures":
            if is_client or is_technician:
                actions.extend(["freeze", "request_signature_otp", "sign", "list_signatures"])
            if is_admin:
                actions.extend(["freeze", "list_signatures"])
        elif obj.status == "pending_finalization":
            if is_client or is_technician or is_admin:
                actions.extend(["list_signatures", "finalize", "list_documents"])
        elif obj.status == "in_progress":
            if is_technician:
                actions.append("request_extension")
            if is_client or is_technician or is_admin:
                actions.append("list_documents")
            if is_admin:
                actions.append("cancel")
        elif obj.status in ("completed", "canceled"):
            pass
        return actions


class ContractCreateSerializer(serializers.Serializer):
    """Serializer for creating a new contract (client initiates)."""
    
    technician_id = serializers.UUIDField()
    work_description = serializers.CharField(max_length=2000)
    
    def validate_technician_id(self, value):
        try:
            technician = TechnicianProfile.objects.get(user__id=value)
        except TechnicianProfile.DoesNotExist:
            raise serializers.ValidationError("Technician does not exist.")
        
        if not technician.is_available:
            raise serializers.ValidationError("Technician is not available for new contracts.")
        
        return value
    
    def create(self, validated_data):
        """Create a new contract with client."""
        request = self.context.get('request')
        client = ClientProfile.objects.get(user=request.user)
        technician = TechnicianProfile.objects.get(user__id=validated_data['technician_id'])
        
        contract = Contract.objects.create(
            client=client,
            technician=technician,
            work_description=validated_data['work_description'],
            status='draft'
        )
        
        return contract


class ContractUpdateSerializer(serializers.ModelSerializer):
    """Serializer for updating contract details (technician completes or parties accept)."""
    
    class Meta:
        model = Contract
        fields = (
            'work_description', 'agreed_amount', 'stage_number', 'start_date', 'duration_days', 'contract_duration',
            'client_accepted', 'technician_accepted'
        )
        read_only_fields = ('contract_duration',)
    
    def validate_stage_number(self, value):
        """Ensure stage_number is between 2 and 5."""
        if value not in [2, 3, 4, 5]:
            raise serializers.ValidationError("Stage number must be between 2 and 5.")
        return value
    
    def validate_agreed_amount(self, value):
        """Ensure agreed_amount is positive."""
        if value <= 0:
            raise serializers.ValidationError("Agreed amount must be greater than zero.")
        return value

    def validate_duration_days(self, value):
        """Ensure duration_days is positive."""
        if value is not None and value <= 0:
            raise serializers.ValidationError("Duration days must be greater than zero.")
        return value
    
    def update(self, instance, validated_data):
        """Update contract with role-based validation."""
        request = self.context.get('request')
        user = request.user
        
        # Get the user's role
        is_technician = hasattr(user, 'technician_profile')
        is_client = hasattr(user, 'client_profile')

        # Handle timeline fields (must be provided together)
        start_date = validated_data.get('start_date')
        duration_days = validated_data.get('duration_days')
        if (start_date is not None) ^ (duration_days is not None):
            raise serializers.ValidationError("start_date and duration_days must be provided together.")
        
        # Prevent updates to completed contracts
        if instance.status in ['completed', 'canceled']:
            raise serializers.ValidationError(f"Cannot modify a {instance.status} contract.")
        
        # Technician can only set amount, stage_number, and timeline
        if is_technician:
            if 'client_accepted' in validated_data or 'technician_accepted' in validated_data:
                # Technician can only set their own acceptance
                if 'client_accepted' in validated_data:
                    validated_data.pop('client_accepted')
                
                if 'technician_accepted' in validated_data:
                    validated_data['technician_accepted'] = True
            
            # Both amount and stages required together
            if ('agreed_amount' in validated_data) or ('stage_number' in validated_data):
                if not all(k in validated_data or getattr(instance, k, None) for k in ['agreed_amount', 'stage_number']):
                    raise serializers.ValidationError("Both agreed amount and stage number are required.")

            # Require start_date and duration_days together for timeline updates
            if (start_date is not None) and (duration_days is not None):
                validated_data['contract_duration'] = start_date + timezone.timedelta(days=duration_days)
        
        # Client can only accept
        if is_client:
            allowed_fields = ['client_accepted']
            for field in validated_data.keys():
                if field not in allowed_fields:
                    validated_data.pop(field)
            
            if 'client_accepted' in validated_data:
                validated_data['client_accepted'] = True
        
        # If client is accepting, check wallet balance
        if is_client and validated_data.get('client_accepted'):
            if instance.status != 'pending_acceptance':
                raise serializers.ValidationError("Contract must be in pending_acceptance status.")
            
            client_wallet = user.wallet
            client_fee = (instance.agreed_amount * instance.PLATFORM_FEE_RATE).quantize(Decimal('0.01'))
            required_total = instance.agreed_amount + client_fee

            if client_wallet.balance < required_total:
                shortfall = required_total - client_wallet.balance
                raise serializers.ValidationError(
                    f"Insufficient funds in wallet. You have {client_wallet.balance} IQD but need "
                    f"{required_total} IQD to initiate this contract (including non-refundable client platform fee of {client_fee} IQD). Please recharge your wallet "
                    f"with at least {shortfall} IQD more."
                )
        
        # Update fields
        for field, value in validated_data.items():
            setattr(instance, field, value)
        
        instance.save()
        return instance


class ContractProposalSerializer(serializers.Serializer):
    """Technician fills proposal fields on a draft contract."""
    work_description = serializers.CharField(required=False)
    agreed_amount = serializers.DecimalField(max_digits=15, decimal_places=2, required=False)
    amount_usd = serializers.DecimalField(max_digits=10, decimal_places=2, required=False)
    duration_days = serializers.IntegerField(required=False, min_value=1)
    start_date = serializers.DateField(required=False)
    stage_number = serializers.ChoiceField(choices=Contract.STAGE_CHOICES, required=False)


class ContractAcceptSerializer(serializers.Serializer):
    """Accept a contract. No required body fields; status derived from auth."""
    pass


class ContractCancelSerializer(serializers.Serializer):
    """Cancel a contract with optional reason."""
    reason = serializers.CharField(required=False, allow_blank=True, max_length=2000)


class TimeExtensionCreateSerializer(serializers.Serializer):
    """Technician creates a time extension request."""
    requested_days = serializers.IntegerField(min_value=1, max_value=30)
    reason = serializers.CharField(max_length=2000, required=False, allow_blank=True)


class ExtensionRespondSerializer(serializers.Serializer):
    """Client responds to an extension request."""
    approve = serializers.BooleanField(default=True)
    client_response = serializers.CharField(required=False, allow_blank=True, max_length=2000)


class ContractFreezeSerializer(serializers.Serializer):
    """Freeze immutable contract snapshot before signatures."""
    pass


class ContractSignatureOtpRequestSerializer(serializers.Serializer):
    """Request OTP email for contract signature."""
    pass


class ContractSignSerializer(serializers.Serializer):
    """Submit OTP to create signature proof."""
    otp_code = serializers.CharField(min_length=6, max_length=6)


class ContractSignatureSerializer(serializers.ModelSerializer):
    """Read-only signature records."""

    class Meta:
        model = ContractSignature
        fields = (
            'id', 'signer_role', 'signature_hash', 'signed_at', 'ip_address', 'user_agent', 'created_at',
        )
        read_only_fields = fields


class ContractDocumentSerializer(serializers.ModelSerializer):
    """Read-only contract document metadata."""
    download_url = serializers.SerializerMethodField()

    class Meta:
        model = ContractDocument
        fields = (
            'id', 'kind', 'sha256', 'mime_type', 'file_size', 'download_url', 'created_at',
        )
        read_only_fields = fields

    def get_download_url(self, obj):
        if not obj.file:
            return None
        request = self.context.get('request')
        if request:
            return request.build_absolute_uri(obj.file.url)
        return obj.file.url


class ContractFinalizeSerializer(serializers.Serializer):
    """Trigger finalization after both signatures."""
    pass


class PublicVerifyCodeSerializer(serializers.Serializer):
    """Public verification payload — no sensitive PII exposed."""
    valid = serializers.BooleanField()
    contract_reference = serializers.CharField()
    version = serializers.IntegerField()
    status = serializers.CharField()
    document_type = serializers.CharField()
    finalized_at = serializers.DateTimeField(allow_null=True)
    client_signature_verified = serializers.BooleanField()
    technician_signature_verified = serializers.BooleanField()
    platform_attestation_verified = serializers.BooleanField()
    document_hash = serializers.CharField(allow_null=True)
    attestation_id = serializers.CharField()


class PublicVerifyPdfSerializer(serializers.Serializer):
    """Upload a PDF for public hash verification."""
    file = serializers.FileField()
