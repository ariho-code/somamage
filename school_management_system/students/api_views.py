"""
DRF ViewSets for the students app.
Kept in api_views.py so the existing template-based views.py is untouched.
"""
import csv
import io
import traceback
from typing import Any

from django.db import transaction
from rest_framework import filters, status, viewsets
from rest_framework.decorators import action
from rest_framework.parsers import FormParser, MultiPartParser
from rest_framework.permissions import IsAuthenticated
from rest_framework.request import Request
from rest_framework.response import Response
from django_filters.rest_framework import DjangoFilterBackend

from core.mixins import TenantMixin
from core.permissions import IsSchoolAdmin, IsTeacherOrAbove
from core.utils import error_response, success_response

from .models import Enrollment, EnrollmentSubject, Guardian, Student
from .serializers import (
    BulkStudentRowSerializer,
    EnrollmentSerializer,
    EnrollmentSubjectSerializer,
    GuardianSerializer,
    StudentListSerializer,
    StudentSerializer,
)


class GuardianViewSet(TenantMixin, viewsets.ModelViewSet):
    queryset = Guardian.objects.all().order_by("name")
    serializer_class = GuardianSerializer
    permission_classes = [IsSchoolAdmin]
    filter_backends = [filters.SearchFilter]
    search_fields = ["name", "phone", "email"]


class StudentViewSet(viewsets.ModelViewSet):
    queryset = Student.objects.prefetch_related("enrollments__grade").order_by("last_name", "first_name")
    permission_classes = [IsTeacherOrAbove]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ["gender"]
    search_fields = ["first_name", "last_name", "admission_number", "index_number"]
    ordering_fields = ["last_name", "first_name", "admission_number"]

    def get_serializer_class(self):
        if self.action == "list":
            return StudentListSerializer
        return StudentSerializer

    def get_queryset(self):
        user = self.request.user
        qs = Student.objects.prefetch_related("enrollments__grade__school")
        if user.role in ("superadmin", "platform_owner"):
            return qs.order_by("last_name", "first_name")
        if user.school:
            return qs.filter(
                enrollments__grade__school=user.school,
                enrollments__is_active=True,
            ).distinct().order_by("last_name", "first_name")
        return Student.objects.none()

    @action(detail=True, methods=["get"])
    def enrollments(self, request: Request, pk: str | None = None) -> Response:
        student = self.get_object()
        serializer = EnrollmentSerializer(
            student.enrollments.select_related("grade", "academic_year", "combination").all(),
            many=True,
        )
        return success_response(data=serializer.data)

    # ── Bulk upload ───────────────────────────────────────────────────────────

    @action(
        detail=False,
        methods=["post"],
        url_path="bulk-upload",
        parser_classes=[MultiPartParser, FormParser],
        permission_classes=[IsSchoolAdmin],
    )
    def bulk_upload(self, request: Request) -> Response:
        """
        Upload an Excel (.xlsx) or CSV file to register students in bulk.

        Expected columns (case-insensitive, any order):
          first_name, last_name, gender, date_of_birth,
          guardian_name, guardian_phone, guardian_email,
          admission_number, blood_group,
          emergency_contact_name, emergency_contact_phone

        Returns a summary: created, skipped (duplicates), errors per row.
        """
        file_obj = request.FILES.get("file")
        if not file_obj:
            return error_response("No file provided. Upload a .xlsx or .csv file.")

        filename = file_obj.name.lower()
        try:
            if filename.endswith(".csv"):
                rows = _parse_csv(file_obj)
            elif filename.endswith((".xlsx", ".xls")):
                rows = _parse_excel(file_obj)
            else:
                return error_response("Unsupported file format. Upload .xlsx or .csv.")
        except Exception as exc:
            return error_response(f"Could not read file: {exc}")

        if not rows:
            return error_response("File is empty or has no data rows.")

        created: list[dict] = []
        skipped: list[dict] = []
        errors: list[dict] = []

        for idx, row in enumerate(rows, start=2):  # row 1 = header
            serializer = BulkStudentRowSerializer(data=row)
            if not serializer.is_valid():
                errors.append({"row": idx, "data": row, "errors": serializer.errors})
                continue

            data = serializer.validated_data
            try:
                with transaction.atomic():
                    # Duplicate check by admission number (if provided)
                    admission = data.get("admission_number") or ""
                    if admission and Student.objects.filter(admission_number=admission).exists():
                        skipped.append({"row": idx, "reason": f"Admission {admission} already exists"})
                        continue

                    # Guardian
                    guardian = None
                    if data.get("guardian_name"):
                        guardian, _ = Guardian.objects.get_or_create(
                            name=data["guardian_name"],
                            phone=data.get("guardian_phone", ""),
                            defaults={"email": data.get("guardian_email", "")},
                        )

                    student = Student.objects.create(
                        first_name=data["first_name"],
                        last_name=data["last_name"],
                        gender=data.get("gender", ""),
                        date_of_birth=data.get("date_of_birth"),
                        guardian=guardian,
                        admission_number=admission or None,
                        blood_group=data.get("blood_group", ""),
                        emergency_contact_name=data.get("emergency_contact_name", ""),
                        emergency_contact_phone=data.get("emergency_contact_phone", ""),
                    )
                    created.append({
                        "row": idx,
                        "admission_number": student.admission_number,
                        "name": student.get_full_name(),
                    })
            except Exception as exc:
                errors.append({"row": idx, "data": row, "errors": str(exc)})

        return success_response(
            data={
                "created": len(created),
                "skipped": len(skipped),
                "errors": len(errors),
                "created_students": created,
                "skipped_students": skipped,
                "error_details": errors,
            },
            message=f"{len(created)} students created, {len(skipped)} skipped, {len(errors)} errors.",
            status_code=status.HTTP_207_MULTI_STATUS if errors else status.HTTP_201_CREATED,
        )

    @action(detail=False, methods=["get"], url_path="bulk-upload/template")
    def bulk_upload_template(self, request: Request) -> Response:
        """Return the expected column headers as a downloadable CSV template."""
        from django.http import HttpResponse
        response = HttpResponse(content_type="text/csv")
        response["Content-Disposition"] = 'attachment; filename="student_upload_template.csv"'
        writer = csv.writer(response)
        writer.writerow([
            "first_name", "last_name", "gender", "date_of_birth",
            "guardian_name", "guardian_phone", "guardian_email",
            "admission_number", "blood_group",
            "emergency_contact_name", "emergency_contact_phone",
        ])
        writer.writerow([
            "John", "Doe", "M", "2010-05-15",
            "Jane Doe", "0700000000", "jane@example.com",
            "", "O+", "Jane Doe", "0700000000",
        ])
        return response


