"""Dibuja una figura esquematica de perfil con los angulos de la postura.

Reemplaza la fotografia en los datos de demostracion: no se usan fotos de personas reales.
Los angulos se dibujan como los mide RULA: el tronco desde la vertical, el cuello y el brazo
respecto al tronco, el antebrazo respecto al brazo y la muneca respecto al antebrazo.
"""
import math
from io import BytesIO

from PIL import Image, ImageDraw

WIDTH, HEIGHT = 800, 600
INK = (15, 23, 42)
LIMB = (15, 118, 110)
FLOOR = (203, 213, 225)


def _point(origin, length, degrees_from_down):
    """Punto a `length` px de `origin`, girado hacia adelante (derecha) desde la vertical hacia abajo."""
    radians = math.radians(degrees_from_down)
    return (origin[0] + length * math.sin(radians), origin[1] + length * math.cos(radians))


def draw_posture(values: dict) -> tuple[bytes, int, int]:
    """Sin texto: la imagen de Docker no trae fuentes con tildes, y el nombre de archivo ya avisa."""
    image = Image.new("RGB", (WIDTH, HEIGHT), (248, 250, 252))
    draw = ImageDraw.Draw(image)
    seated = values.get("trunk_supported_seated", False)
    floor_y = 520
    draw.line([(80, floor_y), (720, floor_y)], fill=FLOOR, width=4)

    if seated:
        hip = (360, 360)
        knee = (hip[0] + 120, hip[1])
        draw.line([hip, knee], fill=INK, width=14)
        draw.line([knee, (knee[0], floor_y)], fill=INK, width=14)
        draw.rectangle([hip[0] - 70, hip[1] + 8, hip[0] + 40, hip[1] + 22], fill=FLOOR)
    else:
        hip = (380, 330)
        draw.line([hip, (hip[0], floor_y)], fill=INK, width=14)

    trunk = float(values.get("trunk_angle", 0))
    shoulder = _point(hip, 170, 180 - trunk)
    draw.line([hip, shoulder], fill=INK, width=16)

    neck_total = trunk + float(values.get("neck_angle", 0))
    head = _point(shoulder, 70, 180 - neck_total)
    draw.line([shoulder, head], fill=INK, width=10)
    draw.ellipse([head[0] - 30, head[1] - 30, head[0] + 30, head[1] + 30], outline=INK, width=8)

    # La linea del tronco hacia abajo forma -trunk con la vertical; el brazo se flexiona desde ella.
    upper_arm = float(values.get("upper_arm_angle", 0)) - trunk
    elbow = _point(shoulder, 120, upper_arm)
    forearm = upper_arm + float(values.get("lower_arm_angle", 0))
    wrist = _point(elbow, 110, forearm)
    hand = _point(wrist, 30, forearm + float(values.get("wrist_angle", 0)))
    draw.line([shoulder, elbow], fill=LIMB, width=12)
    draw.line([elbow, wrist], fill=LIMB, width=10)
    draw.line([wrist, hand], fill=LIMB, width=8)
    for joint in (shoulder, elbow, wrist):
        draw.ellipse([joint[0] - 7, joint[1] - 7, joint[0] + 7, joint[1] + 7], fill=INK)

    output = BytesIO()
    image.save(output, format="JPEG", quality=85)
    return output.getvalue(), WIDTH, HEIGHT
