from typing import Any

from django.db import transaction
from django.utils import timezone
from rest_framework import filters, status, viewsets
from rest_framework.decorators import action
from rest_framework.request import Request
from rest_framework.response import Response
from django_filters.rest_framework import DjangoFilterBackend

from core.permissions import IsSchoolAdmin, IsTeacherOrAbove
from core.utils import error_response, success_response

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
from .serializers import (
    AssignmentSerializer,
    AssignmentSubmissionSerializer,
    CourseEnrollmentSerializer,
    CourseMaterialSerializer,
    CourseSerializer,
    LessonCompletionSerializer,
    LessonSerializer,
    QuizAnswerSerializer,
    QuizQuestionSerializer,
)


class CourseViewSet(viewsets.ModelViewSet):
    queryset = Course.objects.select_related("instructor", "school", "grade", "subject").order_by("-created_at")
    serializer_class = CourseSerializer
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ["grade", "subject", "level", "is_published"]
    search_fields = ["title", "description"]
    ordering_fields = ["created_at", "title"]

    def get_permissions(self) -> list[Any]:
        if self.action in ("create", "update", "partial_update", "destroy"):
            return [IsTeacherOrAbove()]
        return [IsTeacherOrAbove()]

    def get_queryset(self):
        user = self.request.user
        qs = Course.objects.select_related("instructor", "school", "grade", "subject")
        if user.role in ("superadmin", "platform_owner"):
            return qs.order_by("-created_at")
        if user.school:
            return qs.filter(school=user.school).order_by("-created_at")
        return Course.objects.none()

    @action(detail=True, methods=["get"], url_path="lessons")
    def lessons(self, request: Request, pk: Any = None) -> Response:
        """GET /api/v1/elearning/courses/{id}/lessons/"""
        course = self.get_object()
        lessons = course.lessons.filter(is_published=True).order_by("order", "created_at")
        serializer = LessonSerializer(lessons, many=True)
        return success_response(data=serializer.data)

    @action(detail=True, methods=["get"], url_path="materials")
    def materials(self, request: Request, pk: Any = None) -> Response:
        """GET /api/v1/elearning/courses/{id}/materials/"""
        course = self.get_object()
        materials = course.materials.all().order_by("title")
        serializer = CourseMaterialSerializer(materials, many=True)
        return success_response(data=serializer.data)

    @action(detail=True, methods=["get"], url_path="assignments")
    def assignments(self, request: Request, pk: Any = None) -> Response:
        """GET /api/v1/elearning/courses/{id}/assignments/"""
        course = self.get_object()
        assignments = course.assignments.filter(is_published=True).order_by("-created_at")
        serializer = AssignmentSerializer(assignments, many=True)
        return success_response(data=serializer.data)

    @action(detail=True, methods=["post"], url_path="enroll")
    def enroll(self, request: Request, pk: Any = None) -> Response:
        """POST /api/v1/elearning/courses/{id}/enroll/ — enrol current user."""
        course = self.get_object()
        if not course.enrollment_open:
            return error_response("Enrollment is currently closed for this course.", status_code=400)
        enrollment, created = CourseEnrollment.objects.get_or_create(
            student=request.user,
            course=course,
            defaults={"is_active": True},
        )
        if not created and not enrollment.is_active:
            enrollment.is_active = True
            enrollment.save(update_fields=["is_active"])
        serializer = CourseEnrollmentSerializer(enrollment)
        msg = "Enrolled successfully." if created else "Already enrolled."
        return success_response(data=serializer.data, message=msg)


class LessonViewSet(viewsets.ModelViewSet):
    queryset = Lesson.objects.select_related("course").order_by("order", "created_at")
    serializer_class = LessonSerializer
    permission_classes = [IsTeacherOrAbove]
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ["course", "is_published"]

    def get_queryset(self):
        user = self.request.user
        qs = Lesson.objects.select_related("course__school")
        if user.role in ("superadmin", "platform_owner"):
            return qs.order_by("order")
        if user.school:
            return qs.filter(course__school=user.school).order_by("order")
        return Lesson.objects.none()

    @action(detail=True, methods=["post"], url_path="complete")
    def complete(self, request: Request, pk: Any = None) -> Response:
        """POST /api/v1/elearning/lessons/{id}/complete/ — mark lesson complete."""
        lesson = self.get_object()
        enrollment = CourseEnrollment.objects.filter(
            student=request.user, course=lesson.course, is_active=True
        ).first()
        if not enrollment:
            return error_response("You are not enrolled in this course.", status_code=403)
        completion, _ = LessonCompletion.objects.update_or_create(
            enrollment=enrollment,
            lesson=lesson,
            defaults={
                "completed": True,
                "completed_at": timezone.now(),
                "time_spent_minutes": request.data.get("time_spent_minutes", 0),
            },
        )
        enrollment.update_progress()
        serializer = LessonCompletionSerializer(completion)
        return success_response(data=serializer.data, message="Lesson marked as complete.")


