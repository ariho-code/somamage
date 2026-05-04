from rest_framework import serializers
from .models import Guardian, Student, Enrollment, EnrollmentSubject


class GuardianSerializer(serializers.ModelSerializer):
    class Meta:
        model = Guardian
        fields = ["id", "name", "phone", "email", "address"]
        read_only_fields = ["id"]


class StudentSerializer(serializers.ModelSerializer):
    guardian_detail = GuardianSerializer(source="guardian", read_only=True)
    full_name = serializers.SerializerMethodField()
    current_grade = serializers.SerializerMethodField()

    class Meta:
        model = Student
        fields = [
            "id", "first_name", "last_name", "full_name",
            "admission_number", "index_number",
            "date_of_birth", "gender",
            "guardian", "guardian_detail",
            "has_disabilities", "disabilities",
            "has_chronic_diseases", "chronic_diseases",
            "has_special_care_needs", "special_care_needs",
            "medical_notes", "emergency_contact_name", "emergency_contact_phone",
            "blood_group", "allergies",
            "current_grade",
        ]
        read_only_fields = ["id", "admission_number"]

    def get_full_name(self, obj: Student) -> str:
        return obj.get_full_name()

    def get_current_grade(self, obj: Student) -> str | None:
        active = obj.enrollments.filter(is_active=True).select_related("grade").first()
        return active.grade.name if active else None


class StudentListSerializer(serializers.ModelSerializer):
    """Lightweight serializer for list views."""
    full_name = serializers.SerializerMethodField()
    current_grade = serializers.SerializerMethodField()

    class Meta:
        model = Student
        fields = ["id", "admission_number", "full_name", "gender", "current_grade"]

    def get_full_name(self, obj: Student) -> str:
        return obj.get_full_name()

    def get_current_grade(self, obj: Student) -> str | None:
        active = obj.enrollments.filter(is_active=True).select_related("grade").first()
        return active.grade.name if active else None


class EnrollmentSerializer(serializers.ModelSerializer):
    student_name = serializers.CharField(source="student.get_full_name", read_only=True)
    grade_name = serializers.CharField(source="grade.name", read_only=True)
    academic_year_name = serializers.CharField(source="academic_year.name", read_only=True)

    class Meta:
        model = Enrollment
        fields = [
            "id", "student", "student_name",
            "grade", "grade_name",
            "combination", "stream",
            "academic_year", "academic_year_name",
            "date_joined", "date_left", "is_active",
        ]
        read_only_fields = ["id"]


class EnrollmentSubjectSerializer(serializers.ModelSerializer):
    subject_name = serializers.CharField(source="subject.name", read_only=True)

    class Meta:
        model = EnrollmentSubject
        fields = ["id", "enrollment", "subject", "subject_name", "is_compulsory", "assigned_date"]
        read_only_fields = ["id", "assigned_date"]


# ── Bulk Upload Serializer ────────────────────────────────────────────────────

class BulkStudentRowSerializer(serializers.Serializer):
    """Validates a single row from a bulk upload file."""
    first_name = serializers.CharField(max_length=100)
    last_name = serializers.CharField(max_length=100)
    gender = serializers.ChoiceField(choices=["M", "F", "O", "Male", "Female", "Other"], required=False, default="")
    date_of_birth = serializers.DateField(required=False, allow_null=True,
                                          input_formats=["%Y-%m-%d", "%d/%m/%Y", "%m/%d/%Y", "%d-%m-%Y"])
    guardian_name = serializers.CharField(max_length=255, required=False, allow_blank=True)
    guardian_phone = serializers.CharField(max_length=32, required=False, allow_blank=True)
    guardian_email = serializers.EmailField(required=False, allow_blank=True)
    admission_number = serializers.CharField(max_length=50, required=False, allow_blank=True)
    blood_group = serializers.CharField(max_length=10, required=False, allow_blank=True)
    emergency_contact_name = serializers.CharField(max_length=255, required=False, allow_blank=True)
    emergency_contact_phone = serializers.CharField(max_length=32, required=False, allow_blank=True)

    def validate_gender(self, value: str) -> str:
        mapping = {"male": "M", "female": "F", "other": "O", "m": "M", "f": "F", "o": "O"}
        return mapping.get(value.lower(), value.upper()[:1]) if value else ""
