from django.http import HttpResponse
from rest_framework import filters, status, viewsets
from rest_framework.decorators import action
from rest_framework.request import Request
from django_filters.rest_framework import DjangoFilterBackend

from core.permissions import IsBursar, IsSchoolAdmin
from core.utils import error_response, success_response

from .models import FeeBalance, FeePayment, FeeStructure
from .serializers import FeeBalanceSerializer, FeePaymentSerializer, FeeStructureSerializer


class FeeStructureViewSet(viewsets.ModelViewSet):
    queryset = FeeStructure.objects.select_related("grade", "term").order_by("-term__start_date", "grade__name")
    serializer_class = FeeStructureSerializer
    permission_classes = [IsSchoolAdmin]
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ["grade", "term"]

    def get_queryset(self):
        user = self.request.user
        if user.role in ("superadmin", "platform_owner"):
            return FeeStructure.objects.select_related("grade", "term").order_by("-term__start_date", "grade__name")
        if user.school:
            return FeeStructure.objects.filter(
                grade__school=user.school
            ).select_related("grade", "term").order_by("-term__start_date", "grade__name")
        return FeeStructure.objects.none()


class FeePaymentViewSet(viewsets.ModelViewSet):
    queryset = FeePayment.objects.select_related(
        "enrollment__student", "fee_structure", "recorded_by"
    ).order_by("-payment_date")
    serializer_class = FeePaymentSerializer
    permission_classes = [IsBursar]
    filter_backends = [DjangoFilterBackend, filters.OrderingFilter]
    filterset_fields = ["enrollment", "payment_method", "fee_structure"]
    ordering_fields = ["payment_date", "amount_paid"]
    http_method_names = ["get", "post", "head", "options"]  # payments are immutable once made

    def get_queryset(self):
        user = self.request.user
        qs = FeePayment.objects.select_related("enrollment__student", "fee_structure", "recorded_by")
        if user.role in ("superadmin", "platform_owner"):
            return qs.order_by("-payment_date")
        if user.school:
            return qs.filter(
                enrollment__grade__school=user.school
            ).order_by("-payment_date")
        return FeePayment.objects.none()

    @action(detail=True, methods=["get"], url_path="receipt")
    def receipt(self, request: Request, pk: str | None = None) -> HttpResponse:
        """GET /api/v1/fees/payments/{id}/receipt/ — PDF receipt."""
        payment = self.get_object()
        try:
            from django.template.loader import render_to_string
            from weasyprint import HTML
            html = render_to_string("fees/receipt_pdf.html", {"payment": payment}, request=request)
            pdf = HTML(string=html, base_url=request.build_absolute_uri("/")).write_pdf()
            response = HttpResponse(pdf, content_type="application/pdf")
            response["Content-Disposition"] = f'attachment; filename="receipt_{payment.receipt_number}.pdf"'
            return response
        except Exception as exc:
            return error_response(f"PDF generation failed: {exc}")


class FeeBalanceViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = FeeBalance.objects.select_related("enrollment__student", "term").order_by("-last_updated")
    serializer_class = FeeBalanceSerializer
    permission_classes = [IsBursar]
    filter_backends = [DjangoFilterBackend, filters.OrderingFilter]
    filterset_fields = ["enrollment", "term", "is_paid"]

    def get_queryset(self):
        user = self.request.user
        qs = FeeBalance.objects.select_related("enrollment__student", "term")
        if user.role in ("superadmin", "platform_owner"):
            return qs.order_by("-last_updated")
        if user.school:
            return qs.filter(enrollment__grade__school=user.school).order_by("-last_updated")
        return FeeBalance.objects.none()

    @action(detail=False, methods=["get"], url_path="summary")
    def summary(self, request: Request) -> HttpResponse:
        """GET /api/v1/fees/balances/summary/ — totals for the school."""
        qs = self.get_queryset()
        term_id = request.query_params.get("term")
        if term_id:
            qs = qs.filter(term_id=term_id)

        from django.db.models import Sum, Count
        agg = qs.aggregate(
            total_fee=Sum("total_fee"),
            total_paid=Sum("amount_paid"),
            total_balance=Sum("balance"),
            total_students=Count("id"),
            paid_count=Count("id", filter=__import__("django.db.models", fromlist=["Q"]).Q(is_paid=True)),
        )
        return success_response(data=agg)
