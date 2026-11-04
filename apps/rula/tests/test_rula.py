from django.test import SimpleTestCase

from apps.rula.risk import TrafficLight, action_level_for
from apps.rula.scoring import (
    Load,
    RulaInput,
    RulaInputError,
    calculate,
    lower_arm_score,
    neck_score,
    trunk_score,
    upper_arm_score,
    wrist_score,
)
from apps.rula.tables import TABLE_A, TABLE_B, TABLE_C

NEUTRAL = {"upper_arm_angle": 0, "lower_arm_angle": 80, "wrist_angle": 0}


def posture(**changes) -> RulaInput:
    return RulaInput(**{**NEUTRAL, **changes})


class TableIntegrityTests(SimpleTestCase):
    def test_table_shapes(self):
        self.assertEqual(len(TABLE_A), 6)
        for upper in TABLE_A:
            self.assertEqual(len(upper), 3)
            for lower in upper:
                self.assertEqual(len(lower), 4)
                for wrist in lower:
                    self.assertEqual(len(wrist), 2)
        self.assertEqual(len(TABLE_B), 6)
        for neck in TABLE_B:
            self.assertEqual([len(trunk) for trunk in neck], [2] * 6)
        self.assertEqual([len(row) for row in TABLE_C], [7] * 8)

    def test_published_reference_lookups(self):
        # Ejemplos resueltos en la guia RULA de ergo-plus.com.
        self.assertEqual(TABLE_A[3][1][3][0], 5)
        self.assertEqual(TABLE_B[2][1][0], 3)
        self.assertEqual(TABLE_C[6][4], 7)

    def test_table_corners(self):
        self.assertEqual(TABLE_A[0][0][0][0], 1)
        self.assertEqual(TABLE_A[5][2][3][1], 9)
        self.assertEqual(TABLE_B[0][0][0], 1)
        self.assertEqual(TABLE_B[5][5][1], 9)
        self.assertEqual(TABLE_C[0][0], 1)
        self.assertEqual(TABLE_C[7][6], 7)

    def test_worse_posture_never_lowers_the_score(self):
        # Detecta errores de transcripcion: las tablas del metodo nunca bajan al empeorar.
        for u in range(6):
            for l in range(3):
                for w in range(4):
                    for t in range(2):
                        value = TABLE_A[u][l][w][t]
                        if u < 5:
                            self.assertLessEqual(value, TABLE_A[u + 1][l][w][t])
                        if l < 2:
                            self.assertLessEqual(value, TABLE_A[u][l + 1][w][t])
                        if w < 3:
                            self.assertLessEqual(value, TABLE_A[u][l][w + 1][t])
                        if t < 1:
                            self.assertLessEqual(value, TABLE_A[u][l][w][t + 1])
        for n in range(6):
            for k in range(6):
                self.assertLessEqual(TABLE_B[n][k][0], TABLE_B[n][k][1])
                if n < 5:
                    self.assertLessEqual(TABLE_B[n][k][0], TABLE_B[n + 1][k][0])
                if k < 5:
                    self.assertLessEqual(TABLE_B[n][k][0], TABLE_B[n][k + 1][0])
        for c in range(8):
            for d in range(7):
                if c < 7:
                    self.assertLessEqual(TABLE_C[c][d], TABLE_C[c + 1][d])
                if d < 6:
                    self.assertLessEqual(TABLE_C[c][d], TABLE_C[c][d + 1])


class SegmentScoreTests(SimpleTestCase):
    def assert_scores(self, function, field, expected):
        for angle, score in expected.items():
            self.assertEqual(function(posture(**{field: angle})), score, f"{field}={angle}")

    def test_upper_arm_ranges(self):
        self.assert_scores(
            upper_arm_score,
            "upper_arm_angle",
            {-21: 2, -20: 1, 0: 1, 20: 1, 21: 2, 45: 2, 46: 3, 90: 3, 91: 4},
        )

    def test_upper_arm_adjustments(self):
        base = {"upper_arm_angle": 100}
        self.assertEqual(upper_arm_score(posture(**base, shoulder_raised=True)), 5)
        self.assertEqual(upper_arm_score(posture(**base, shoulder_raised=True, upper_arm_abducted=True)), 6)
        self.assertEqual(upper_arm_score(posture(**base, arm_supported=True)), 3)

    def test_supported_arm_never_scores_below_one(self):
        self.assertEqual(upper_arm_score(posture(arm_supported=True)), 1)

    def test_lower_arm_ranges(self):
        self.assert_scores(lower_arm_score, "lower_arm_angle", {0: 2, 59: 2, 60: 1, 100: 1, 101: 2})
        self.assertEqual(lower_arm_score(posture(lower_arm_across_midline_or_out=True)), 2)

    def test_wrist_ranges_use_flexion_and_extension_alike(self):
        self.assert_scores(wrist_score, "wrist_angle", {0: 1, 1: 2, -15: 2, 15: 2, 16: 3, -16: 3})
        self.assertEqual(wrist_score(posture(wrist_angle=20, wrist_bent_from_midline=True)), 4)

    def test_neck_ranges(self):
        self.assert_scores(neck_score, "neck_angle", {-1: 4, 0: 1, 10: 1, 11: 2, 19: 2, 20: 3})
        self.assertEqual(neck_score(posture(neck_angle=-5, neck_twisted=True, neck_side_bent=True)), 6)

    def test_trunk_ranges(self):
        self.assert_scores(trunk_score, "trunk_angle", {0: 1, 1: 2, 20: 2, 21: 3, 59: 3, 60: 4})
        self.assertEqual(trunk_score(posture(trunk_angle=70, trunk_twisted=True, trunk_side_bent=True)), 6)

    def test_seated_and_well_supported_trunk_scores_one(self):
        self.assertEqual(trunk_score(posture(trunk_angle=15, trunk_supported_seated=True)), 1)

    def test_trunk_extension_is_not_invented(self):
        with self.assertRaisesMessage(RulaInputError, "extensión"):
            trunk_score(posture(trunk_angle=-5))

    def test_impossible_angles_are_rejected(self):
        for changes in (
            {"lower_arm_angle": -1},
            {"upper_arm_angle": 181},
            {"wrist_angle": float("nan")},
            {"neck_angle": float("inf")},
        ):
            with self.assertRaises(RulaInputError, msg=changes):
                calculate(posture(**changes))


