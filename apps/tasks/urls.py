from django.urls import path

from . import views

app_name = "tasks"

urlpatterns = [
    path("", views.TaskListView.as_view(), name="list"),
    path("recomendaciones/<int:pk>/atender/", views.AttendView.as_view(), name="attend"),
    path("recomendaciones/<int:pk>/reabrir/", views.ReopenView.as_view(), name="reopen"),
]
