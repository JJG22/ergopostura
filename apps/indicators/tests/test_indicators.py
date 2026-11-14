from datetime import timedelta

from django.test import SimpleTestCase
from django.utils import timezone

from apps.evaluations import services
from apps.evaluations.models import Recommendation
from apps.evaluations.tests.test_evaluations import (
    make_assessment,
    make_evaluation,
    make_posture,
)
from apps.indicators.metrics import EvaluationRow, distribution, latest_per_position
from apps.rula.scoring import Load

LOW = dict(
    upper_arm_angle="0", shoulder_raised="", lower_arm_angle="80", wrist_angle="0",
    wrist_bent_from_midline="", arm_static_or_repeated="",
    arm_load=Load.NONE_OR_LIGHT_INTERMITTENT.name, neck_angle="0", neck_twisted="", trunk_angle="0",
)
# Puntaje 6: amarillo. Es el caso calculado a mano en las pruebas de RULA.
MEDIUM = {}
HIGH = dict(
    upper_arm_angle="120", lower_arm_angle="10", wrist_angle="40", arm_load=Load.SHOCK_OR_RAPID_FORCE.name,
    neck_angle="-10", trunk_angle="80", body_load=Load.HEAVY_STATIC_OR_REPEATED.name,
)


def row(position, score, area=1, company=1):
    return EvaluationRow(position, area, company, "Empresa", score)


def finished(user, position, level, days_ago=0):
    evaluation = make_evaluation(
        user, position, evaluated_on=timezone.localdate() - timedelta(days=days_ago)
    )
    posture = make_posture(evaluation)
    make_assessment(posture, **level)
    Recommendation.objects.create(posture=posture, text="Ajustar", author=user)
    services.complete_evaluation(evaluation)
    return evaluation


class MetricsTests(SimpleTestCase):
    def test_counts_by_traffic_light(self):
        risk = distribution([row(1, 1), row(2, 2), row(3, 3), row(4, 6), row(5, 7)])
        self.assertEqual((risk.green, risk.yellow, risk.red), (2, 2, 1))
        self.assertEqual(risk.total, 5)
        self.assertEqual(risk.follow_up, 3)
        self.assertEqual(risk.follow_up_percent, 60)

    def test_empty_does_not_divide_by_zero(self):
        self.assertEqual(distribution([]).follow_up_percent, 0)

    def test_only_the_latest_evaluation_of_a_position_counts(self):
        rows = [row(1, 2), row(1, 7), row(2, 7)]
        self.assertEqual(latest_per_position(rows), [row(1, 2), row(2, 7)])


