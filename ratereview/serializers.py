"""Serializers for review creation, updates, responses, and moderation."""

from rest_framework import serializers
from .models import Review, ReviewReport, ReviewModerationAction, UserReputationSnapshot
from contract.models import Contract


class ReviewPublicSerializer(serializers.ModelSerializer):
    """Public review detail — used for list & detail views."""

    reviewer_name = serializers.SerializerMethodField()
    technician_name = serializers.SerializerMethodField()
    reviewee_name = serializers.SerializerMethodField()

    class Meta:
        model = Review
        fields = [
            'id',
            'technician',
            'reviewee',
            'reviewee_name',
            'reviewer',
            'reviewer_role',
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
            'status',
            'is_verified',
            'is_public',
            'helpful_count',
            'reported_count',
            'edit_count',
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

    def get_reviewee_name(self, obj):
        if obj.reviewee:
            return obj.reviewee.get_full_name() or obj.reviewee.username
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

        client_user = contract.client.user
        tech_user = contract.technician.user
        if user not in [client_user, tech_user]:
            raise serializers.ValidationError("You are not a participant for this contract.")

        # Contract must be completed
        if contract.status != 'completed':
            raise serializers.ValidationError("Contract must be completed before reviewing.")

        reviewee = tech_user if user == client_user else client_user

        # Only one review per reviewer/reviewee/contract
        if Review.objects.filter(reviewer=user, reviewee=reviewee, contract=contract).exists():
            raise serializers.ValidationError("You have already reviewed this contract.")

        self._contract = contract
        self._reviewee = reviewee
        return value

    def create(self, validated_data):
        contract = self._contract
        request = self.context['request']

        validated_data.pop('contract_id')
        review = Review.objects.create(
            contract=contract,
            reviewer=request.user,
            reviewee=self._reviewee,
            reviewer_role=request.user.role,
            technician=contract.technician if self._reviewee == contract.technician.user else None,
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


class ContractReviewCreateSerializer(serializers.Serializer):
    """Contract-scoped review payload."""

    rating = serializers.IntegerField(min_value=1, max_value=5)
    title = serializers.CharField(max_length=150, required=False, allow_blank=True)
    comment = serializers.CharField(required=False, allow_blank=True)
    work_quality_rating = serializers.IntegerField(min_value=1, max_value=5, required=False)
    communication_rating = serializers.IntegerField(min_value=1, max_value=5, required=False)
    timeliness_rating = serializers.IntegerField(min_value=1, max_value=5, required=False)
    professionalism_rating = serializers.IntegerField(min_value=1, max_value=5, required=False)


class ReviewEligibilitySerializer(serializers.Serializer):
    eligible = serializers.BooleanField()
    reason_code = serializers.CharField()
    reviewee = serializers.DictField(allow_null=True)
    existing_review = serializers.CharField(allow_null=True)
    editable = serializers.BooleanField()


class UserReputationSnapshotSerializer(serializers.ModelSerializer):
    """Backend-owned transparent reputation aggregate."""

    class Meta:
        model = UserReputationSnapshot
        fields = [
            'user', 'role', 'average_rating', 'review_count',
            'rating_1_count', 'rating_2_count', 'rating_3_count',
            'rating_4_count', 'rating_5_count',
            'completed_contract_count', 'label', 'last_recalculated_at',
        ]
        read_only_fields = fields


class ReviewModerationActionSerializer(serializers.ModelSerializer):
    actor_name = serializers.SerializerMethodField()

    class Meta:
        model = ReviewModerationAction
        fields = ['id', 'action', 'reason', 'actor', 'actor_name', 'created_at']
        read_only_fields = fields

    def get_actor_name(self, obj):
        if obj.actor:
            return obj.actor.get_full_name() or obj.actor.username
        return None
