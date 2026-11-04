"""Reglas del ciclo de vida de una evaluacion."""
from django.db import transaction
from django.utils import timezone

from .models import Evaluation, Posture, PosturePhoto
from .photos import InvalidPhoto, process_photo

MAX_PHOTOS_PER_POSTURE = 10


class EvaluationIncomplete(ValueError):
    def __init__(self, problems: list[str]):
        super().__init__(" ".join(problems))
        self.problems = problems


def completion_problems(evaluation: Evaluation) -> list[str]:
    postures = list(evaluation.postures.all())
    if not postures:
        return ["Agrega al menos una postura."]

    problems = []
    for posture in postures:
        result = posture.result
        if result is None:
            problems.append(f"Falta el análisis RULA de «{posture.name}».")
        elif result.action_level > 1 and not posture.recommendations.all():
            # El nivel 1 es aceptable; desde el nivel 2 el metodo pide investigar o cambiar.
            problems.append(f"Falta una recomendación para «{posture.name}».")
    return problems


def complete_evaluation(evaluation: Evaluation) -> None:
    problems = completion_problems(evaluation)
    if problems:
        raise EvaluationIncomplete(problems)
    evaluation.status = Evaluation.Status.COMPLETED
    evaluation.completed_at = timezone.now()
    evaluation.save(update_fields=["status", "completed_at", "updated_at"])


def reopen_evaluation(evaluation: Evaluation) -> None:
    evaluation.status = Evaluation.Status.DRAFT
    evaluation.completed_at = None
    evaluation.save(update_fields=["status", "completed_at", "updated_at"])


def add_photo(posture: Posture, uploaded) -> PosturePhoto:
    with transaction.atomic():
        # Bloquea la postura para que dos envios simultaneos no superen el limite.
        Posture.objects.select_for_update().get(pk=posture.pk)
        if posture.photos.count() >= MAX_PHOTOS_PER_POSTURE:
            raise InvalidPhoto(f"Cada postura admite hasta {MAX_PHOTOS_PER_POSTURE} fotografías.")
        processed = process_photo(uploaded)
        return PosturePhoto.objects.create(
            posture=posture,
            data=processed.data,
            content_type=processed.content_type,
            width=processed.width,
            height=processed.height,
            original_name=(uploaded.name or "")[:255],
        )
