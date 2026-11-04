"""Indicadores de riesgo (RF-026 y RF-027, decision D6). Calculo sin base de datos.

Definicion unica para toda comparacion:
- Poblacion: evaluaciones terminadas; las que estan en curso no cuentan.
- Puestos reevaluados: solo cuenta la evaluacion mas reciente, para no contarlos dos veces.
- Medida: cada puesto cuenta una vez, segun el color de su postura de mayor riesgo.
- No se promedian puntajes ni se ordena por ranking: RULA no define ninguna de las dos cosas.
"""
from dataclasses import dataclass

from apps.rula.risk import TrafficLight, action_level_for


@dataclass(frozen=True)
class EvaluationRow:
    position_id: int
    area_id: int
    company_id: int
    company_name: str
    worst_score: int


@dataclass(frozen=True)
class RiskDistribution:
    green: int = 0
    yellow: int = 0
    red: int = 0

    @property
    def total(self) -> int:
        return self.green + self.yellow + self.red

    @property
    def follow_up(self) -> int:
        """Puestos con color amarillo o rojo."""
        return self.yellow + self.red

    @property
    def follow_up_percent(self) -> int:
        return round(self.follow_up * 100 / self.total) if self.total else 0


def latest_per_position(rows: list[EvaluationRow]) -> list[EvaluationRow]:
    """Requiere las filas ordenadas de la mas reciente a la mas antigua."""
    latest: dict[int, EvaluationRow] = {}
    for row in rows:
        latest.setdefault(row.position_id, row)
    return list(latest.values())


def distribution(rows: list[EvaluationRow]) -> RiskDistribution:
    counts = {TrafficLight.GREEN: 0, TrafficLight.YELLOW: 0, TrafficLight.RED: 0}
    for row in rows:
        counts[action_level_for(row.worst_score).traffic_light] += 1
    return RiskDistribution(counts[TrafficLight.GREEN], counts[TrafficLight.YELLOW], counts[TrafficLight.RED])
