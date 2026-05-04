from rest_framework import serializers
from .models import (
    Combination, Exam, Grade, MarkEntry,
    ReportCard, Stream, Subject, SubjectPaper, TeacherSubject,
)


class GradeSerializer(serializers.ModelSerializer):
    school_name = serializers.CharField(source="school.name", read_only=True)
    level_display = serializers.CharField(source="get_level_display", read_only=True)

    class Meta:
        model = Grade
        fields = ["id", "school", "school_name", "name", "code", "level", "level_display", "class_teacher"]
        read_only_fields = ["id"]


class SubjectPaperSerializer(serializers.ModelSerializer):
    class Meta:
        model = SubjectPaper
        fields = ["id", "subject", "name", "paper_number", "code", "description", "is_active"]
        read_only_fields = ["id"]


class SubjectSerializer(serializers.ModelSerializer):
    papers = SubjectPaperSerializer(many=True, read_only=True)
    level_display = serializers.CharField(source="get_level_display", read_only=True)

    class Meta:
        model = Subject
        fields = [
            "id", "name", "code", "level", "level_display",
            "is_compulsory", "has_papers", "has_elective_papers",
            "paper_selection_mode", "papers",
        ]
        read_only_fields = ["id"]


class CombinationSerializer(serializers.ModelSerializer):
    subjects_detail = SubjectSerializer(source="subjects", many=True, read_only=True)

    class Meta:
        model = Combination
        fields = ["id", "grade", "name", "code", "subjects", "subjects_detail", "subsidiary_choice"]
        read_only_fields = ["id"]


class StreamSerializer(serializers.ModelSerializer):
    class Meta:
        model = Stream
        fields = ["id", "school", "grade", "combination", "name"]
        read_only_fields = ["id"]


class ExamSerializer(serializers.ModelSerializer):
    term_name = serializers.CharField(source="term.name", read_only=True)

    class Meta:
        model = Exam
        fields = [
            "id", "school", "name", "percentage_weight",
            "term", "term_name", "is_active", "order",
        ]
        read_only_fields = ["id"]


class MarkEntrySerializer(serializers.ModelSerializer):
    student_name = serializers.SerializerMethodField()
    subject_name = serializers.CharField(source="subject.name", read_only=True)
    exam_name = serializers.CharField(source="exam.name", read_only=True)

    class Meta:
        model = MarkEntry
        fields = [
            "id", "enrollment", "student_name",
            "subject", "subject_name",
            "subject_paper",
            "exam", "exam_name",
            "score", "grade", "points",
            "teacher",
        ]
        read_only_fields = ["id", "grade", "points"]

    def get_student_name(self, obj: MarkEntry) -> str:
        return obj.enrollment.student.get_full_name()


class BulkMarkEntrySerializer(serializers.Serializer):
    """Validate a list of mark entries for bulk save."""
    marks = MarkEntrySerializer(many=True)

    def validate_marks(self, value: list) -> list:
        if not value:
            raise serializers.ValidationError("At least one mark entry is required.")
        return value


class ReportCardSerializer(serializers.ModelSerializer):
    student_name = serializers.SerializerMethodField()
    grade_name = serializers.SerializerMethodField()
    term_name = serializers.CharField(source="term.name", read_only=True)

    class Meta:
        model = ReportCard
        fields = [
            "id", "enrollment", "student_name", "grade_name",
            "term", "term_name",
            "total_marks", "average_score", "total_points",
            "overall_grade", "position",
            "aggregate", "division",
            "class_teacher_comment", "headteacher_comment",
            "days_present", "days_absent",
            "is_published", "date_created", "date_published",
        ]
        read_only_fields = [
            "id", "total_marks", "average_score", "total_points",
            "overall_grade", "aggregate", "division",
            "date_created", "date_published",
        ]

    def get_student_name(self, obj: ReportCard) -> str:
        return obj.enrollment.student.get_full_name()

    def get_grade_name(self, obj: ReportCard) -> str:
        return obj.enrollment.grade.name


class TeacherSubjectSerializer(serializers.ModelSerializer):
    teacher_name = serializers.SerializerMethodField()
    subject_name = serializers.CharField(source="subject.name", read_only=True)
    grade_name = serializers.CharField(source="grade.name", read_only=True, allow_null=True)

    class Meta:
        model = TeacherSubject
        fields = ["id", "teacher", "teacher_name", "subject", "subject_name", "grade", "grade_name", "papers"]
        read_only_fields = ["id"]

    def get_teacher_name(self, obj: TeacherSubject) -> str:
        return obj.teacher.get_full_name() or obj.teacher.username
