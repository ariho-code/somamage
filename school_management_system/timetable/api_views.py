from rest_framework import filters, viewsets
from rest_framework.decorators import action
from rest_framework.request import Request
from django_filters.rest_framework import DjangoFilterBackend

from core.permissions import IsSchoolAdmin, IsTeacherOrAbove
from core.utils import success_response

from .models import TimetableSlot
from .serializers import TimetableSlotSerializer


class TimetableSlotViewSet(viewsets.ModelViewSet):
    queryset = TimetableSlot.objects.select_related(
        "grade__school", "subject", "teacher"
    ).order_by("grade__name", "day_of_week", "start_time")
    serializer_class = TimetableSlotSerializer
    permission_classes = [IsTeacherOrAbove]
    filter_backends = [DjangoFilterBackend, filters.OrderingFilter]
    filterset_fields = ["grade", "subject", "teacher", "day_of_week"]
    ordering_fields = ["day_of_week", "start_time"]

    def get_queryset(self):
        user = self.request.user
        qs = TimetableSlot.objects.select_related("grade__school", "subject", "teacher")
        if user.role in ("superadmin", "platform_owner"):
            return qs.order_by("grade__name", "day_of_week", "start_time")
        if user.school:
            return qs.filter(
                grade__school=user.school
            ).order_by("grade__name", "day_of_week", "start_time")
        return TimetableSlot.objects.none()

    def get_permissions(self):
        if self.action in ("create", "update", "partial_update", "destroy"):
            return [IsSchoolAdmin()]
        return [IsTeacherOrAbove()]

    @action(detail=False, methods=["get"], url_path="by-grade/(?P<grade_id>[^/.]+)")
    def by_grade(self, request: Request, grade_id: str | None = None):
        """GET /api/v1/timetable/slots/by-grade/{grade_id}/ — full week for a grade."""
        qs = self.get_queryset().filter(grade_id=grade_id)
        serializer = self.get_serializer(qs, many=True)
        return success_response(data=serializer.data)

    @action(detail=False, methods=["get"], url_path="by-teacher/(?P<teacher_id>[^/.]+)")
    def by_teacher(self, request: Request, teacher_id: str | None = None):
        """GET /api/v1/timetable/slots/by-teacher/{teacher_id}/ — full week for a teacher."""
        qs = self.get_queryset().filter(teacher_id=teacher_id)
        serializer = self.get_serializer(qs, many=True)
        return success_response(data=serializer.data)
