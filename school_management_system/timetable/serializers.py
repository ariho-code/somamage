from rest_framework import serializers
from .models import TimetableSlot


class TimetableSlotSerializer(serializers.ModelSerializer):
    grade_name = serializers.CharField(source="grade.name", read_only=True)
    subject_name = serializers.CharField(source="subject.name", read_only=True)
    teacher_name = serializers.SerializerMethodField()
    day_display = serializers.CharField(source="get_day_of_week_display", read_only=True)

    class Meta:
        model = TimetableSlot
        fields = [
            "id", "grade", "grade_name",
            "subject", "subject_name",
            "teacher", "teacher_name",
            "day_of_week", "day_display",
            "start_time", "end_time", "room",
        ]
        read_only_fields = ["id"]

    def get_teacher_name(self, obj: TimetableSlot) -> str | None:
        if obj.teacher:
            return obj.teacher.get_full_name() or obj.teacher.username
        return None

    def validate(self, attrs: dict) -> dict:
        start = attrs.get("start_time")
        end = attrs.get("end_time")
        if start and end and start >= end:
            raise serializers.ValidationError({"end_time": "End time must be after start time."})
        return attrs
