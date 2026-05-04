from rest_framework import viewsets, filters, status
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.request import Request
from rest_framework.response import Response
from django_filters.rest_framework import DjangoFilterBackend

from core.mixins import TenantMixin
from core.models import AcademicYear, Notification, School, Term, User
from core.permissions import IsSchoolAdmin, IsPlatformOwner
from core.utils import success_response
from .serializers import (
    AcademicYearSerializer,
    NotificationSerializer,
    SchoolSerializer,
    TermSerializer,
    UserProfileSerializer,
)


class UserViewSet(TenantMixin, viewsets.ModelViewSet):
    queryset = User.objects.all().order_by("last_name", "first_name")
    serializer_class = UserProfileSerializer
    permission_classes = [IsSchoolAdmin]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ["role", "is_active", "school"]
    search_fields = ["first_name", "last_name", "email", "username"]
    ordering_fields = ["last_name", "first_name", "date_joined", "role"]

    def get_queryset(self):
        user = self.request.user
        if user.role in ("superadmin", "platform_owner"):
            return User.objects.all().order_by("last_name", "first_name")
        if user.school:
            return User.objects.filter(school=user.school).order_by("last_name", "first_name")
        return User.objects.none()

    @action(detail=False, methods=["get"], permission_classes=[IsAuthenticated])
    def me(self, request: Request) -> Response:
        return success_response(data=UserProfileSerializer(request.user).data)


class SchoolViewSet(viewsets.ModelViewSet):
    queryset = School.objects.all().order_by("name")
    serializer_class = SchoolSerializer
    permission_classes = [IsSchoolAdmin]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter]
    filterset_fields = ["school_type"]
    search_fields = ["name", "code", "email"]

    def get_queryset(self):
        user = self.request.user
        if user.role in ("superadmin", "platform_owner"):
            return School.objects.all().order_by("name")
        if user.school:
            return School.objects.filter(pk=user.school_id)
        return School.objects.none()


class AcademicYearViewSet(TenantMixin, viewsets.ModelViewSet):
    queryset = AcademicYear.objects.select_related("school").order_by("-start_date")
    serializer_class = AcademicYearSerializer
    permission_classes = [IsSchoolAdmin]
    filter_backends = [DjangoFilterBackend, filters.OrderingFilter]
    filterset_fields = ["school", "is_active"]
    ordering_fields = ["start_date", "end_date", "name"]

    def get_queryset(self):
        user = self.request.user
        if user.role in ("superadmin", "platform_owner"):
            return AcademicYear.objects.select_related("school").order_by("-start_date")
        if user.school:
            return AcademicYear.objects.filter(school=user.school).order_by("-start_date")
        return AcademicYear.objects.none()


class TermViewSet(viewsets.ModelViewSet):
    queryset = Term.objects.select_related("academic_year__school").order_by("-academic_year__start_date", "start_date")
    serializer_class = TermSerializer
    permission_classes = [IsSchoolAdmin]
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ["academic_year"]

    def get_queryset(self):
        user = self.request.user
        if user.role in ("superadmin", "platform_owner"):
            return Term.objects.select_related("academic_year__school").order_by("-academic_year__start_date", "start_date")
        if user.school:
            return Term.objects.filter(academic_year__school=user.school).order_by("-academic_year__start_date", "start_date")
        return Term.objects.none()


class NotificationViewSet(viewsets.ModelViewSet):
    serializer_class = NotificationSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend, filters.OrderingFilter]
    filterset_fields = ["is_read", "notification_type"]
    ordering_fields = ["created_at"]
    http_method_names = ["get", "patch", "delete", "head", "options"]  # no POST — system-generated

    def get_queryset(self):
        return Notification.objects.filter(user=self.request.user).order_by("-created_at")

    @action(detail=True, methods=["patch"])
    def read(self, request: Request, pk: str | None = None) -> Response:
        notification = self.get_object()
        notification.is_read = True
        notification.save(update_fields=["is_read"])
        return success_response(message="Marked as read.")

    @action(detail=False, methods=["patch"])
    def read_all(self, request: Request) -> Response:
        self.get_queryset().filter(is_read=False).update(is_read=True)
        return success_response(message="All notifications marked as read.")
