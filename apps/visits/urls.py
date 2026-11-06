from django.urls import path

from . import views

app_name = "visits"

urlpatterns = [
    path("", views.VisitCalendarView.as_view(), name="list"),
    path("agenda/", views.VisitAgendaView.as_view(), name="agenda"),
    path("nueva/", views.VisitCreateView.as_view(), name="create"),
    path("opciones/", views.VisitCascadeView.as_view(), name="cascade"),
    path("<int:pk>/", views.VisitDetailView.as_view(), name="detail"),
    path("<int:pk>/editar/", views.VisitUpdateView.as_view(), name="update"),
]
