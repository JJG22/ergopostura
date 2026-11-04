"""Evaluacion > postura > fotografias, analisis RULA y recomendaciones.

La evaluacion solo guarda el puesto: la empresa sale de la jerarquia, de modo que no puede
presentarse como evaluacion de otra empresa (RNF-002).
"""
from dataclasses import asdict, fields

from django.conf import settings
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models
from django.db.models import Q
from django.db.models.functions import Lower

from apps.companies.models import Position
from apps.core.models import TimeStampedModel
from apps.rula.risk import action_level_for
from apps.rula.scoring import Load, RulaInput, calculate
from apps.visits.models import Visit


class Evaluation(TimeStampedModel):
    class Status(models.TextChoices):
        DRAFT = "borrador", "En curso"
        COMPLETED = "terminada", "Terminada"

    position = models.ForeignKey(
        Position, verbose_name="puesto de trabajo", on_delete=models.PROTECT, related_name="evaluations"
    )
    visit = models.ForeignKey(
        Visit,
        verbose_name="visita",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="evaluations",
    )
    evaluator = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        verbose_name="evaluador",
        on_delete=models.PROTECT,
        related_name="evaluations",
    )
    evaluated_on = models.DateField("fecha de la evaluación")
    status = models.CharField("estado", max_length=20, choices=Status.choices, default=Status.DRAFT)
    completed_at = models.DateTimeField("terminada el", null=True, blank=True)

    activity_description = models.TextField(
        "actividad observada", help_text="Qué hace el trabajador durante la actividad evaluada."
    )
    worker_context = models.TextField(
        "contexto del trabajador",
        blank=True,
        help_text="Solo lo necesario para el análisis. No escribas nombres, documentos ni diagnósticos.",
    )
    carries_load = models.BooleanField("la actividad incluye levantar o cargar peso", default=False)
    load_weight_kg = models.DecimalField(
        "peso aproximado (kg)",
        max_digits=6,
        decimal_places=2,
        null=True,
        blank=True,
        validators=[MinValueValidator(0.01)],
        help_text="Déjalo vacío si no se conoce.",
    )
    repetitive_movements = models.BooleanField("se observan movimientos repetitivos", default=False)
    repetition_notes = models.CharField("detalle de la repetición", max_length=250, blank=True)

    class Meta:
        verbose_name = "evaluación"
        verbose_name_plural = "evaluaciones"
        ordering = ["-evaluated_on", "-pk"]
        constraints = [
            models.CheckConstraint(
                name="evaluation_weight_requires_load",
                condition=Q(load_weight_kg__isnull=True) | Q(carries_load=True, load_weight_kg__gt=0),
            ),
            models.CheckConstraint(
                name="evaluation_completed_has_date",
                condition=Q(status="borrador") | Q(completed_at__isnull=False),
            ),
        ]

    def __str__(self):
        return self.code

    @property
    def code(self) -> str:
        return f"EV-{self.pk:04d}"

    @property
    def company(self):
        return self.position.area.site.company

    @property
    def is_draft(self) -> bool:
        return self.status == self.Status.DRAFT


class Posture(TimeStampedModel):
    class Side(models.TextChoices):
        RIGHT = "derecho", "Lado derecho"
        LEFT = "izquierdo", "Lado izquierdo"

    class DurationUnit(models.TextChoices):
        SECONDS = "segundos", "Segundos"
        MINUTES = "minutos", "Minutos"
        HOURS = "horas", "Horas"

    evaluation = models.ForeignKey(Evaluation, on_delete=models.CASCADE, related_name="postures")
    name = models.CharField("nombre de la postura", max_length=150)
    side = models.CharField(
        "lado evaluado",
        max_length=10,
        choices=Side.choices,
        default=Side.RIGHT,
        help_text="RULA evalúa un lado a la vez.",
    )
    duration_value = models.DecimalField(
        "tiempo en la postura", max_digits=7, decimal_places=2, validators=[MinValueValidator(0.01)]
    )
    duration_unit = models.CharField(
        "unidad de tiempo", max_length=10, choices=DurationUnit.choices, default=DurationUnit.MINUTES
    )

    class Meta:
        verbose_name = "postura"
        verbose_name_plural = "posturas"
        ordering = ["pk"]
        constraints = [
            models.UniqueConstraint(
                "evaluation", Lower("name"), "side", name="posture_unique_name_side_in_evaluation"
            ),
            models.CheckConstraint(name="posture_duration_positive", condition=Q(duration_value__gt=0)),
        ]

    def __str__(self):
        return f"{self.name} ({self.get_side_display()})"

    @property
    def result(self):
        """El analisis de la postura, o None si aun no se ha hecho."""
        return getattr(self, "assessment", None)


class PosturePhoto(TimeStampedModel):
    """La imagen se guarda en PostgreSQL, ya optimizada y sin metadatos.

    Asi la evidencia queda protegida por la misma base de datos y solo se entrega a
    quien puede ver la evaluacion. Tambien sobrevive en servidores sin disco persistente.
    """

    posture = models.ForeignKey(Posture, on_delete=models.CASCADE, related_name="photos")
    data = models.BinaryField("imagen", editable=False)
    content_type = models.CharField(max_length=50, editable=False)
    width = models.PositiveIntegerField(editable=False)
    height = models.PositiveIntegerField(editable=False)
    original_name = models.CharField("archivo original", max_length=255, blank=True)

    class Meta:
        verbose_name = "fotografía"
        verbose_name_plural = "fotografías"
        ordering = ["pk"]

    def __str__(self):
        return self.original_name or f"Fotografía {self.pk}"


