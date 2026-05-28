from django.http import Http404
from rest_framework import exceptions, status
from rest_framework.views import exception_handler


def api_exception_handler(exc, context):
    response = exception_handler(exc, context)
    if response is None:
        return response

    error_code, message, fields = _exception_payload(exc, response.data)
    response.data = {
        "error": error_code,
        "message": message,
        "fields": fields,
    }
    return response


def _exception_payload(exc, data):
    if isinstance(exc, exceptions.ValidationError):
        return "validation_error", "Request validation failed.", _validation_fields(data)
    if isinstance(exc, exceptions.NotAuthenticated):
        return "authentication_required", _detail_message(data, "Authentication is required."), {}
    if isinstance(exc, exceptions.AuthenticationFailed):
        return "invalid_token", _detail_message(data, "Invalid bearer token."), {}
    if isinstance(exc, exceptions.PermissionDenied):
        return "permission_denied", _detail_message(data, "Permission denied."), {}
    if isinstance(exc, (exceptions.NotFound, Http404)):
        return "not_found", _detail_message(data, "Resource not found."), {}
    if isinstance(exc, exceptions.MethodNotAllowed):
        return "method_not_allowed", _detail_message(data, "Method not allowed."), {}

    if getattr(exc, "status_code", None) == status.HTTP_500_INTERNAL_SERVER_ERROR:
        return "server_error", "Server error.", {}
    return "api_error", _detail_message(data, "API request failed."), {}


def _detail_message(data, default):
    if isinstance(data, dict) and "detail" in data:
        return str(data["detail"])
    if isinstance(data, list):
        return " ".join(str(item) for item in data)
    return default


def _validation_fields(data):
    if isinstance(data, dict):
        return {key: _stringify_errors(value) for key, value in data.items()}
    return {"non_field_errors": _stringify_errors(data)}


def _stringify_errors(value):
    if isinstance(value, dict):
        return {key: _stringify_errors(item) for key, item in value.items()}
    if isinstance(value, list):
        return [str(item) for item in value]
    return str(value)
