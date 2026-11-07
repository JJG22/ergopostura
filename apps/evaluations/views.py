from django.contrib import messages
from django.db import transaction
from django.db.models import RestrictedError
from django.http import HttpResponse
from django.shortcuts import get_object_or_404, redirect
from django.urls import reverse
from django.utils.functional import cached_property
from django.views import View
from django.views.generic import CreateView, DetailView, ListView, UpdateView

from apps.accounts.mixins import CapabilityRequiredMixin
from apps.accounts.permissions import Capability, has_capability
from apps.companies.cascade import PositionCascadeView
from apps.core.views import ModalFormMixin

from . import selectors, services
from .forms import EvaluationForm, PostureForm, RecommendationForm, RulaAssessmentForm
from .models import Evaluation, PosturePhoto, Recommendation, RulaAssessment
from .photos import InvalidPhoto

VIEW_CAPABILITIES = (
    Capability.EVALUATION_VIEW_ALL,
    Capability.EVALUATION_VIEW_OWN,
)


def detail_url(evaluation, posture=None) -> str:
    url = reverse("evaluations:detail", args=[evaluation.pk])
    return f"{url}#postura-{posture.pk}" if posture else url


class ManageMixin(CapabilityRequiredMixin):
    required_capabilities = (Capability.EVALUATION_MANAGE,)


class EvaluationListView(CapabilityRequiredMixin, ListView):
    required_capabilities = VIEW_CAPABILITIES
    template_name = "evaluations/list.html"
    context_object_name = "evaluations"
    paginate_by = 15

    def get_queryset(self):
        return selectors.search_evaluations(self.request.user, self.request.GET.get("q", ""))

    def get_context_data(self, **kwargs):
        return super().get_context_data(query=self.request.GET.get("q", "").strip(), **kwargs)


class EvaluationDetailView(CapabilityRequiredMixin, DetailView):
    required_capabilities = VIEW_CAPABILITIES
    template_name = "evaluations/detail.html"
    context_object_name = "evaluation"

    def get_queryset(self):
        return selectors.with_details(selectors.visible_evaluations(self.request.user))

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        evaluation = self.object
        user = self.request.user
        can_edit = (
            evaluation.is_draft
            and evaluation.evaluator_id == user.pk
            and has_capability(user, Capability.EVALUATION_MANAGE)
        )
        context.update(
            can_edit=can_edit,
            can_reopen=not evaluation.is_draft and has_capability(user, Capability.EVALUATION_REOPEN),
            completion_problems=services.completion_problems(evaluation) if can_edit else [],
            recommendation_form=RecommendationForm(),
        )
        return context


class EvaluationReportView(CapabilityRequiredMixin, DetailView):
    """Informe para imprimir o guardar como PDF (RF-028). Solo de evaluaciones terminadas."""

    required_capabilities = VIEW_CAPABILITIES
    template_name = "evaluations/report.html"
    context_object_name = "evaluation"

    def get_queryset(self):
        return selectors.with_details(
            selectors.visible_evaluations(self.request.user).filter(status=Evaluation.Status.COMPLETED)
        )


class EvaluationCreateView(ManageMixin, ModalFormMixin, CreateView):
    form_class = EvaluationForm
    title = "Nueva evaluación"
    submit_label = "Crear evaluación"
    note = "Parte de una visita realizada. Después agregarás las posturas, sus fotografías y el análisis RULA."
    success_title = "Evaluación creada"

    def get_form_kwargs(self):
        return {**super().get_form_kwargs(), "user": self.request.user}

    def get_initial(self):
        """Al iniciar desde una visita, la deja elegida."""
        initial = super().get_initial()
        visit_id = self.request.GET.get("visita", "")
        if visit_id.isdigit():
            initial["visit"] = int(visit_id)
        return initial

    def get_cancel_url(self):
        return reverse("evaluations:list")

    def get_success_url(self):
        return detail_url(self.object)


class EvaluationUpdateView(ManageMixin, ModalFormMixin, UpdateView):
    form_class = EvaluationForm
    title = "Editar evaluación"
    success_title = "Evaluación actualizada"

    def get_queryset(self):
        return selectors.editable_evaluations(self.request.user)

    def get_form_kwargs(self):
        return {**super().get_form_kwargs(), "user": self.request.user}

    def get_cancel_url(self):
        return detail_url(self.object)

    def get_success_url(self):
        return detail_url(self.object)


class EvaluationCascadeView(PositionCascadeView):
    required_capabilities = (Capability.EVALUATION_MANAGE,)
    form_class = EvaluationForm


class EvaluationCompleteView(ManageMixin, View):
    def post(self, request, pk):
        evaluation = get_object_or_404(
            selectors.with_details(selectors.editable_evaluations(request.user)), pk=pk
        )
        try:
            services.complete_evaluation(evaluation)
        except services.EvaluationIncomplete as error:
            messages.error(request, str(error))
        else:
            messages.success(request, "Evaluación terminada")
        return redirect(detail_url(evaluation))


class EvaluationReopenView(CapabilityRequiredMixin, View):
    required_capabilities = (Capability.EVALUATION_REOPEN,)

    def post(self, request, pk):
        evaluation = get_object_or_404(selectors.visible_evaluations(request.user), pk=pk)
        services.reopen_evaluation(evaluation)
        messages.success(request, "Evaluación reabierta")
        return redirect(detail_url(evaluation))


class PostureCreateView(ManageMixin, ModalFormMixin, CreateView):
    form_class = PostureForm
    title = "Agregar postura"
    success_title = "Postura agregada"
    integrity_error_message = "Esta evaluación ya tiene esa postura para el mismo lado."

    @cached_property
    def evaluation(self):
        return get_object_or_404(selectors.editable_evaluations(self.request.user), pk=self.kwargs["pk"])

    def get_form_kwargs(self):
        return {**super().get_form_kwargs(), "evaluation": self.evaluation}

    def get_cancel_url(self):
        return detail_url(self.evaluation)

    def get_success_url(self):
        return detail_url(self.evaluation, self.object)


