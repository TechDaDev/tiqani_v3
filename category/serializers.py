from rest_framework import serializers

from category.models import Category, Skill, SubSkill


class SubSkillSerializer(serializers.ModelSerializer):
    class Meta:
        model = SubSkill
        fields = [
            "id",
            "skill",
            "name",
            "description",
            "difficulty_level",
            "is_active",
            "is_delete",
            "order",
            "full_path",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "full_path", "created_at", "updated_at"]


class SkillSlimSerializer(serializers.ModelSerializer):
    class Meta:
        model = Skill
        fields = [
            "id",
            "category",
            "name",
            "description",
            "is_active",
            "is_delete",
            "order",
            "technician_count",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "technician_count", "created_at", "updated_at"]


class SkillSerializer(serializers.ModelSerializer):
    sub_skills = SubSkillSerializer(many=True, read_only=True)

    class Meta:
        model = Skill
        fields = [
            "id",
            "category",
            "name",
            "description",
            "is_active",
            "is_delete",
            "order",
            "technician_count",
            "created_at",
            "updated_at",
            "sub_skills",
        ]
        read_only_fields = ["id", "technician_count", "created_at", "updated_at"]


class CategorySlimSerializer(serializers.ModelSerializer):
    skills = SkillSlimSerializer(many=True, read_only=True)

    class Meta:
        model = Category
        fields = [
            "id",
            "name",
            "description",
            "icon",
            "parent",
            "is_active",
            "is_featured",
            "is_delete",
            "order",
            "skill_count",
            "technician_count",
            "created_at",
            "updated_at",
            "skills",
        ]
        read_only_fields = [
            "id",
            "skill_count",
            "technician_count",
            "created_at",
            "updated_at",
        ]


class CategorySerializer(serializers.ModelSerializer):
    skills = SkillSerializer(many=True, read_only=True)

    class Meta:
        model = Category
        fields = [
            "id",
            "name",
            "description",
            "icon",
            "parent",
            "is_active",
            "is_featured",
            "is_delete",
            "order",
            "skill_count",
            "technician_count",
            "created_at",
            "updated_at",
            "skills",
        ]
        read_only_fields = [
            "id",
            "skill_count",
            "technician_count",
            "created_at",
            "updated_at",
        ]
