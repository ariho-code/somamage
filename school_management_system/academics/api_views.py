"""
DRF ViewSets for the academics app.
Kept in api_views.py so existing template views.py is untouched.
"""
from django.http import HttpResponse
from django.shortcuts import get_object_or_404
from rest_framework import filters, status, viewsets
from rest_framework.decorators import action
from rest_framework.request import Request
from rest_framework.response import Response
from django_filters.rest_framework import DjangoFilterBackend

from core.mixins import TenantMixin
from core.permissions import IsSchoolAdmin, IsTeacherOrAbove
from core.utils import error_response, success_response

from .models import (
    Combination, Exam, Grade, MarkEntry,
    ReportCard, Stream, Subject, TeacherSubject,
)
from .serializers import (
    BulkMarkEntrySerializer,
    CombinationSerializer,
    ExamSerializer,
    GradeSerializer,
    MarkEntrySerializer,
    ReportCardSerializer,
    StreamSerializer,
    SubjectSerializer,
    TeacherSubjectSerializer,
)


class GradeViewSet(TenantMixin, viewsets.ModelViewSet):
    queryset = Grade.objects.select_related("school", "class_teacher").order_by("school__name", "level", "name")
    serializer_class = GradeSerializer
    permission_classes = [IsSchoolAdmin]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter]
    filterset_fields = ["school", "level"]
    search_fields = ["name", "code"]

    def get_queryset(self):
        user = self.request.user
        if user.role in ("superadmin", "platform_owner"):
            return Grade.objects.select_related("school", "class_teacher").order_by("school__name", "level", "name")
        if user.school:
            return Grade.objects.filter(school=user.school).select_related("school", "class_teacher").order_by("level", "name")
        return Grade.objects.none()


class SubjectViewSet(viewsets.ModelViewSet):
    queryset = Subject.objects.prefetch_related("papers").order_by("level", "name")
    serializer_class = SubjectSerializer
    permission_classes = [IsSchoolAdmin]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter]
    filterset_fields = ["level", "is_compulsory", "has_papers"]
    search_fields = ["name", "code"]


class CombinationViewSet(TenantMixin, viewsets.ModelViewSet):
    queryset = Combination.objects.prefetch_related("subjects").order_by("name")
    serializer_class = CombinationSerializer
    permission_classes = [IsSchoolAdmin]
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ["grade"]

    def get_queryset(self):
        user = self.request.user
        if user.role in ("superadmin", "platform_owner"):
            return Combination.objects.prefetch_related("subjects").order_by("name")
        if user.school:
            return Combination.objects.filter(
                grade__school=user.school
            ).prefetch_related("subjects").order_by("name")
        return Combination.objects.none()


class StreamViewSet(TenantMixin, viewsets.ModelViewSet):
    queryset = Stream.objects.select_related("school", "grade", "combination").order_by("name")
    serializer_class = StreamSerializer
    permission_classes = [IsSchoolAdmin]
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ["school", "grade", "combination"]

    def get_queryset(self):
        user = self.request.user
        if user.role in ("superadmin", "platform_owner"):
            return Stream.objects.select_related("school", "grade", "combination").order_by("name")
        if user.school:
            return Stream.objects.filter(school=user.school).select_related("school", "grade", "combination").order_by("name")
        return Stream.objects.none()


class ExamViewSet(TenantMixin, viewsets.ModelViewSet):
    queryset = Exam.objects.select_related("school", "term").order_by("-term__start_date", "order")
    serializer_class = ExamSerializer
    permission_classes = [IsSchoolAdmin]
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ["school", "term", "is_active"]

    def get_queryset(self):
        user = self.request.user
        if user.role in ("superadmin", "platform_owner"):
            return Exam.objects.select_related("school", "term").order_by("-term__start_date", "order")
        if user.school:
            return Exam.objects.filter(school=user.school).select_related("school", "term").order_by("-term__start_date", "order")
        return Exam.objects.none()


class MarkEntryViewSet(viewsets.ModelViewSet):
    queryset = MarkEntry.objects.select_related(
        "enrollment__student", "subject", "exam", "teacher"
    ).order_by("exam__term", "subject__name")
    serializer_class = MarkEntrySerializer
    permission_classes = [IsTeacherOrAbove]
    filter_backends = [DjangoFilterBackend, filters.OrderingFilter]
    filterset_fields = ["enrollment", "subject", "exam", "teacher"]

    def get_queryset(self):
        user = self.request.user
        qs = MarkEntry.objects.select_related("enrollment__student", "subject", "exam", "teacher")
        if user.role in ("superadmin", "platform_owner"):
            return qs.order_by("exam__term", "subject__name")
        if user.school:
            return qs.filter(
                enrollment__grade__school=user.school
            ).order_by("exam__term", "subject__name")
        return MarkEntry.objects.none()

    @action(detail=False, methods=["post"], url_path="bulk")
    def bulk_save(self, request: Request) -> Response:
        """
        POST /api/v1/academics/marks/bulk/
        Body: {"marks": [{enrollment, subject, exam, score, ...}, ...]}
        Creates or updates marks in one request (spreadsheet-style entry).
        """
        serializer = BulkMarkEntrySerializer(data=request.data)
        if not serializer.is_valid():
            return error_response("Invalid mark data.", serializer.errors)

        saved = []
        errors = []
        for i, mark_data in enumerate(serializer.validated_data["marks"]):
            try:
                obj, created = MarkEntry.objects.update_or_create(
                    enrollment=mark_data["enrollment"],
                    subject=mark_data["subject"],
                    exam=mark_data["exam"],
                    subject_paper=mark_data.get("subject_paper"),
                    defaults={
                        "score": mark_data["score"],
                        "teacher": request.user,
                    },
                )
                saved.append({"index": i, "id": obj.pk, "created": created})
            except Exception as exc:
                errors.append({"index": i, "error": str(exc)})

        return success_response(
            data={"saved": len(saved), "errors": len(errors), "error_details": errors},
            message=f"{len(saved)} marks saved.",
            status_code=status.HTTP_207_MULTI_STATUS if errors else status.HTTP_200_OK,
        )


