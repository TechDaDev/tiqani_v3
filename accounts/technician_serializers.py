"""
Serializers for technician-specific endpoints.
Handles profile, skills, images, and availability management.
"""

from rest_framework import serializers
from django.db import transaction

from .models import TechnicianProfile, TechnicianImage, TechnicianSkillSet
from category.models import Category, Skill, SubSkill


class TechnicianListSerializer(serializers.ModelSerializer):
    """Serializer for listing available technicians (public view).
    
    Admin users see additional fields:
    - is_complete: Profile completion status
    - incomplete_fields: List of missing required fields
    """

    user_id = serializers.CharField(source='user.id', read_only=True)
    username = serializers.CharField(source='user.username', read_only=True)
    full_name = serializers.CharField(source='user.get_full_name', read_only=True)
    governorate = serializers.CharField(source='user.governorate', read_only=True)
    profile_image = serializers.SerializerMethodField()
    is_complete = serializers.SerializerMethodField()
    incomplete_fields = serializers.SerializerMethodField()

    class Meta:
        model = TechnicianProfile
        fields = (
            'user_id', 'username', 'full_name', 'governorate', 'profile_image',
            'job_title', 'about', 'years_of_expertise', 'is_available', 'rate',
            'is_complete', 'incomplete_fields'
        )
        read_only_fields = fields

    def get_profile_image(self, obj):
        if obj.user.profile_image:
            request = self.context.get('request')
            if request:
                return request.build_absolute_uri(obj.user.profile_image.url)
            return obj.user.profile_image.url
        return None

    def _is_admin(self):
        """Check if the request user is an admin."""
        request = self.context.get('request')
        if request and request.user:
            return request.user.is_authenticated and request.user.is_staff
        return False

    def get_is_complete(self, obj):
        """Return is_complete only for admin users."""
        if self._is_admin():
            return obj.is_complete
        return None

    def get_incomplete_fields(self, obj):
        """Return incomplete fields list only for admin users."""
        if self._is_admin():
            return obj.get_incomplete_fields()
        return None


class TechnicianImageSerializer(serializers.ModelSerializer):
    """Serializer for managing technician portfolio images."""

    class Meta:
        model = TechnicianImage
        fields = ('id', 'image', 'description')
        read_only_fields = ('id',)


class TechnicianSkillSetSerializer(serializers.ModelSerializer):
    """Serializer for managing technician skills, categories, and sub-skills."""

    categories = serializers.PrimaryKeyRelatedField(queryset=Category.objects.all(), many=True, required=False)
    skills = serializers.PrimaryKeyRelatedField(queryset=Skill.objects.all(), many=True, required=False)
    sub_skills = serializers.PrimaryKeyRelatedField(queryset=SubSkill.objects.all(), many=True, required=False)

    categories_detail = serializers.SerializerMethodField()
    skills_detail = serializers.SerializerMethodField()
    sub_skills_detail = serializers.SerializerMethodField()

    class Meta:
        model = TechnicianSkillSet
        fields = (
            'id', 'categories', 'categories_detail',
            'skills', 'skills_detail',
            'sub_skills', 'sub_skills_detail',
            'created_at'
        )
        read_only_fields = ('id', 'created_at')

    def get_categories_detail(self, obj):
        return [{'id': cat.id, 'name': cat.name} for cat in obj.categories.all()]

    def get_skills_detail(self, obj):
        return [{'id': skill.id, 'name': skill.name} for skill in obj.skills.all()]

    def get_sub_skills_detail(self, obj):
        return [{'id': sub.id, 'name': sub.name} for sub in obj.sub_skills.all()]

    def update(self, instance, validated_data):
        with transaction.atomic():
            if 'categories' in validated_data:
                categories = validated_data.pop('categories')
                instance.categories.set(categories)

            if 'skills' in validated_data:
                skills = validated_data.pop('skills')
                instance.skills.set(skills)

            if 'sub_skills' in validated_data:
                sub_skills = validated_data.pop('sub_skills')
                instance.sub_skills.set(sub_skills)

            return super().update(instance, validated_data)


class TechnicianProfileSerializer(serializers.ModelSerializer):
    """Serializer for retrieving and updating technician profile information."""

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
    skill_sets = serializers.SerializerMethodField()
    images = TechnicianImageSerializer(many=True, read_only=True)
    url1 = serializers.SerializerMethodField()
    url2 = serializers.SerializerMethodField()
    identification_documents = serializers.SerializerMethodField()
    wallet_id = serializers.SerializerMethodField()
    balance = serializers.SerializerMethodField()
    approved = serializers.SerializerMethodField()

    class Meta:
        model = TechnicianProfile
        fields = (
            'user_id', 'username', 'full_name', 'email', 'phone_number', 'address', 'date_of_birth',
            'governorate', 'gender', 'profile_image', 'job_title', 'about', 'years_of_expertise',
            'is_available', 'approved', 'is_complete', 'rate', 'last_active',
            'url1', 'url2', 'identification_documents', 'wallet_id', 'balance',
            'skill_sets', 'images'
        )
        read_only_fields = (
            'user_id', 'username', 'full_name', 'email', 'phone_number', 'address', 'date_of_birth',
            'governorate', 'gender', 'profile_image', 'approved', 'is_complete', 'rate', 'last_active',
            'url1', 'url2', 'identification_documents', 'wallet_id', 'balance',
            'skill_sets', 'images'
        )

    def _can_view_sensitive(self, obj):
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

    def get_url1(self, obj):
        return obj.github if self._can_view_sensitive(obj) else None

    def get_url2(self, obj):
        return obj.linkedin if self._can_view_sensitive(obj) else None

    def get_identification_documents(self, obj):
        if self._can_view_sensitive(obj) and obj.identification_documents:
            request = self.context.get('request')
            if request:
                return request.build_absolute_uri(obj.identification_documents.url)
            return obj.identification_documents.url
        return None

    def get_approved(self, obj):
        return obj.approved if self._can_view_sensitive(obj) else None

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

    def get_skill_sets(self, obj):
        skill_set = getattr(obj, 'skill_set', None)
        if not skill_set:
            return {
                "detail": "No skill set assigned yet.",
                "categories": [],
                "categories_detail": [],
                "skills": [],
                "skills_detail": [],
                "sub_skills": [],
                "sub_skills_detail": [],
                "created_at": None,
            }
        return TechnicianSkillSetSerializer(skill_set, context=self.context).data


class TechnicianAvailabilitySerializer(serializers.ModelSerializer):
    """Serializer for updating technician availability status."""

    class Meta:
        model = TechnicianProfile
        fields = ('id', 'is_available')
        read_only_fields = ('id',)


class TechnicianRatingsSerializer(serializers.Serializer):
    """Serializer for displaying technician ratings and review statistics."""

    average_rating = serializers.FloatField(read_only=True)
    total_reviews = serializers.IntegerField(read_only=True)
    rating_breakdown = serializers.DictField(read_only=True)
    recent_reviews = serializers.SerializerMethodField(read_only=True)

    def get_recent_reviews(self, obj):
        # This will be populated by the view
        return obj.get('recent_reviews', [])