class PostureUpdateView(ManageMixin, ModalFormMixin, UpdateView):
    form_class = PostureForm
    title = "Editar postura"
    integrity_error_message = "Esta evaluación ya tiene esa postura para el mismo lado."

    def get_queryset(self):
        return selectors.editable_postures(self.request.user)

    def get_cancel_url(self):
        return detail_url(self.object.evaluation, self.object)

    def get_success_url(self):
        return detail_url(self.object.evaluation, self.object)


class PostureDeleteView(ManageMixin, View):
    def post(self, request, pk):
        posture = get_object_or_404(selectors.editable_postures(request.user), pk=pk)
        evaluation = posture.evaluation
        posture.delete()
        messages.success(request, "Postura eliminada")
        return redirect(detail_url(evaluation))


class PhotoUploadView(ManageMixin, View):
    def post(self, request, pk):
        posture = get_object_or_404(selectors.editable_postures(request.user), pk=pk)
        uploaded = request.FILES.get("photo")
        if uploaded is None:
            messages.error(request, "Elige una fotografía.")
        else:
            try:
                services.add_photo(posture, uploaded)
            except InvalidPhoto as error:
                messages.error(request, str(error))
            else:
                messages.success(request, "Fotografía agregada")
        return redirect(detail_url(posture.evaluation, posture))


class PhotoDeleteView(ManageMixin, View):
    def post(self, request, pk):
        photo = get_object_or_404(
            PosturePhoto.objects.defer("data").select_related("posture__evaluation").filter(
                posture__in=selectors.editable_postures(request.user)
            ),
            pk=pk,
        )
        posture = photo.posture
        try:
            with transaction.atomic():
                photo.delete()
        except RestrictedError:
            messages.error(request, "Esta fotografía sustenta el análisis. Elige otra en el análisis antes de eliminarla.")
        else:
            messages.success(request, "Fotografía eliminada")
        return redirect(detail_url(posture.evaluation, posture))


class PhotoView(CapabilityRequiredMixin, View):
    """Entrega la imagen solo a quien puede ver su evaluacion: nunca es una URL publica."""

    required_capabilities = VIEW_CAPABILITIES

    def get(self, request, pk):
        photo = get_object_or_404(
            PosturePhoto.objects.filter(posture__evaluation__in=selectors.visible_evaluations(request.user).values("pk")),
            pk=pk,
        )
        response = HttpResponse(bytes(photo.data), content_type=photo.content_type)
        response["Cache-Control"] = "private, max-age=3600"
        response["X-Content-Type-Options"] = "nosniff"
        return response


class AssessmentView(ManageMixin, ModalFormMixin, UpdateView):
    """Registra los segmentos y angulos (RF-015, RF-016) y calcula el resultado."""

    form_class = RulaAssessmentForm
    template_name = "evaluations/assessment.html"
    modal_template_name = "evaluations/assessment.html"
    title = "Análisis RULA"
    success_title = "Análisis guardado"
    integrity_error_message = "Otra sesión guardó este análisis. Recarga la página."

    @cached_property
    def posture(self):
        return get_object_or_404(selectors.editable_postures(self.request.user), pk=self.kwargs["pk"])

    @cached_property
    def photos(self):
        return selectors.posture_photos(self.posture)

    def dispatch(self, request, *args, **kwargs):
        if request.user.is_authenticated and has_capability(request.user, Capability.EVALUATION_MANAGE):
            # El analisis corresponde a una fotografia elegida (RF-014).
            if not self.photos.exists():
                messages.error(request, "Agrega una fotografía antes de hacer el análisis.")
                return redirect(detail_url(self.posture.evaluation, self.posture))
        return super().dispatch(request, *args, **kwargs)

    def get_object(self, queryset=None):
        return RulaAssessment.objects.filter(posture=self.posture).first()

    def get_form_kwargs(self):
        return {**super().get_form_kwargs(), "posture": self.posture, "photos": self.photos}

    def get_initial(self):
        return {} if self.object else {"photo": self.photos.first()}

    def get_context_data(self, **kwargs):
        return super().get_context_data(posture=self.posture, photos=self.photos, **kwargs)

    def get_cancel_url(self):
        return detail_url(self.posture.evaluation, self.posture)

    def get_success_url(self):
        return detail_url(self.posture.evaluation, self.posture)


class RecommendationCreateView(ManageMixin, View):
    def post(self, request, pk):
        posture = get_object_or_404(selectors.editable_postures(request.user).select_related("assessment"), pk=pk)
        target = detail_url(posture.evaluation, posture)
        # Se escribe despues de ver el resultado (D5).
        if posture.result is None:
            messages.error(request, "Primero haz el análisis RULA de esta postura.")
            return redirect(target)

        form = RecommendationForm(request.POST)
        if form.is_valid():
            form.instance.posture = posture
            form.instance.author = request.user
            form.save()
            messages.success(request, "Recomendación agregada")
        else:
            messages.error(request, "Escribe la recomendación.")
        return redirect(target)


class RecommendationDeleteView(ManageMixin, View):
    def post(self, request, pk):
        recommendation = get_object_or_404(
            Recommendation.objects.select_related("posture__evaluation").filter(
                posture__in=selectors.editable_postures(request.user)
            ),
            pk=pk,
        )
        posture = recommendation.posture
        recommendation.delete()
        messages.success(request, "Recomendación eliminada")
        return redirect(detail_url(posture.evaluation, posture))
