from rest_framework import serializers
from .models import Campus, Platform
from core.models import School


class PlatformSerializer(serializers.ModelSerializer):
    class Meta:
        model = Platform
        fields = ["id", "name", "logo", "contact_email", "is_active", "created_at"]
        read_only_fields = ["id", "created_at"]


class SchoolSerializer(serializers.ModelSerializer):
    campus_count = serializers.SerializerMethodField()

    class Meta:
        model = School
        fields = [
            "id", "name", "code", "school_type", "address",
            "email", "phone", "motto", "is_active",
            "campus_count",
        ]
        read_only_fields = ["id"]

    def get_campus_count(self, obj: School) -> int:
        return getattr(obj, "campuses", obj.__class__.objects).filter(school=obj).count() if hasattr(obj, "campuses") else 0


class CampusSerializer(serializers.ModelSerializer):
    school_name = serializers.CharField(source="school.name", read_only=True)
    headteacher_name = serializers.SerializerMethodField()

    class Meta:
        model = Campus
        fields = [
            "id", "school", "school_name", "name", "is_main",
            "address", "contact_phone", "headteacher", "headteacher_name",
            "is_active", "created_at",
        ]
        read_only_fields = ["id", "created_at"]

    def get_headteacher_name(self, obj: Campus) -> str | None:
        if obj.headteacher:
            return obj.headteacher.get_full_name() or obj.headteacher.username
        return None
