from django.conf import settings
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from apps.core.demo import data
from apps.core.demo.builder import DemoBuilder

DEMO_PASSWORD = data.DEMO_PASSWORD


class Command(BaseCommand):
    help = (
        "Solo para desarrollo: crea datos ficticios con el flujo completo (soporte, ingeniero, "
        "empresas con contrato y acceso, visitas realizadas, por cerrar y futuras, evaluaciones "
        "con los cuatro niveles de RULA y recomendaciones). Se puede ejecutar varias veces."
    )

    def add_arguments(self, parser):
        parser.add_argument("--password", default=DEMO_PASSWORD)

    def handle(self, *args, **options):
        # En produccion el sistema arranca vacio: las cuentas las crea soporte y los datos,
        # el ingeniero. Datos ficticios ahi se confundirian con clientes reales.
        if not settings.DEBUG:
            raise CommandError("seed_demo solo se ejecuta en desarrollo (DEBUG activo).")

        with transaction.atomic():
            counts = DemoBuilder(options["password"]).build()

        self.stdout.write(self.style.SUCCESS("Datos de demostración listos."))
        created = ", ".join(f"{value} {name}" for name, value in counts.items())
        self.stdout.write(f"Nuevos en esta ejecución: {created}.")
        for email, *_ in data.USERS:
            self.stdout.write(f"  {email}")
