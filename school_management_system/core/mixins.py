from typing import Any
from rest_framework.request import Request


class TenantMixin:
    """
    Automatically filter querysets by the requesting user's school.
    Platform owners / superadmins see everything.
    """

    request: Request

    def get_queryset(self) -> Any:
        qs = super().get_queryset()  # type: ignore[misc]
        user = self.request.user
        if not user or not user.is_authenticated:
            return qs.none()
        if user.role in ("superadmin", "platform_owner"):
            return qs
        school = getattr(user, "school", None)
        if school is None:
            return qs.none()
        # Try filtering by school FK first, fall back to school via enrollment/academic_year
        model = qs.model
        field_names = [f.name for f in model._meta.get_fields()]
        if "school" in field_names:
            return qs.filter(school=school)
        return qs


class AuditMixin:
    """
    Automatically stamp created_by / updated_by on save.
    Requires model to have created_by and updated_by ForeignKey fields.
    """

    request: Request

    def perform_create(self, serializer: Any) -> None:
        serializer.save(created_by=self.request.user)

    def perform_update(self, serializer: Any) -> None:
        serializer.save(updated_by=self.request.user)
