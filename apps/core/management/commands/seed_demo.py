from django.conf import settings
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from apps.core.demo import data
from apps.core.demo.builder import DemoBuilder

DEMO_PASSWORD = data.DEMO_PASSWORD


class Command(BaseCommand):
    help = (
        "Crea datos ficticios para probar el sistema: empresas en varios departamentos, usuarios de "
        "cada rol, visitas pasadas y futuras, evaluaciones terminadas y en curso con los cuatro niveles "
        "de RULA, y recomendaciones atendidas y pendientes. Se puede ejecutar varias veces."
    )

    def add_arguments(self, parser):
        parser.add_argument("--password", default=DEMO_PASSWORD)
        parser.add_argument(
            "--allow-production",
            action="store_true",
            help="Permite ejecutarlo sin DEBUG; exige una clave distinta a la publicada en el repositorio.",
        )

    def handle(self, *args, **options):
        if not settings.DEBUG:
            if not options["allow_production"]:
                raise CommandError("seed_demo solo se ejecuta con DEBUG activo.")
            if options["password"] == DEMO_PASSWORD:
                raise CommandError("En producción no se permite la clave de demostración publicada.")

        with transaction.atomic():
            counts = DemoBuilder(options["password"]).build()

        self.stdout.write(self.style.SUCCESS("Datos de demostración listos."))
        created = ", ".join(f"{value} {name}" for name, value in counts.items())
        self.stdout.write(f"Nuevos en esta ejecución: {created}.")
        for email, *_ in data.USERS:
            self.stdout.write(f"  {email}")
