from django.urls import path

from . import views

app_name = "geography"

urlpatterns = [
    path("municipios/", views.MunicipalityOptionsView.as_view(), name="municipalities"),
]
