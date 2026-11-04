from django.contrib.auth.views import LogoutView
from django.urls import path

from .views import UserLoginView

app_name = "accounts"

urlpatterns = [
    path("ingresar/", UserLoginView.as_view(), name="login"),
    path("salir/", LogoutView.as_view(), name="logout"),
]
