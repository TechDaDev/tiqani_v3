"""
Serializers for client-specific endpoints.
Handles profile information with sensitive field masking.
"""

from rest_framework import serializers
from .models import ClientProfile


class ClientProfileSerializer(serializers.ModelSerializer):
    """Serializer for retrieving and updating client profile information."""

    user_id = serializers.CharField(source='user.id', read_only=True)
    username = serializers.CharField(source='user.username', read_only=True)
    full_name = serializers.CharField(source='user.get_full_name', read_only=True)
    email = serializers.SerializerMethodField()
    phone_number = serializers.SerializerMethodField()
    address = serializers.SerializerMethodField()
    date_of_birth = serializers.SerializerMethodField()
    governorate = serializers.CharField(source='user.governorate', read_only=True)
    gender = serializers.CharField(source='user.gender', read_only=True)
    profile_image = serializers.SerializerMethodField()
    age = serializers.IntegerField(source='user.age', read_only=True)
    wallet_id = serializers.SerializerMethodField()
    balance = serializers.SerializerMethodField()

    class Meta:
        model = ClientProfile
        fields = (
            'user_id', 'username', 'full_name', 'email', 'phone_number', 'address', 'date_of_birth',
            'governorate', 'gender', 'profile_image', 'age', 'is_complete',
            'wallet_id', 'balance', 'created_at'
        )
        read_only_fields = (
            'user_id', 'username', 'full_name', 'email', 'phone_number', 'address', 'date_of_birth',
            'governorate', 'gender', 'profile_image', 'age', 'is_complete',
            'wallet_id', 'balance', 'created_at'
        )

    def _can_view_sensitive(self, obj):
        """Check if user can view sensitive information (email, phone, address, DOB, balance)."""
        request = self.context.get('request')
        user = getattr(request, 'user', None)
        if not user or not user.is_authenticated:
            return False
        return user.is_staff or user == obj.user

    def get_email(self, obj):
        return obj.user.email if self._can_view_sensitive(obj) else None

    def get_phone_number(self, obj):
        return obj.user.phone_number if self._can_view_sensitive(obj) else None

    def get_address(self, obj):
        return obj.user.address if self._can_view_sensitive(obj) else None

    def get_date_of_birth(self, obj):
        return obj.user.date_of_birth if self._can_view_sensitive(obj) else None

    def get_wallet_id(self, obj):
        wallet = getattr(obj.user, 'wallet', None)
        return wallet.transaction_id if wallet else None

    def get_balance(self, obj):
        if not self._can_view_sensitive(obj):
            return None
        wallet = getattr(obj.user, 'wallet', None)
        return str(wallet.balance) if wallet else None

    def get_profile_image(self, obj):
        if obj.user.profile_image:
            request = self.context.get('request')
            if request:
                return request.build_absolute_uri(obj.user.profile_image.url)
            return obj.user.profile_image.url
        return None


class IncompleteFieldsSerializer(serializers.Serializer):
    """Serializer for returning incomplete profile fields."""

    is_complete = serializers.BooleanField(read_only=True)
    incomplete_fields = serializers.ListField(child=serializers.CharField(), read_only=True)
    total_required = serializers.IntegerField(read_only=True)
    completed_count = serializers.IntegerField(read_only=True)
    completion_percentage = serializers.FloatField(read_only=True)