class EnrollmentViewSet(viewsets.ModelViewSet):
    queryset = Enrollment.objects.select_related("student", "grade", "academic_year").order_by("-academic_year__start_date")
    serializer_class = EnrollmentSerializer
    permission_classes = [IsSchoolAdmin]
    filter_backends = [DjangoFilterBackend, filters.OrderingFilter]
    filterset_fields = ["student", "grade", "academic_year", "is_active"]

    def get_queryset(self):
        user = self.request.user
        if user.role in ("superadmin", "platform_owner"):
            return Enrollment.objects.select_related("student", "grade", "academic_year").order_by("-academic_year__start_date")
        if user.school:
            return Enrollment.objects.filter(grade__school=user.school).select_related(
                "student", "grade", "academic_year"
            ).order_by("-academic_year__start_date")
        return Enrollment.objects.none()


# ── Helpers ───────────────────────────────────────────────────────────────────

def _normalise_headers(headers: list[str]) -> list[str]:
    return [h.strip().lower().replace(" ", "_") for h in headers]


def _parse_csv(file_obj: Any) -> list[dict]:
    text = file_obj.read().decode("utf-8-sig")
    reader = csv.DictReader(io.StringIO(text))
    headers = _normalise_headers(reader.fieldnames or [])
    rows = []
    for row in reader:
        normalised = {k.strip().lower().replace(" ", "_"): (v or "").strip() for k, v in row.items()}
        rows.append(normalised)
    return rows


def _parse_excel(file_obj: Any) -> list[dict]:
    import openpyxl
    wb = openpyxl.load_workbook(file_obj, read_only=True, data_only=True)
    ws = wb.active
    rows_iter = ws.iter_rows(values_only=True)
    headers = _normalise_headers([str(c) if c is not None else "" for c in next(rows_iter, [])])
    rows = []
    for row in rows_iter:
        values = [str(c).strip() if c is not None else "" for c in row]
        if not any(values):
            continue
        rows.append(dict(zip(headers, values)))
    wb.close()
    return rows
