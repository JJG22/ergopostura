from django.urls import path

from .views import IndicatorsView

app_name = "indicators"

urlpatterns = [
    path("", IndicatorsView.as_view(), name="home"),
]
