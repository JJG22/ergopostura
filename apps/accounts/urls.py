from django.contrib.auth.views import LogoutView
from django.urls import path

from . import views

app_name = "accounts"

urlpatterns = [
    path("ingresar/", views.UserLoginView.as_view(), name="login"),
    path("salir/", LogoutView.as_view(), name="logout"),
    path("cuenta/contrasena/", views.OwnPasswordChangeView.as_view(), name="password_change"),
    path("usuarios/", views.UserListView.as_view(), name="users"),
    path("usuarios/nuevo/", views.UserCreateView.as_view(), name="user_create"),
    path("usuarios/<int:pk>/editar/", views.UserUpdateView.as_view(), name="user_update"),
    path("usuarios/<int:pk>/contrasena/", views.UserPasswordView.as_view(), name="user_password"),
    path("usuarios/<int:pk>/estado/", views.UserToggleActiveView.as_view(), name="user_toggle"),
]
