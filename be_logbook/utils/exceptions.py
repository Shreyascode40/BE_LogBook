from __future__ import annotations

from typing import Any

from rest_framework import status
from rest_framework.exceptions import APIException
from rest_framework.response import Response
from rest_framework.views import exception_handler


class BusinessRuleViolation(APIException):
    """Raised when a server-side business rule is violated.

    Maps to HTTP 422 so the client receives a structured validation error.
    """

    status_code = status.HTTP_422_UNPROCESSABLE_ENTITY
    default_detail = "Business rule violation."
    default_code = "business_rule_violation"

    def __init__(self, detail: Any = None, code: str | None = None) -> None:
        super().__init__(detail=detail)
        if code is not None:
            self.default_code = code


def custom_exception_handler(exc: Any, context: dict[str, Any]) -> Response | None:
    """Central DRF exception handler returning a consistent JSON envelope.

    Success/error responses follow:
        {"success": false, "message": "...", "errors": {...}}
    """
    response = exception_handler(exc, context)

    if response is None:
        # Uncaught server error - let Django handle (or DRF default).
        return None

    if isinstance(exc, BusinessRuleViolation):
        message = "Operation not allowed."
        errors: dict[str, Any] = {}
        detail = response.data
        if isinstance(detail, dict):
            errors = detail
            first = _first_message(detail)
            if first:
                message = first
        else:
            message = str(detail)
        response.data = {"success": False, "message": message, "errors": errors}
        return response

    # Standard DRF exceptions (validation, auth, not found, etc.)
    message = "Request failed."
    errors: dict[str, Any] = {}
    if isinstance(response.data, dict):
        errors = response.data
        message = _first_message(response.data) or message
    elif isinstance(response.data, list):
        message = " ".join(str(x) for x in response.data)
    else:
        message = str(response.data)

    response.data = {"success": False, "message": message, "errors": errors}
    return response


def _first_message(data: Any) -> str | None:
    if isinstance(data, dict):
        for value in data.values():
            if isinstance(value, list) and value:
                return str(value[0])
            if isinstance(value, str):
                return value
            if isinstance(value, dict):
                return _first_message(value)
    return None
