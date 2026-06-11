"""Serializers for review creation, updates, responses, and moderation."""

from rest_framework import serializers
from .models import Review, ReviewReport
from contract.models import Contract


class ReviewPublicSerializer(serializers.ModelSerializer):
    """Public review detail — used for list & detail views."""

    reviewer_name = serializers.SerializerMethodField()
    technician_name = serializers.SerializerMethodField()

    class Meta:
        model = Review
        fields = [
            'id',
            'technician',
            'reviewer',
            'reviewer_name',
            'technician_name',
            'rating',
            'work_quality_rating',
            'communication_rating',
            'timeliness_rating',
            'professionalism_rating',
            'title',
            'comment',
            'technician_response',
            'is_verified',
            'helpful_count',
            'created_at',
            'updated_at',
        ]
        read_only_fields = fields

    def get_reviewer_name(self, obj):
        if obj.reviewer:
            return obj.reviewer.get_full_name() or obj.reviewer.username
        return None

    def get_technician_name(self, obj):
        if obj.technician and obj.technician.user:
            return obj.technician.user.get_full_name() or obj.technician.user.username
        return None


class ReviewCreateSerializer(serializers.ModelSerializer):
    """Used for POST /api/reviews/ — clients create review after completed contract."""

    contract_id = serializers.UUIDField(write_only=True)

    class Meta:
        model = Review
        fields = [
            'contract_id',
            'rating',
            'work_quality_rating',
            'communication_rating',
            'timeliness_rating',
            'professionalism_rating',
            'title',
            'comment',
        ]

    def validate_contract_id(self, value):
        try:
            contract = Contract.objects.get(id=value)
        except Contract.DoesNotExist:
            raise serializers.ValidationError("Contract not found.")

        user = self.context['request'].user

        # Must be the contract client
        if not hasattr(user, 'client_profile') or contract.client.user != user:
            raise serializers.ValidationError("You are not the client for this contract.")

        # Contract must be completed
        if contract.status != 'completed':
            raise serializers.ValidationError("Contract must be completed before reviewing.")

        # Only one review per contract
        if Review.objects.filter(reviewer=user, contract=contract).exists():
            raise serializers.ValidationError("You have already reviewed this contract.")

        self._contract = contract
        return value

    def create(self, validated_data):
        contract = self._contract
        request = self.context['request']

        validated_data.pop('contract_id')
        review = Review.objects.create(
            contract=contract,
            reviewer=request.user,
            technician=contract.technician,
            is_verified=True,
            is_public=True,
            **validated_data,
        )
        return review


class ReviewUpdateSerializer(serializers.ModelSerializer):
    """Used for PATCH /api/reviews/<id>/ — reviewer updates own review."""

    class Meta:
        model = Review
        fields = [
            'rating',
            'work_quality_rating',
            'communication_rating',
            'timeliness_rating',
            'professionalism_rating',
            'title',
            'comment',
        ]
        extra_kwargs = {field: {'required': False} for field in fields}

    def update(self, instance, validated_data):
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save()
        return instance


class ReviewTechnicianResponseSerializer(serializers.ModelSerializer):
    """Used for POST /api/reviews/<id>/respond/."""

    class Meta:
        model = Review
        fields = ['technician_response']

    def validate_technician_response(self, value):
        if not value or not value.strip():
            raise serializers.ValidationError("Response cannot be empty.")
        return value.strip()

    def update(self, instance, validated_data):
        instance.technician_response = validated_data['technician_response']
        instance.save(update_fields=['technician_response', 'updated_at'])
        return instance


class ReviewHelpfulSerializer(serializers.Serializer):
    """Response serializer for helpful action — no input fields needed."""
    helpful_count = serializers.IntegerField(read_only=True)


class ReviewReportSerializer(serializers.ModelSerializer):
    """Used for POST /api/reviews/<id>/report/."""

    class Meta:
        model = ReviewReport
        fields = ['reason', 'comment']
        extra_kwargs = {
            'reason': {'required': True},
            'comment': {'required': False},
        }

