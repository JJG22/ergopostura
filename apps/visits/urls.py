from django.urls import path

from . import views

app_name = "visits"

urlpatterns = [
    path("", views.VisitListView.as_view(), name="list"),
    path("nueva/", views.VisitCreateView.as_view(), name="create"),
    path("opciones/", views.VisitCascadeView.as_view(), name="cascade"),
    path("<int:pk>/editar/", views.VisitUpdateView.as_view(), name="update"),
]
