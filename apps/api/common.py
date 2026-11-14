"""Piezas que comparten las vistas de la API: validar con los formularios de Django y paginar.

Las vistas no repiten reglas: el mismo formulario que usa la pantalla actual valida la petición
JSON, y su error se devuelve con el formato único de apps.api.errors.
"""
from django.core.paginator import Paginator
from django.db import IntegrityError, transaction
from rest_framework import status
from rest_framework.response import Response

from .errors import error_response


def form_errors(form) -> dict[str, list[str]]:
    return {name: [str(error) for error in errors] for name, errors in form.errors.items()}


def invalid(form) -> Response:
    fields = form_errors(form)
    general = fields.get("__all__")
    message = general[0] if general and len(fields) == 1 else "Revisa los datos marcados."
    return error_response("validation_error", message, status.HTTP_400_BAD_REQUEST, fields)


def save_form(form, present, *, integrity_message: str, created: bool = False) -> Response:
    """Valida y guarda. Si la base rechaza un duplicado al mismo tiempo, responde 400, no 500."""
    if not form.is_valid():
        return invalid(form)
    try:
        with transaction.atomic():
            instance = form.save()
    except IntegrityError:
        form.add_error(None, integrity_message)
        return invalid(form)
    return Response(present(instance), status=status.HTTP_201_CREATED if created else status.HTTP_200_OK)


def paginate(request, queryset, present, per_page: int) -> dict:
    paginator = Paginator(queryset, per_page)
    page = paginator.get_page(request.query_params.get("page"))
    return {
        "results": [present(item) for item in page.object_list],
        "count": paginator.count,
        "page": page.number,
        "pages": paginator.num_pages,
    }


def choices(items) -> list[dict]:
    return [{"value": str(value), "label": str(label)} for value, label in items]
