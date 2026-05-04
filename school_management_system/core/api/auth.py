from typing import Any
from django.contrib.auth import authenticate
from rest_framework import status
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework_simplejwt.exceptions import TokenError

from core.models import User
from core.utils import error_response, success_response
from .serializers import (
    ChangePasswordSerializer,
    LoginSerializer,
    UserProfileSerializer,
)


class LoginView(APIView):
    """[PUBLIC] POST /api/v1/auth/login/"""

    permission_classes = [AllowAny]
    throttle_scope = "auth"

    def post(self, request: Request) -> Response:
        serializer = LoginSerializer(data=request.data)
        if not serializer.is_valid():
            return error_response("Invalid input.", serializer.errors)

        email = serializer.validated_data["email"]
        password = serializer.validated_data["password"]

        user = authenticate(request, username=email, password=password)
        if user is None:
            # Try by email if username auth fails (in case username != email)
            try:
                u = User.objects.get(email=email)
                user = authenticate(request, username=u.username, password=password)
            except User.DoesNotExist:
                pass

        if user is None:
            return error_response("Invalid credentials.", status_code=status.HTTP_401_UNAUTHORIZED)

        if not user.is_active:
            return error_response("Account is inactive.", status_code=status.HTTP_403_FORBIDDEN)

        refresh = RefreshToken.for_user(user)
        profile = UserProfileSerializer(user).data

        return success_response(
            data={
                "access": str(refresh.access_token),
                "refresh": str(refresh),
                "user": profile,
            },
            message="Login successful.",
        )


class LogoutView(APIView):
    """POST /api/v1/auth/logout/  — blacklists the refresh token."""

    permission_classes = [IsAuthenticated]

    def post(self, request: Request) -> Response:
        refresh_token = request.data.get("refresh")
        if not refresh_token:
            return error_response("Refresh token is required.")
        try:
            token = RefreshToken(refresh_token)
            token.blacklist()
        except TokenError as exc:
            return error_response(str(exc))
        return success_response(message="Logged out successfully.")


class TokenRefreshView(APIView):
    """[PUBLIC] POST /api/v1/auth/refresh/"""

    permission_classes = [AllowAny]

    def post(self, request: Request) -> Response:
        refresh_token = request.data.get("refresh")
        if not refresh_token:
            return error_response("Refresh token is required.")
        try:
            token = RefreshToken(refresh_token)
            return success_response(
                data={"access": str(token.access_token)},
                message="Token refreshed.",
            )
        except TokenError as exc:
            return error_response(str(exc), status_code=status.HTTP_401_UNAUTHORIZED)


class ChangePasswordView(APIView):
    """POST /api/v1/auth/change-password/"""

    permission_classes = [IsAuthenticated]

    def post(self, request: Request) -> Response:
        serializer = ChangePasswordSerializer(data=request.data, context={"request": request})
        if not serializer.is_valid():
            return error_response("Invalid input.", serializer.errors)

        user: User = request.user
        user.set_password(serializer.validated_data["new_password"])
        user.must_change_password = False
        user.save(update_fields=["password", "must_change_password"])
        return success_response(message="Password changed successfully.")


class MeView(APIView):
    """GET /api/v1/auth/me/  — return current user's profile."""

    permission_classes = [IsAuthenticated]

    def get(self, request: Request) -> Response:
        return success_response(data=UserProfileSerializer(request.user).data)