class ReportCardViewSet(viewsets.ModelViewSet):
    queryset = ReportCard.objects.select_related(
        "enrollment__student", "enrollment__grade", "term"
    ).order_by("-term__start_date")
    serializer_class = ReportCardSerializer
    permission_classes = [IsTeacherOrAbove]
    filter_backends = [DjangoFilterBackend, filters.OrderingFilter]
    filterset_fields = ["enrollment", "term", "is_published"]
    http_method_names = ["get", "patch", "head", "options"]  # report cards are system-generated

    def get_queryset(self):
        user = self.request.user
        qs = ReportCard.objects.select_related(
            "enrollment__student", "enrollment__grade", "term"
        )
        if user.role in ("superadmin", "platform_owner"):
            return qs.order_by("-term__start_date")
        if user.school:
            return qs.filter(
                enrollment__grade__school=user.school
            ).order_by("-term__start_date")
        return ReportCard.objects.none()

    @action(detail=True, methods=["get"], url_path="pdf")
    def pdf(self, request: Request, pk: str | None = None) -> HttpResponse:
        """
        GET /api/v1/academics/report-cards/{id}/pdf/
        Generate a PDF version of the report card using WeasyPrint.
        """
        report_card = self.get_object()
        grade_level = report_card.enrollment.grade.level

        # Choose the right template based on level
        if grade_level == "A":
            template_name = "academics/report_card_alevel_pdf.html"
        elif grade_level == "O":
            template_name = "academics/report_card_pdf.html"
        else:
            template_name = "academics/report_card_pdf.html"

        try:
            from django.template.loader import render_to_string
            from weasyprint import HTML, CSS
            html_string = render_to_string(template_name, {
                "report_card": report_card,
                "enrollment": report_card.enrollment,
                "student": report_card.enrollment.student,
            }, request=request)
            pdf_file = HTML(string=html_string, base_url=request.build_absolute_uri("/")).write_pdf()
            student_name = report_card.enrollment.student.get_full_name().replace(" ", "_")
            filename = f"ReportCard_{student_name}_{report_card.term.name}.pdf"
            response = HttpResponse(pdf_file, content_type="application/pdf")
            response["Content-Disposition"] = f'attachment; filename="{filename}"'
            return response
        except Exception as exc:
            return error_response(f"PDF generation failed: {exc}")

    @action(detail=False, methods=["post"], url_path="bulk-pdf", permission_classes=[IsSchoolAdmin])
    def bulk_pdf(self, request: Request) -> HttpResponse:
        """
        POST /api/v1/academics/report-cards/bulk-pdf/
        Body: {"report_card_ids": [1, 2, 3], "term_id": 5}
        Returns a ZIP archive of PDFs (or single PDF if one id).
        """
        ids = request.data.get("report_card_ids", [])
        if not ids:
            return error_response("No report card IDs provided.")

        qs = self.get_queryset().filter(pk__in=ids)
        if not qs.exists():
            return error_response("No matching report cards found.")

        import zipfile
        import io as _io
        from django.template.loader import render_to_string
        try:
            from weasyprint import HTML
        except ImportError:
            return error_response("PDF generation library (WeasyPrint) not available.")

        zip_buffer = _io.BytesIO()
        with zipfile.ZipFile(zip_buffer, "w", zipfile.ZIP_DEFLATED) as zf:
            for rc in qs.select_related("enrollment__student", "enrollment__grade", "term"):
                level = rc.enrollment.grade.level
                template = "academics/report_card_alevel_pdf.html" if level == "A" else "academics/report_card_pdf.html"
                html_string = render_to_string(template, {
                    "report_card": rc,
                    "enrollment": rc.enrollment,
                    "student": rc.enrollment.student,
                }, request=request)
                pdf_bytes = HTML(string=html_string, base_url=request.build_absolute_uri("/")).write_pdf()
                name = rc.enrollment.student.get_full_name().replace(" ", "_")
                zf.writestr(f"{name}_{rc.term.name}.pdf", pdf_bytes)

        zip_buffer.seek(0)
        response = HttpResponse(zip_buffer.read(), content_type="application/zip")
        response["Content-Disposition"] = 'attachment; filename="report_cards.zip"'
        return response


class TeacherSubjectViewSet(TenantMixin, viewsets.ModelViewSet):
    queryset = TeacherSubject.objects.select_related("teacher", "subject", "grade").order_by("teacher__last_name")
    serializer_class = TeacherSubjectSerializer
    permission_classes = [IsSchoolAdmin]
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ["teacher", "subject", "grade"]

    def get_queryset(self):
        user = self.request.user
        qs = TeacherSubject.objects.select_related("teacher", "subject", "grade")
        if user.role in ("superadmin", "platform_owner"):
            return qs.order_by("teacher__last_name")
        if user.school:
            return qs.filter(grade__school=user.school).order_by("teacher__last_name")
        return TeacherSubject.objects.none()
