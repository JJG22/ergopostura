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
TIMEOUT_SECONDS = 100


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

    def __init__(self, message: str, *, quota: bool = False):
        super().__init__(message)
        self.quota = quota


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


def gemini_json(*, system: str, parts: list[dict], schema: dict) -> tuple[dict, str]:
    """Pide a Gemini una respuesta JSON con el esquema dado. Devuelve los datos y el modelo."""
    from google import genai
    from google.genai import errors

    client = genai.Client(api_key=settings.GEMINI_API_KEY)
    try:
        interaction = client.interactions.create(
            model=settings.GEMINI_MODEL,
            system_instruction=system,
            input=parts,
            response_format={"type": "text", "mime_type": "application/json", "schema": gemini_schema(schema)},
            # No se guarda la conversación en Google para consultarla después.
            store=False,
            timeout=TIMEOUT_SECONDS,
        )
    except errors.ClientError as error:
        if error.code == 429:
            raise GeminiFailed(
                "Se alcanzó el límite gratuito de la IA por ahora. Intenta de nuevo en un rato.", quota=True
            ) from error
        if error.code in (401, 403):
            raise GeminiFailed("La clave de Gemini no es válida o no tiene permiso. Revisa GEMINI_API_KEY.") from error
        if error.code == 404:
            raise GeminiFailed(f"El modelo {settings.GEMINI_MODEL} no está disponible. Revisa GEMINI_MODEL.") from error
        raise GeminiFailed("La IA no pudo procesar el archivo enviado.") from error
    except errors.ServerError as error:
        raise GeminiFailed("El servicio de IA no está disponible en este momento. Intenta más tarde.") from error
    except errors.APIError as error:
        raise GeminiFailed("El servicio de IA respondió con un error. Intenta más tarde.") from error
    except Exception as error:  # tiempo de espera o red: el paquete usa varios tipos de error
        raise GeminiFailed("No se pudo conectar con el servicio de IA. Intenta de nuevo.") from error

    if interaction.status != "completed":
        raise GeminiFailed("La IA no terminó la respuesta. Intenta de nuevo.")
    try:
        data = json.loads(interaction.output_text or "")
    except ValueError as error:
        raise GeminiFailed("La IA devolvió una respuesta incompleta. Intenta de nuevo.") from error
    return data, settings.GEMINI_MODEL[:60]
