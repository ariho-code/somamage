from rest_framework import serializers
from .models import AttendanceRecord


class AttendanceRecordSerializer(serializers.ModelSerializer):
    student_name = serializers.SerializerMethodField()
    status_display = serializers.CharField(source="get_status_display", read_only=True)

    class Meta:
        model = AttendanceRecord
        fields = ["id", "enrollment", "student_name", "date", "status", "status_display", "remark"]
        read_only_fields = ["id"]

    def get_student_name(self, obj: AttendanceRecord) -> str:
        return obj.enrollment.student.get_full_name()


class BulkAttendanceSerializer(serializers.Serializer):
    """Validate a list of attendance records for one class on one date."""
    date = serializers.DateField()
    records = serializers.ListField(
        child=serializers.DictField(),
        min_length=1,
    )

    def validate_records(self, records: list) -> list:
        valid_statuses = {"present", "absent", "late"}
        for i, rec in enumerate(records):
            if "enrollment" not in rec:
                raise serializers.ValidationError(f"Row {i}: 'enrollment' is required.")
            if rec.get("status", "").lower() not in valid_statuses:
                raise serializers.ValidationError(
                    f"Row {i}: status must be one of {valid_statuses}."
                )
        return records