class RulaAssessment(TimeStampedModel):
    """Datos registrados por el evaluador y los puntajes que produjeron.

    Los campos de entrada se llaman igual que los de RulaInput. Los puntajes se guardan
    para que una evaluacion terminada no cambie si mas adelante se ajusta el calculo.
    """

    LOAD_CHOICES = [(load.name, load.label) for load in Load]
    METHOD = "RULA (McAtamney y Corlett, 1993)"

    posture = models.OneToOneField(Posture, on_delete=models.CASCADE, related_name="assessment")
    # RESTRICT: no se borra una foto analizada, salvo que se borre toda la postura.
    photo = models.ForeignKey(
        PosturePhoto, verbose_name="fotografía analizada", on_delete=models.RESTRICT, related_name="assessments"
    )
    method = models.CharField("método", max_length=80, default=METHOD, editable=False)

    upper_arm_angle = models.DecimalField("Ángulo del brazo", max_digits=4, decimal_places=1)
    shoulder_raised = models.BooleanField("Hombro elevado", default=False)
    upper_arm_abducted = models.BooleanField("Brazo separado del cuerpo (abducción)", default=False)
    arm_supported = models.BooleanField("Brazo apoyado o trabajador inclinado", default=False)
    lower_arm_angle = models.DecimalField("Ángulo del antebrazo", max_digits=4, decimal_places=1)
    lower_arm_across_midline_or_out = models.BooleanField("Cruza la línea media o trabaja hacia afuera", default=False)
    wrist_angle = models.DecimalField("Ángulo de la muñeca", max_digits=4, decimal_places=1)
    wrist_bent_from_midline = models.BooleanField("Muñeca desviada de la línea media", default=False)
    wrist_twist_near_end = models.BooleanField("Giro de muñeca cerca del final del rango", default=False)
    arm_static_or_repeated = models.BooleanField(
        "Postura estática (más de 1 minuto) o repetida (más de 4 veces por minuto)", default=False
    )
    arm_load = models.CharField("Carga o fuerza", max_length=30, choices=LOAD_CHOICES, default=Load.NONE_OR_LIGHT_INTERMITTENT.name)

    neck_angle = models.DecimalField("Ángulo del cuello", max_digits=4, decimal_places=1)
    neck_twisted = models.BooleanField("Cuello girado", default=False)
    neck_side_bent = models.BooleanField("Cuello inclinado hacia un lado", default=False)
    trunk_angle = models.DecimalField("Ángulo del tronco", max_digits=4, decimal_places=1)
    trunk_supported_seated = models.BooleanField("Sentado con el tronco bien apoyado", default=False)
    trunk_twisted = models.BooleanField("Tronco girado", default=False)
    trunk_side_bent = models.BooleanField("Tronco inclinado hacia un lado", default=False)
    legs_supported_and_balanced = models.BooleanField("Piernas y pies apoyados y con el peso equilibrado", default=True)
    body_static_or_repeated = models.BooleanField(
        "Postura estática (más de 1 minuto) o repetida (más de 4 veces por minuto)", default=False
    )
    body_load = models.CharField("Carga o fuerza", max_length=30, choices=LOAD_CHOICES, default=Load.NONE_OR_LIGHT_INTERMITTENT.name)

    partial_scores = models.JSONField("puntajes parciales", default=dict, editable=False)
    grand_score = models.PositiveSmallIntegerField(
        "puntaje final", validators=[MinValueValidator(1), MaxValueValidator(7)], editable=False
    )
    action_level = models.PositiveSmallIntegerField(
        "nivel de acción", validators=[MinValueValidator(1), MaxValueValidator(4)], editable=False
    )

    class Meta:
        verbose_name = "análisis RULA"
        verbose_name_plural = "análisis RULA"
        constraints = [
            models.CheckConstraint(name="assessment_grand_score_range", condition=Q(grand_score__range=(1, 7))),
            models.CheckConstraint(name="assessment_action_level_range", condition=Q(action_level__range=(1, 4))),
        ]

    def __str__(self):
        return f"RULA {self.grand_score} · {self.posture}"

    @property
    def action(self):
        return action_level_for(self.grand_score)

    def recalculate(self):
        result = calculate(rula_input_from(self.__dict__))
        self.partial_scores = asdict(result)
        self.grand_score = result.grand_score
        self.action_level = action_level_for(result.grand_score).level


def rula_input_from(values) -> RulaInput:
    """Convierte datos del formulario o del modelo en la entrada del motor de calculo."""
    data = {field.name: values[field.name] for field in fields(RulaInput)}
    for name in ("upper_arm_angle", "lower_arm_angle", "wrist_angle", "neck_angle", "trunk_angle"):
        data[name] = float(data[name])
    for name in ("arm_load", "body_load"):
        data[name] = Load[data[name]]
    return RulaInput(**data)


class Recommendation(TimeStampedModel):
    """La escribe el evaluador despues de ver el resultado de la postura (D5)."""

    posture = models.ForeignKey(Posture, on_delete=models.CASCADE, related_name="recommendations")
    text = models.TextField("recomendación")
    author = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="recommendations", editable=False
    )
    # Seguimiento (RF-029). Cambiar este estado no altera el resultado de la evaluacion.
    attended_at = models.DateTimeField("atendida el", null=True, blank=True, editable=False)
    attended_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        verbose_name="atendida por",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="attended_recommendations",
        editable=False,
    )

    class Meta:
        verbose_name = "recomendación"
        verbose_name_plural = "recomendaciones"
        ordering = ["pk"]

    def __str__(self):
        return self.text[:60]
