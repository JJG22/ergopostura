"""Proveedor de IA y cliente de Gemini (Google), compartidos por contratos y evaluaciones.

La lectura de contratos y las recomendaciones RULA pueden usar Claude (Anthropic) o Gemini.
Con AI_PROVIDER vacío se usa Gemini si tiene clave y, si no, Claude. Gemini se usa con la
Interactions API del paquete google-genai: una sola llamada con instrucciones de sistema,
el documento o la foto en línea y una respuesta JSON que cumple un esquema.
"""
import base64
import json

from django.conf import settings

GEMINI = "gemini"
ANTHROPIC = "anthropic"
# Gunicorn corta a los 120 s: caben dos intentos (el modelo y su respaldo).
TIMEOUT_SECONDS = 45


def provider() -> str | None:
    """El proveedor configurado, o None si no hay ninguna clave."""
    chosen = (settings.AI_PROVIDER or "").strip().lower()
    if chosen == GEMINI:
        return GEMINI if settings.GEMINI_API_KEY else None
    if chosen == ANTHROPIC:
        return ANTHROPIC if settings.ANTHROPIC_API_KEY else None
    if settings.GEMINI_API_KEY:
        return GEMINI
    if settings.ANTHROPIC_API_KEY:
        return ANTHROPIC
    return None


class GeminiFailed(RuntimeError):
    """La llamada a Gemini no se completó; el mensaje se puede mostrar al usuario."""

    def __init__(self, message: str, *, quota: bool = False, retry: bool = False):
        super().__init__(message)
        self.quota = quota
        # Otro modelo podría responder: saturación, cupo agotado o modelo no disponible.
        self.retry = retry


def inline(kind: str, data: bytes, mime_type: str) -> dict:
    """Un documento («document») o una imagen («image») enviados en la misma solicitud."""
    return {"type": kind, "data": base64.b64encode(data).decode("ascii"), "mime_type": mime_type}


def gemini_schema(schema):
    """Adapta un esquema JSON al subconjunto que acepta Gemini.

    Los campos opcionales se escriben como anyOf [tipo, null]; aquí quedan solo con su tipo,
    y las instrucciones piden una cadena vacía cuando el dato no aparece.
    """
    if isinstance(schema, dict):
        options = schema.get("anyOf")
        if isinstance(options, list):
            kept = [option for option in options if option.get("type") != "null"]
            if len(kept) == 1:
                return gemini_schema(kept[0])
        return {key: gemini_schema(value) for key, value in schema.items()}
    if isinstance(schema, list):
        return [gemini_schema(item) for item in schema]
    return schema


def _status_failure(status: int | None) -> GeminiFailed:
    """El mensaje para la persona según el código HTTP, y si conviene probar otro modelo."""
    if status == 429:
        return GeminiFailed("Se alcanzó el límite gratuito de la IA por ahora. Intenta de nuevo en un rato.",
                            quota=True, retry=True)
    if status in (401, 403):
        return GeminiFailed("La clave de Gemini no es válida o no tiene permiso. Revisa GEMINI_API_KEY.")
    if status == 404:
        return GeminiFailed("El modelo de Gemini configurado no está disponible. Revisa GEMINI_MODEL.", retry=True)
    if status is not None and status >= 500:
        return GeminiFailed("La IA de Google está muy ocupada en este momento. Intenta de nuevo en un rato.", retry=True)
    return GeminiFailed("La IA no pudo procesar el archivo enviado.")


def _ask(client, model: str, *, system: str, parts: list[dict], schema: dict) -> dict:
    from google.genai import _interactions_errors as interaction_errors
    from google.genai import errors

    try:
        interaction = client.interactions.create(
            model=model,
            system_instruction=system,
            input=parts,
            response_format={"type": "text", "mime_type": "application/json", "schema": gemini_schema(schema)},
            # No se guarda la conversación en Google para consultarla después.
            store=False,
            timeout=TIMEOUT_SECONDS,
        )
    except interaction_errors.APITimeoutError as error:
        raise GeminiFailed("La IA tardó demasiado. Intenta de nuevo.", retry=True) from error
    except interaction_errors.APIConnectionError as error:
        raise GeminiFailed("No se pudo conectar con el servicio de IA. Intenta de nuevo.") from error
    except interaction_errors.APIStatusError as error:
        raise _status_failure(error.status_code) from error
    except errors.APIError as error:
        raise _status_failure(error.code) from error
    except interaction_errors.APIError as error:
        raise GeminiFailed("El servicio de IA respondió con un error. Intenta más tarde.") from error

    if interaction.status != "completed":
        raise GeminiFailed("La IA no terminó la respuesta. Intenta de nuevo.", retry=True)
    try:
        return json.loads(interaction.output_text or "")
    except ValueError as error:
        raise GeminiFailed("La IA devolvió una respuesta incompleta. Intenta de nuevo.", retry=True) from error


def gemini_models() -> list[str]:
    """El modelo configurado y, detrás, los de respaldo (sin repetir)."""
    models = [settings.GEMINI_MODEL, *settings.GEMINI_FALLBACK_MODELS]
    return [model for index, model in enumerate(models) if model and model not in models[:index]]


def gemini_json(*, system: str, parts: list[dict], schema: dict) -> tuple[dict, str]:
    """Pide a Gemini una respuesta JSON con el esquema dado. Devuelve los datos y el modelo.

    En el plan gratis un modelo puede estar saturado o agotar su cupo del día: en ese caso se
    prueba el siguiente modelo de respaldo, que tiene su propio cupo.
    """
    from google import genai
    from google.genai import types

    # Sin reintentos automáticos: el paquete reintenta un 503 durante unos dos minutos, y es
    # mejor pasar enseguida al modelo de respaldo.
    client = genai.Client(
        api_key=settings.GEMINI_API_KEY,
        http_options=types.HttpOptions(retry_options=types.HttpRetryOptions(attempts=1)),
    )
    failure = None
    for model in gemini_models():
        try:
            return _ask(client, model, system=system, parts=parts, schema=schema), model[:60]
        except GeminiFailed as error:
            failure = error
            if not error.retry:
                break
    raise failure
