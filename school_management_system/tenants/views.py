from rest_framework import viewsets, filters
from rest_framework.decorators import action
from rest_framework.response import Response
from django_filters.rest_framework import DjangoFilterBackend

from core.permissions import IsPlatformOwner, IsSchoolAdmin
from core.models import School
from .models import Campus, Platform
from .serializers import CampusSerializer, PlatformSerializer, SchoolSerializer


class PlatformViewSet(viewsets.ModelViewSet):
    queryset = Platform.objects.all()
    serializer_class = PlatformSerializer
    permission_classes = [IsPlatformOwner]
    http_method_names = ["get", "patch", "head", "options"]  # singleton, no create/delete via API


class SchoolViewSet(viewsets.ModelViewSet):
    queryset = School.objects.all().order_by("name")
    serializer_class = SchoolSerializer
    permission_classes = [IsSchoolAdmin]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ["school_type"]
    search_fields = ["name", "code", "email"]
    ordering_fields = ["name", "school_type"]

    def get_queryset(self):
        user = self.request.user
        if user.role in ("superadmin", "platform_owner"):
            return School.objects.all().order_by("name")
        if user.school:
            return School.objects.filter(pk=user.school_id).order_by("name")
        return School.objects.none()

    @action(detail=True, methods=["get"])
    def campuses(self, request, pk=None):
        school = self.get_object()
        campuses = Campus.objects.filter(school=school, is_active=True)
        serializer = CampusSerializer(campuses, many=True)
        return Response({"success": True, "data": serializer.data, "message": "OK", "errors": None})


class CampusViewSet(viewsets.ModelViewSet):
    queryset = Campus.objects.select_related("school", "headteacher").order_by("school__name", "name")
    serializer_class = CampusSerializer
    permission_classes = [IsSchoolAdmin]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter]
    filterset_fields = ["school", "is_main", "is_active"]
    search_fields = ["name", "school__name"]

    def get_queryset(self):
        user = self.request.user
        if user.role in ("superadmin", "platform_owner"):
            return Campus.objects.select_related("school", "headteacher").order_by("school__name", "name")
        if user.school:
            return Campus.objects.filter(school=user.school, is_active=True).select_related("school", "headteacher")
        return Campus.objects.none()
