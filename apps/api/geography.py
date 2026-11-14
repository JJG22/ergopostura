"""Departamentos y municipios para las listas dependientes de los formularios."""
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.geography.forms import municipality_choices
from apps.geography.models import Department


class DepartmentsView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        return Response([{"id": d.pk, "name": d.name} for d in Department.objects.order_by("name")])


class MunicipalitiesView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        _, municipalities = municipality_choices(request.query_params.get("department"))
        return Response([{"id": m.pk, "name": m.name} for m in municipalities.order_by("name")])
