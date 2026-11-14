"""Formato único de error de la API.

Toda respuesta de error tiene la misma forma, para que el cliente la maneje con un solo tipo:

    {"error": {"code": "validation_error", "message": "Texto para mostrar", "fields": {"email": ["..."]}}}

`code` es estable y en inglés (el cliente decide con él); `message` es para la persona.
"""
from django.core.exceptions import PermissionDenied
from django.http import Http404
from rest_framework import exceptions, status
from rest_framework.response import Response
from rest_framework.views import exception_handler

MESSAGES = {
    "not_authenticated": "Tu sesión terminó. Ingresa de nuevo.",
    "authentication_failed": "Tu sesión terminó. Ingresa de nuevo.",
    "permission_denied": "No tienes permiso para hacer esto.",
    "not_found": "No encontramos lo que buscas.",
    "method_not_allowed": "Esta acción no está permitida aquí.",
    "throttled": "Hiciste demasiados intentos. Espera un momento y vuelve a intentarlo.",
    "parse_error": "La solicitud llegó con un formato inválido.",
    "unsupported_media_type": "La solicitud llegó con un formato inválido.",
}


def error_body(code: str, message: str, fields: dict | None = None) -> dict:
    body = {"code": code, "message": message}
    if fields:
        body["fields"] = fields
    return {"error": body}


def error_response(code: str, message: str, http_status: int, fields: dict | None = None) -> Response:
    return Response(error_body(code, message, fields), status=http_status)


def _flatten(detail) -> dict[str, list[str]]:
    """Errores de validación como {campo: [mensajes]}; los generales van en "__all__"."""
    if isinstance(detail, dict):
        result = {}
        for key, value in detail.items():
            name = "__all__" if key in ("non_field_errors", "__all__") else key
            items = value if isinstance(value, list) else [value]
            result[name] = [str(item) for item in items]
        return result
    items = detail if isinstance(detail, list) else [detail]
    return {"__all__": [str(item) for item in items]}


def handler(exc, context):
    if isinstance(exc, Http404):
        exc = exceptions.NotFound()
    elif isinstance(exc, PermissionDenied):
        exc = exceptions.PermissionDenied()

    response = exception_handler(exc, context)
    if response is None:
        # Error no previsto: Django lo registra; el cliente recibe un mensaje sin detalles internos.
        return None

    if isinstance(exc, exceptions.ValidationError):
        fields = _flatten(exc.detail)
        first = next(iter(fields.values()))[0]
        response.data = error_body("validation_error", first if "__all__" in fields else "Revisa los datos marcados.", fields)
        response.status_code = status.HTTP_400_BAD_REQUEST
        return response

    code = getattr(exc, "default_code", "error")
    if isinstance(exc, (exceptions.NotAuthenticated, exceptions.AuthenticationFailed)):
        # 401 sin desafio WWW-Authenticate: la sesion es por cookie.
        response.status_code = status.HTTP_401_UNAUTHORIZED
        code = "not_authenticated"
    message = MESSAGES.get(code) or str(getattr(exc, "detail", "")) or "Ocurrió un error."
    response.data = error_body(code, message)
    return response
