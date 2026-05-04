from rest_framework import serializers
from .models import (
    Assignment,
    AssignmentSubmission,
    Course,
    CourseEnrollment,
    CourseMaterial,
    Lesson,
    LessonCompletion,
    QuizAnswer,
    QuizOption,
    QuizQuestion,
)


class LessonSerializer(serializers.ModelSerializer):
    class Meta:
        model = Lesson
        fields = [
            "id", "course", "title", "description", "content",
            "video_url", "order", "duration_minutes", "is_published",
            "created_at", "updated_at",
        ]
        read_only_fields = ["id", "created_at", "updated_at"]


class CourseMaterialSerializer(serializers.ModelSerializer):
    class Meta:
        model = CourseMaterial
        fields = [
            "id", "course", "title", "material_type", "file", "external_url",
            "description", "created_at",
        ]
        read_only_fields = ["id", "created_at"]


class CourseSerializer(serializers.ModelSerializer):
    instructor_name = serializers.SerializerMethodField()
    enrollment_count = serializers.SerializerMethodField()
    lesson_count = serializers.SerializerMethodField()
    grade_name = serializers.CharField(source="grade.name", read_only=True, default=None)
    subject_name = serializers.CharField(source="subject.name", read_only=True, default=None)

    class Meta:
        model = Course
        fields = [
            "id", "title", "description", "instructor", "instructor_name",
            "school", "grade", "grade_name", "subject", "subject_name",
            "level", "thumbnail", "is_published", "enrollment_open",
            "enrollment_count", "lesson_count", "created_at",
        ]
        read_only_fields = ["id", "created_at"]

    def get_instructor_name(self, obj: Course) -> str:
        return obj.instructor.get_full_name() or obj.instructor.username

    def get_enrollment_count(self, obj: Course) -> int:
        return obj.get_enrollment_count()

    def get_lesson_count(self, obj: Course) -> int:
        return obj.get_lesson_count()


class CourseEnrollmentSerializer(serializers.ModelSerializer):
    course_title = serializers.CharField(source="course.title", read_only=True)
    student_name = serializers.SerializerMethodField()

    class Meta:
        model = CourseEnrollment
        fields = [
            "id", "student", "student_name", "course", "course_title",
            "enrolled_at", "is_active", "progress", "last_accessed",
        ]
        read_only_fields = ["id", "enrolled_at", "progress", "last_accessed"]

    def get_student_name(self, obj: CourseEnrollment) -> str:
        return obj.student.get_full_name() or obj.student.username


class LessonCompletionSerializer(serializers.ModelSerializer):
    class Meta:
        model = LessonCompletion
        fields = [
            "id", "enrollment", "lesson", "completed", "completed_at",
            "time_spent_minutes", "last_accessed",
        ]
        read_only_fields = ["id", "last_accessed"]


class QuizOptionSerializer(serializers.ModelSerializer):
    class Meta:
        model = QuizOption
        fields = ["id", "option_text", "order"]  # is_correct hidden from students


class QuizQuestionSerializer(serializers.ModelSerializer):
    options = QuizOptionSerializer(many=True, read_only=True)

    class Meta:
        model = QuizQuestion
        fields = [
            "id", "assignment", "question_text", "question_type",
            "points", "order", "options",
        ]
        read_only_fields = ["id"]


class AssignmentSerializer(serializers.ModelSerializer):
    course_title = serializers.CharField(source="course.title", read_only=True)
    question_count = serializers.SerializerMethodField()

    class Meta:
        model = Assignment
        fields = [
            "id", "course", "course_title", "title", "description",
            "assignment_type", "due_date", "start_time", "duration_minutes",
            "total_points", "is_published", "exam_pdf", "allow_attachments",
            "question_count", "created_at",
        ]
        read_only_fields = ["id", "created_at"]

    def get_question_count(self, obj: Assignment) -> int:
        return obj.questions.count()


class AssignmentSubmissionSerializer(serializers.ModelSerializer):
    assignment_title = serializers.CharField(source="assignment.title", read_only=True)
    student_name = serializers.SerializerMethodField()
    percentage = serializers.SerializerMethodField()

    class Meta:
        model = AssignmentSubmission
        fields = [
            "id", "assignment", "assignment_title", "student", "student_name",
            "submission_text", "submission_file", "submitted_at", "started_at",
            "completed_at", "score", "total_score", "percentage",
            "feedback", "is_graded", "is_auto_graded",
        ]
        read_only_fields = [
            "id", "submitted_at", "is_auto_graded",
            "score", "total_score", "is_graded",
        ]

    def get_student_name(self, obj: AssignmentSubmission) -> str:
        return obj.student.get_full_name() or obj.student.username

    def get_percentage(self, obj: AssignmentSubmission) -> float:
        return obj.get_percentage()


class QuizAnswerSerializer(serializers.ModelSerializer):
    class Meta:
        model = QuizAnswer
        fields = [
            "id", "submission", "question", "selected_option",
            "text_answer", "is_correct", "points_earned",
        ]
        read_only_fields = ["id", "is_correct", "points_earned"]
