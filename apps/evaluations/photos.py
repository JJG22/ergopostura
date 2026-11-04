"""Valida y optimiza las fotografias antes de guardarlas.

Volver a codificar cada imagen reduce su peso y elimina los metadatos, como la ubicacion
GPS que agregan los celulares. Tambien descarta archivos que solo aparentan ser imagenes.
Los limites son propuestos: el documento de requisitos no los fija (RF-012).
"""
from dataclasses import dataclass
from io import BytesIO

from PIL import Image, ImageOps, UnidentifiedImageError

MAX_UPLOAD_BYTES = 10 * 1024 * 1024
MAX_PIXELS = 50_000_000
MAX_SIDE = 1600
JPEG_QUALITY = 82
ALLOWED_FORMATS = {"JPEG", "PNG", "WEBP"}


class InvalidPhoto(ValueError):
    pass


@dataclass(frozen=True)
class ProcessedPhoto:
    data: bytes
    content_type: str
    width: int
    height: int


def process_photo(uploaded) -> ProcessedPhoto:
    if uploaded.size > MAX_UPLOAD_BYTES:
        raise InvalidPhoto("La fotografía supera el límite de 10 MB.")
    try:
        image = Image.open(uploaded)
        if image.format not in ALLOWED_FORMATS:
            raise InvalidPhoto("Usa una fotografía en formato JPG, PNG o WEBP.")
        # Se revisa antes de decodificar: una imagen enorme podria agotar la memoria.
        if image.width * image.height > MAX_PIXELS:
            raise InvalidPhoto("La fotografía tiene demasiada resolución.")
        image.load()
        image = ImageOps.exif_transpose(image)
    except (UnidentifiedImageError, OSError, Image.DecompressionBombError, SyntaxError, ValueError) as error:
        if isinstance(error, InvalidPhoto):
            raise
        raise InvalidPhoto("El archivo no es una fotografía válida.") from error

    if image.mode != "RGB":
        image = image.convert("RGB")
    image.thumbnail((MAX_SIDE, MAX_SIDE))

    output = BytesIO()
    image.save(output, format="JPEG", quality=JPEG_QUALITY, optimize=True)
    return ProcessedPhoto(output.getvalue(), "image/jpeg", image.width, image.height)
