"""Nivel de accion de RULA (RF-020) y su representacion en el semaforo (RF-021, RNF-004).

Los niveles de accion son del metodo. La correspondencia con los colores es una decision
del proyecto (D4): se sigue la lectura literal de RF-021, donde el rojo se reserva para
"intervencion inmediata", el unico caso del nivel 4. Para no suavizar el nivel 3, la vista
de resultados siempre muestra el texto del nivel junto al color. El color no se guarda en
la base de datos, asi que cambiar esta tabla no requiere migrar evaluaciones.
"""
from dataclasses import dataclass
from enum import StrEnum


class TrafficLight(StrEnum):
    GREEN = "verde"
    YELLOW = "amarillo"
    RED = "rojo"


TRAFFIC_LIGHT_MEANING = {
    TrafficLight.GREEN: "Adecuado, sin intervención",
    TrafficLight.YELLOW: "Requiere revisión",
    TrafficLight.RED: "Puede requerir intervención inmediata",
}


@dataclass(frozen=True)
class ActionLevel:
    level: int
    min_score: int
    max_score: int
    description: str
    traffic_light: TrafficLight

    @property
    def traffic_light_meaning(self) -> str:
        return TRAFFIC_LIGHT_MEANING[self.traffic_light]


ACTION_LEVELS = (
    ActionLevel(
        1, 1, 2,
        "La postura es aceptable si no se mantiene ni se repite durante periodos largos.",
        TrafficLight.GREEN,
    ),
    ActionLevel(
        2, 3, 4,
        "Se necesita investigar más y pueden requerirse cambios.",
        TrafficLight.YELLOW,
    ),
    ActionLevel(
        3, 5, 6,
        "Se requiere investigar y hacer cambios pronto.",
        TrafficLight.YELLOW,
    ),
    ActionLevel(
        4, 7, 7,
        "Se requiere investigar y hacer cambios de inmediato.",
        TrafficLight.RED,
    ),
)


def action_level_for(grand_score: int) -> ActionLevel:
    for action_level in ACTION_LEVELS:
        if action_level.min_score <= grand_score <= action_level.max_score:
            return action_level
    raise ValueError(f"El puntaje final de RULA va de 1 a 7; se recibió {grand_score}.")
