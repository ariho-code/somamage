from typing import Any
from rest_framework.permissions import BasePermission
from rest_framework.request import Request
from rest_framework.views import View


class RoleBasedPermission(BasePermission):
    """
    Grant access based on user role.
    Subclass and set `allowed_roles` on the ViewSet, or override `has_permission`.
    """

    allowed_roles: list[str] = []

    def has_permission(self, request: Request, view: View) -> bool:
        if not request.user or not request.user.is_authenticated:
            return False
        view_roles = getattr(view, "allowed_roles", self.allowed_roles)
        if not view_roles:
            return True  # No restriction — any authenticated user allowed
        return getattr(request.user, "role", None) in view_roles


class IsPlatformOwner(BasePermission):
    def has_permission(self, request: Request, view: View) -> bool:
        return bool(
            request.user
            and request.user.is_authenticated
            and request.user.role in ("superadmin", "platform_owner")
        )


class IsSchoolAdmin(BasePermission):
    def has_permission(self, request: Request, view: View) -> bool:
        return bool(
            request.user
            and request.user.is_authenticated
            and request.user.role in ("superadmin", "platform_owner", "headteacher", "school_admin")
        )


class IsHeadteacher(BasePermission):
    def has_permission(self, request: Request, view: View) -> bool:
        return bool(
            request.user
            and request.user.is_authenticated
            and request.user.role in ("superadmin", "platform_owner", "headteacher")
        )


class IsTeacherOrAbove(BasePermission):
    TEACHER_ROLES = {"superadmin", "platform_owner", "headteacher", "school_admin",
                     "director_of_studies", "teacher"}

    def has_permission(self, request: Request, view: View) -> bool:
        return bool(
            request.user
            and request.user.is_authenticated
            and request.user.role in self.TEACHER_ROLES
        )


class IsBursar(BasePermission):
    def has_permission(self, request: Request, view: View) -> bool:
        return bool(
            request.user
            and request.user.is_authenticated
            and request.user.role in ("superadmin", "platform_owner", "headteacher", "bursar")
        )


class IsOwnerOrReadOnly(BasePermission):
    """Object-level permission: allow write only to object owner."""

    def has_object_permission(self, request: Request, view: View, obj: Any) -> bool:
        from rest_framework.permissions import SAFE_METHODS
        if request.method in SAFE_METHODS:
            return True
        owner = getattr(obj, "user", None) or getattr(obj, "created_by", None)
        return owner == request.user