class LoadTests(SimpleTestCase):
    def test_points_match_the_original_article(self):
        self.assertEqual(
            {load.name: load.points for load in Load},
            {
                "NONE_OR_LIGHT_INTERMITTENT": 0,
                "MEDIUM_INTERMITTENT": 1,
                "MEDIUM_STATIC_OR_REPEATED": 2,
                "HEAVY_INTERMITTENT": 2,
                "HEAVY_STATIC_OR_REPEATED": 3,
                "SHOCK_OR_RAPID_FORCE": 3,
            },
        )


class CalculationTests(SimpleTestCase):
    def test_lowest_possible_posture(self):
        result = calculate(posture())
        self.assertEqual((result.score_c, result.score_d, result.grand_score), (1, 1, 1))

    def test_case_worked_by_hand(self):
        result = calculate(
            RulaInput(
                upper_arm_angle=30,  # 2
                shoulder_raised=True,  # +1 = 3
                lower_arm_angle=110,  # 2
                wrist_angle=10,  # 2
                wrist_bent_from_midline=True,  # +1 = 3
                arm_static_or_repeated=True,  # musculo +1
                arm_load=Load.MEDIUM_INTERMITTENT,  # carga +1
                neck_angle=15,  # 2
                neck_twisted=True,  # +1 = 3
                trunk_angle=30,  # 3
            )
        )
        self.assertEqual((result.upper_arm, result.lower_arm, result.wrist, result.wrist_twist), (3, 2, 3, 1))
        self.assertEqual(result.posture_a, 4)
        self.assertEqual(result.score_c, 6)
        self.assertEqual((result.neck, result.trunk, result.legs), (3, 3, 1))
        self.assertEqual(result.posture_b, 4)
        self.assertEqual(result.score_d, 4)
        self.assertEqual(result.grand_score, 6)
        self.assertEqual(action_level_for(result.grand_score).level, 3)

    def test_worst_posture_uses_last_row_and_column(self):
        result = calculate(
            RulaInput(
                upper_arm_angle=120,
                shoulder_raised=True,
                upper_arm_abducted=True,
                lower_arm_angle=10,
                lower_arm_across_midline_or_out=True,
                wrist_angle=40,
                wrist_bent_from_midline=True,
                wrist_twist_near_end=True,
                arm_static_or_repeated=True,
                arm_load=Load.SHOCK_OR_RAPID_FORCE,
                neck_angle=-10,
                neck_twisted=True,
                neck_side_bent=True,
                trunk_angle=80,
                trunk_twisted=True,
                trunk_side_bent=True,
                legs_supported_and_balanced=False,
                body_static_or_repeated=True,
                body_load=Load.HEAVY_STATIC_OR_REPEATED,
            )
        )
        self.assertEqual(result.score_c, 13)
        self.assertEqual(result.score_d, 13)
        self.assertEqual(result.grand_score, 7)

    def test_load_and_muscle_only_affect_their_own_group(self):
        result = calculate(posture(arm_load=Load.HEAVY_STATIC_OR_REPEATED))
        self.assertEqual((result.load_a, result.load_b), (3, 0))
        self.assertEqual(result.score_d, 1)


class ActionLevelTests(SimpleTestCase):
    def test_every_grand_score_has_one_level(self):
        expected = {1: 1, 2: 1, 3: 2, 4: 2, 5: 3, 6: 3, 7: 4}
        for score, level in expected.items():
            self.assertEqual(action_level_for(score).level, level)

    def test_every_value_in_table_c_has_a_level(self):
        for row in TABLE_C:
            for score in row:
                action_level_for(score)

    def test_scores_outside_the_method_are_rejected(self):
        for score in (0, 8):
            with self.assertRaises(ValueError):
                action_level_for(score)

    def test_traffic_light_includes_text_meaning(self):
        self.assertEqual(action_level_for(1).traffic_light, TrafficLight.GREEN)
        self.assertEqual(action_level_for(7).traffic_light, TrafficLight.RED)
        self.assertEqual(action_level_for(7).traffic_light_meaning, "Puede requerir intervención inmediata")
