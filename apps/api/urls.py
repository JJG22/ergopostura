from django.urls import path

from . import views

app_name = "api"

urlpatterns = [
    path("auth/csrf/", views.CsrfView.as_view(), name="csrf"),
    path("auth/login/", views.LoginView.as_view(), name="login"),
    path("auth/logout/", views.LogoutView.as_view(), name="logout"),
    path("auth/session/", views.SessionView.as_view(), name="session"),
    path("auth/password/", views.PasswordView.as_view(), name="password"),
    path("dashboard/", views.DashboardView.as_view(), name="dashboard"),
]
