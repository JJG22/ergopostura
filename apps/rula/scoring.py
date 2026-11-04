"""Calculo de RULA. Python puro: sin base de datos ni Django, para probarlo de forma aislada.

Los angulos se registran a mano en grados (decision D2). Convencion de signos:
positivo es flexion y negativo es extension.

Donde el articulo da rangos que se tocan (por ejemplo 0-10 y 10-20), el limite pertenece
al rango inferior, salvo que el texto diga "o mas": cuello de 20 y tronco de 60 ya
puntuan en el rango superior.
"""
import math
from dataclasses import dataclass
from enum import Enum

from .tables import TABLE_A, TABLE_B, TABLE_C


class RulaInputError(ValueError):
    """Dato que el metodo no permite puntuar. Nunca se reemplaza por un valor supuesto."""


class Load(Enum):
    """Filas de la figura 5 y del texto del articulo, con su puntaje."""

    NONE_OR_LIGHT_INTERMITTENT = ("Sin resistencia o hasta 2 kg intermitente", 0)
    MEDIUM_INTERMITTENT = ("De 2 a 10 kg intermitente", 1)
    MEDIUM_STATIC_OR_REPEATED = ("De 2 a 10 kg estática o repetida", 2)
    HEAVY_INTERMITTENT = ("Más de 10 kg intermitente", 2)
    HEAVY_STATIC_OR_REPEATED = ("Más de 10 kg estática o repetida", 3)
    SHOCK_OR_RAPID_FORCE = ("Golpes o fuerza brusca, de cualquier magnitud", 3)

    @property
    def label(self) -> str:
        return self.value[0]

    @property
    def points(self) -> int:
        return self.value[1]


@dataclass(frozen=True)
class RulaInput:
    # Grupo A: brazo, antebrazo y muneca
    upper_arm_angle: float
    lower_arm_angle: float
    wrist_angle: float
    shoulder_raised: bool = False
    upper_arm_abducted: bool = False
    arm_supported: bool = False
    lower_arm_across_midline_or_out: bool = False
    wrist_bent_from_midline: bool = False
    wrist_twist_near_end: bool = False
    arm_static_or_repeated: bool = False
    arm_load: Load = Load.NONE_OR_LIGHT_INTERMITTENT

    # Grupo B: cuello, tronco y piernas
    neck_angle: float = 0
    trunk_angle: float = 0
    neck_twisted: bool = False
    neck_side_bent: bool = False
    trunk_supported_seated: bool = False
    trunk_twisted: bool = False
    trunk_side_bent: bool = False
    legs_supported_and_balanced: bool = True
    body_static_or_repeated: bool = False
    body_load: Load = Load.NONE_OR_LIGHT_INTERMITTENT


@dataclass(frozen=True)
class RulaResult:
    """Conserva cada puntaje parcial (RF-017) y cada factor aplicado (RF-018)."""

    upper_arm: int
    lower_arm: int
    wrist: int
    wrist_twist: int
    posture_a: int
    muscle_a: int
    load_a: int
    score_c: int
    neck: int
    trunk: int
    legs: int
    posture_b: int
    muscle_b: int
    load_b: int
    score_d: int
    grand_score: int


def _require_angle(name: str, value: float, minimum: float, maximum: float) -> None:
    if not math.isfinite(value) or not minimum <= value <= maximum:
        raise RulaInputError(f"El ángulo de {name} debe estar entre {minimum}° y {maximum}°.")


def upper_arm_score(data: RulaInput) -> int:
    angle = data.upper_arm_angle
    _require_angle("brazo", angle, -180, 180)
    if angle < -20:
        score = 2
    elif angle <= 20:
        score = 1
    elif angle <= 45:
        score = 2
    elif angle <= 90:
        score = 3
    else:
        score = 4
    score += data.shoulder_raised + data.upper_arm_abducted - data.arm_supported
    return max(score, 1)


def lower_arm_score(data: RulaInput) -> int:
    angle = data.lower_arm_angle
    _require_angle("antebrazo", angle, 0, 180)
    score = 1 if 60 <= angle <= 100 else 2
    return score + data.lower_arm_across_midline_or_out


def wrist_score(data: RulaInput) -> int:
    angle = data.wrist_angle
    _require_angle("muñeca", angle, -180, 180)
    magnitude = abs(angle)
    if magnitude == 0:
        score = 1
    elif magnitude <= 15:
        score = 2
    else:
        score = 3
    return score + data.wrist_bent_from_midline


def neck_score(data: RulaInput) -> int:
    angle = data.neck_angle
    _require_angle("cuello", angle, -180, 180)
    if angle < 0:
        score = 4
    elif angle <= 10:
        score = 1
    elif angle < 20:
        score = 2
    else:
        score = 3
    return score + data.neck_twisted + data.neck_side_bent


def trunk_score(data: RulaInput) -> int:
    angle = data.trunk_angle
    _require_angle("tronco", angle, -180, 180)
    if angle < 0:
        # El articulo solo define el tronco erguido y en flexion.
        raise RulaInputError("RULA no define un puntaje para el tronco en extensión.")
    if data.trunk_supported_seated or angle == 0:
        score = 1
    elif angle <= 20:
        score = 2
    elif angle < 60:
        score = 3
    else:
        score = 4
    return score + data.trunk_twisted + data.trunk_side_bent


def calculate(data: RulaInput) -> RulaResult:
    upper_arm = upper_arm_score(data)
    lower_arm = lower_arm_score(data)
    wrist = wrist_score(data)
    wrist_twist = 2 if data.wrist_twist_near_end else 1
    posture_a = TABLE_A[upper_arm - 1][lower_arm - 1][wrist - 1][wrist_twist - 1]
    muscle_a = int(data.arm_static_or_repeated)
    load_a = data.arm_load.points
    score_c = posture_a + muscle_a + load_a

    neck = neck_score(data)
    trunk = trunk_score(data)
    legs = 1 if data.legs_supported_and_balanced else 2
    posture_b = TABLE_B[neck - 1][trunk - 1][legs - 1]
    muscle_b = int(data.body_static_or_repeated)
    load_b = data.body_load.points
    score_d = posture_b + muscle_b + load_b

    # La tabla C agrupa los valores altos en la fila 8+ y la columna 7+.
    grand_score = TABLE_C[min(score_c, 8) - 1][min(score_d, 7) - 1]

    return RulaResult(
        upper_arm=upper_arm,
        lower_arm=lower_arm,
        wrist=wrist,
        wrist_twist=wrist_twist,
        posture_a=posture_a,
        muscle_a=muscle_a,
        load_a=load_a,
        score_c=score_c,
        neck=neck,
        trunk=trunk,
        legs=legs,
        posture_b=posture_b,
        muscle_b=muscle_b,
        load_b=load_b,
        score_d=score_d,
        grand_score=grand_score,
    )
