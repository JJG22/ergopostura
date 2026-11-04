from django.urls import path

from . import views

app_name = "companies"

urlpatterns = [
    path("", views.CompanyListView.as_view(), name="list"),
    path("nueva/", views.CompanyCreateView.as_view(), name="create"),
    path("<int:pk>/", views.CompanyDetailView.as_view(), name="detail"),
    path("<int:pk>/editar/", views.CompanyUpdateView.as_view(), name="update"),
    path("<int:parent_pk>/sedes/nueva/", views.SiteCreateView.as_view(), name="site_create"),
    path("sedes/<int:pk>/editar/", views.SiteUpdateView.as_view(), name="site_update"),
    path("sedes/<int:parent_pk>/areas/nueva/", views.AreaCreateView.as_view(), name="area_create"),
    path("areas/<int:pk>/editar/", views.AreaUpdateView.as_view(), name="area_update"),
    path("areas/<int:parent_pk>/puestos/nuevo/", views.PositionCreateView.as_view(), name="position_create"),
    path("puestos/<int:pk>/editar/", views.PositionUpdateView.as_view(), name="position_update"),
]