class AssignmentViewSet(viewsets.ModelViewSet):
    queryset = Assignment.objects.select_related("course").order_by("-created_at")
    serializer_class = AssignmentSerializer
    permission_classes = [IsTeacherOrAbove]
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ["course", "assignment_type", "is_published"]

    def get_queryset(self):
        user = self.request.user
        qs = Assignment.objects.select_related("course__school")
        if user.role in ("superadmin", "platform_owner"):
            return qs.order_by("-created_at")
        if user.school:
            return qs.filter(course__school=user.school).order_by("-created_at")
        return Assignment.objects.none()

    @action(detail=True, methods=["get"], url_path="questions")
    def questions(self, request: Request, pk: Any = None) -> Response:
        """GET /api/v1/elearning/assignments/{id}/questions/"""
        assignment = self.get_object()
        questions = assignment.questions.prefetch_related("options").order_by("order")
        serializer = QuizQuestionSerializer(questions, many=True)
        return success_response(data=serializer.data)

    @action(detail=True, methods=["get"], url_path="submissions")
    def submissions(self, request: Request, pk: Any = None) -> Response:
        """GET /api/v1/elearning/assignments/{id}/submissions/ — teacher view."""
        assignment = self.get_object()
        subs = assignment.submissions.select_related("student").order_by("-submitted_at")
        serializer = AssignmentSubmissionSerializer(subs, many=True)
        return success_response(data=serializer.data)


class AssignmentSubmissionViewSet(viewsets.ModelViewSet):
    queryset = AssignmentSubmission.objects.select_related(
        "assignment__course", "student"
    ).order_by("-submitted_at")
    serializer_class = AssignmentSubmissionSerializer
    permission_classes = [IsTeacherOrAbove]
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ["assignment", "student", "is_graded"]
    http_method_names = ["get", "post", "patch", "head", "options"]  # no DELETE

    def get_queryset(self):
        user = self.request.user
        qs = AssignmentSubmission.objects.select_related("assignment__course__school", "student")
        if user.role in ("superadmin", "platform_owner"):
            return qs.order_by("-submitted_at")
        if user.role == "student":
            return qs.filter(student=user).order_by("-submitted_at")
        if user.school:
            return qs.filter(
                assignment__course__school=user.school
            ).order_by("-submitted_at")
        return AssignmentSubmission.objects.none()

    def perform_create(self, serializer: AssignmentSubmissionSerializer) -> None:
        serializer.save(student=self.request.user)

    @action(detail=True, methods=["patch"], url_path="grade")
    def grade(self, request: Request, pk: Any = None) -> Response:
        """PATCH /api/v1/elearning/submissions/{id}/grade/ — teacher grades submission."""
        submission = self.get_object()
        score = request.data.get("score")
        feedback = request.data.get("feedback", "")
        if score is None:
            return error_response("score is required.", status_code=400)
        submission.score = score
        submission.total_score = submission.assignment.total_points
        submission.feedback = feedback
        submission.is_graded = True
        submission.completed_at = timezone.now()
        submission.save(update_fields=["score", "total_score", "feedback", "is_graded", "completed_at"])
        serializer = AssignmentSubmissionSerializer(submission)
        return success_response(data=serializer.data, message="Submission graded.")


class CourseEnrollmentViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = CourseEnrollment.objects.select_related("student", "course").order_by("-enrolled_at")
    serializer_class = CourseEnrollmentSerializer
    permission_classes = [IsTeacherOrAbove]
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ["course", "student", "is_active"]

    def get_queryset(self):
        user = self.request.user
        qs = CourseEnrollment.objects.select_related("student", "course__school")
        if user.role in ("superadmin", "platform_owner"):
            return qs.order_by("-enrolled_at")
        if user.role == "student":
            return qs.filter(student=user).order_by("-enrolled_at")
        if user.school:
            return qs.filter(course__school=user.school).order_by("-enrolled_at")
        return CourseEnrollment.objects.none()
