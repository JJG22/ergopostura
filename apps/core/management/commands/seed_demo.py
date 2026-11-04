from datetime import timedelta

from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from django.utils import timezone

from apps.accounts.models import Role
from apps.companies.models import Area, Company, Position, Site
from apps.visits.models import Visit

DEMO_PASSWORD = "ErgoDemo2026!"

DEMO_USERS = (
    ("admin@ergopostura.test", "Ana", "Administradora", Role.ADMIN),
    ("ingeniero@ergopostura.test", "Andrés", "Ríos", Role.ENGINEER),
    ("evaluador@ergopostura.test", "Laura", "Gómez", Role.EVALUATOR),
    ("empresa@ergopostura.test", "Marta", "Salazar", Role.COMPANY),
    ("consulta@ergopostura.test", "Carlos", "Mejía", Role.RESULTS),
    ("tareas@ergopostura.test", "Sofía", "Duque", Role.TASKS),
)


class Command(BaseCommand):
    help = "Crea datos ficticios para desarrollo. Se puede ejecutar varias veces."

    def add_arguments(self, parser):
        parser.add_argument("--password", default=DEMO_PASSWORD)

    @transaction.atomic
    def handle(self, *args, **options):
        if not settings.DEBUG:
            raise CommandError("seed_demo solo se ejecuta con DEBUG activo.")

        coffee = self._company("Café Montaña S.A.S.", "900123456", "Armenia", "Quindío")
        plant, _ = Site.objects.get_or_create(
            company=coffee, name="Planta Armenia", defaults={"city": "Armenia", "department": "Quindío"}
        )
        warehouse, _ = Site.objects.get_or_create(
            company=coffee, name="Bodega Calarcá", defaults={"city": "Calarcá", "department": "Quindío"}
        )
        packing, _ = Area.objects.get_or_create(site=plant, name="Empaque")
        admin_area, _ = Area.objects.get_or_create(site=plant, name="Administración")
        storage, _ = Area.objects.get_or_create(site=warehouse, name="Almacenamiento")
        Position.objects.get_or_create(area=packing, name="Operario de empaque")
        Position.objects.get_or_create(area=admin_area, name="Digitador")
        Position.objects.get_or_create(area=storage, name="Auxiliar de bodega")

        self._company("Muebles del Eje Ltda.", "901234567", "Pereira", "Risaralda")

        User = get_user_model()
        for email, first_name, last_name, role in DEMO_USERS:
            if User.objects.filter(email=email).exists():
                continue
            User.objects.create_user(
                email=email,
                password=options["password"],
                first_name=first_name,
                last_name=last_name,
                role=role,
                company=coffee if role == Role.COMPANY else None,
            )

        if not Visit.objects.exists():
            author = User.objects.get(email="empresa@ergopostura.test")
            start = timezone.localtime().replace(hour=9, minute=0, second=0, microsecond=0)
            for days, position_name in ((3, "Operario de empaque"), (5, "Digitador"), (8, "Auxiliar de bodega")):
                Visit.objects.create(
                    position=Position.objects.get(name=position_name, area__site__company=coffee),
                    scheduled_at=start + timedelta(days=days),
                    contact_name="Marta Salazar",
                    created_by=author,
                )

        self.stdout.write(self.style.SUCCESS("Datos de demostración listos."))
        for email, *_ in DEMO_USERS:
            self.stdout.write(f"  {email}")

    @staticmethod
    def _company(name, nit, city, department):
        company, _ = Company.objects.get_or_create(
            nit=nit, defaults={"name": name, "city": city, "department": department}
        )
        return company
