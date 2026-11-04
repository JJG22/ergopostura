from django.urls import path

from . import views

app_name = "evaluations"

urlpatterns = [
    path("", views.EvaluationListView.as_view(), name="list"),
    path("nueva/", views.EvaluationCreateView.as_view(), name="create"),
    path("opciones/", views.EvaluationCascadeView.as_view(), name="cascade"),
    path("<int:pk>/", views.EvaluationDetailView.as_view(), name="detail"),
    path("<int:pk>/informe/", views.EvaluationReportView.as_view(), name="report"),
    path("<int:pk>/editar/", views.EvaluationUpdateView.as_view(), name="update"),
    path("<int:pk>/terminar/", views.EvaluationCompleteView.as_view(), name="complete"),
    path("<int:pk>/reabrir/", views.EvaluationReopenView.as_view(), name="reopen"),
    path("<int:pk>/posturas/nueva/", views.PostureCreateView.as_view(), name="posture_create"),
    path("posturas/<int:pk>/editar/", views.PostureUpdateView.as_view(), name="posture_update"),
    path("posturas/<int:pk>/eliminar/", views.PostureDeleteView.as_view(), name="posture_delete"),
    path("posturas/<int:pk>/fotos/", views.PhotoUploadView.as_view(), name="photo_upload"),
    path("posturas/<int:pk>/analisis/", views.AssessmentView.as_view(), name="assessment"),
    path("posturas/<int:pk>/recomendaciones/", views.RecommendationCreateView.as_view(), name="recommendation_create"),
    path("fotos/<int:pk>/", views.PhotoView.as_view(), name="photo"),
    path("fotos/<int:pk>/eliminar/", views.PhotoDeleteView.as_view(), name="photo_delete"),
    path("recomendaciones/<int:pk>/eliminar/", views.RecommendationDeleteView.as_view(), name="recommendation_delete"),
]
