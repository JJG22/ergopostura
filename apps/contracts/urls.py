from django.urls import path

from . import views

app_name = "contracts"

urlpatterns = [
    path("", views.ContractListView.as_view(), name="list"),
    path("nuevo/", views.ContractCreateView.as_view(), name="create"),
    path("leer/", views.ContractReadView.as_view(), name="read"),
    path("<int:pk>/", views.ContractDetailView.as_view(), name="detail"),
    path("<int:pk>/editar/", views.ContractUpdateView.as_view(), name="update"),
    path("<int:pk>/documento/", views.ContractFileView.as_view(), name="file"),
    path("<int:pk>/resumen/", views.ContractSummarizeView.as_view(), name="summarize"),
    path("<int:pk>/eliminar/", views.ContractDeleteView.as_view(), name="delete"),
]
