from django.db import transaction
from rest_framework import filters, status, viewsets
from rest_framework.decorators import action
from rest_framework.request import Request
from django_filters.rest_framework import DjangoFilterBackend

from core.permissions import IsTeacherOrAbove
from core.utils import error_response, success_response

from .models import AttendanceRecord
from .serializers import AttendanceRecordSerializer, BulkAttendanceSerializer


class AttendanceRecordViewSet(viewsets.ModelViewSet):
    queryset = AttendanceRecord.objects.select_related(
        "enrollment__student", "enrollment__grade"
    ).order_by("-date")
    serializer_class = AttendanceRecordSerializer
    permission_classes = [IsTeacherOrAbove]
    filter_backends = [DjangoFilterBackend, filters.OrderingFilter]
    filterset_fields = ["enrollment", "date", "status"]
    ordering_fields = ["date"]

    def get_queryset(self):
        user = self.request.user
        qs = AttendanceRecord.objects.select_related("enrollment__student", "enrollment__grade")
        if user.role in ("superadmin", "platform_owner"):
            return qs.order_by("-date")
        if user.school:
            return qs.filter(
                enrollment__grade__school=user.school
            ).order_by("-date")
        return AttendanceRecord.objects.none()

    @action(detail=False, methods=["post"], url_path="bulk")
    def bulk_record(self, request: Request):
        """
        POST /api/v1/attendance/bulk/
        Body: {
          "date": "2024-03-15",
          "records": [
            {"enrollment": 1, "status": "present", "remark": ""},
            {"enrollment": 2, "status": "absent", "remark": "Sick"},
            ...
          ]
        }
        Creates or updates attendance for a whole class at once.
        """
        serializer = BulkAttendanceSerializer(data=request.data)
        if not serializer.is_valid():
            return error_response("Invalid data.", serializer.errors)

        date = serializer.validated_data["date"]
        records = serializer.validated_data["records"]
        saved, errors = [], []

        with transaction.atomic():
            for i, rec in enumerate(records):
                try:
                    obj, created = AttendanceRecord.objects.update_or_create(
                        enrollment_id=rec["enrollment"],
                        date=date,
                        defaults={
                            "status": rec["status"].lower(),
                            "remark": rec.get("remark", ""),
                        },
                    )
                    saved.append({"enrollment": rec["enrollment"], "created": created})
                except Exception as exc:
                    errors.append({"index": i, "enrollment": rec.get("enrollment"), "error": str(exc)})

        return success_response(
            data={"saved": len(saved), "errors": len(errors), "error_details": errors},
            message=f"{len(saved)} attendance records saved for {date}.",
            status_code=status.HTTP_207_MULTI_STATUS if errors else status.HTTP_200_OK,
        )

    @action(detail=False, methods=["get"], url_path="report")
    def report(self, request: Request):
        """
        GET /api/v1/attendance/report/?enrollment=1&start=2024-01-01&end=2024-03-31
        Returns present/absent/late counts for an enrollment over a date range.
        """
        enrollment_id = request.query_params.get("enrollment")
        start = request.query_params.get("start")
        end = request.query_params.get("end")

        if not enrollment_id:
            return error_response("enrollment query param is required.")

        qs = self.get_queryset().filter(enrollment_id=enrollment_id)
        if start:
            qs = qs.filter(date__gte=start)
        if end:
            qs = qs.filter(date__lte=end)

        from django.db.models import Count
        counts = qs.values("status").annotate(count=Count("id"))
        summary = {row["status"]: row["count"] for row in counts}
        total = sum(summary.values())

        return success_response(data={
            "enrollment": enrollment_id,
            "start": start,
            "end": end,
            "total_days": total,
            "present": summary.get("present", 0),
            "absent": summary.get("absent", 0),
            "late": summary.get("late", 0),
        })
