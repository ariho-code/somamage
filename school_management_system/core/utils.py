from typing import Any
from rest_framework.views import exception_handler
from rest_framework.response import Response
from rest_framework import status


def custom_exception_handler(exc: Exception, context: dict) -> Response | None:
    """Wrap DRF exceptions in the standard response envelope."""
    response = exception_handler(exc, context)
    if response is not None:
        response.data = {
            "success": False,
            "data": None,
            "message": _extract_message(response.data),
            "errors": response.data,
        }
    return response


def _extract_message(data: Any) -> str:
    if isinstance(data, dict):
        for key in ("detail", "non_field_errors"):
            if key in data:
                val = data[key]
                if hasattr(val, "__iter__") and not isinstance(val, str):
                    return str(list(val)[0])
                return str(val)
        first_val = next(iter(data.values()), None)
        if first_val is not None:
            if hasattr(first_val, "__iter__") and not isinstance(first_val, str):
                return str(list(first_val)[0])
            return str(first_val)
    if isinstance(data, list) and data:
        return str(data[0])
    return "An error occurred."


def success_response(data: Any = None, message: str = "OK", status_code: int = status.HTTP_200_OK) -> Response:
    return Response(
        {"success": True, "data": data, "message": message, "errors": None},
        status=status_code,
    )


def error_response(message: str, errors: Any = None, status_code: int = status.HTTP_400_BAD_REQUEST) -> Response:
    return Response(
        {"success": False, "data": None, "message": message, "errors": errors},
        status=status_code,
    )
