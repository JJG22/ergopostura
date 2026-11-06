import json
from urllib.error import URLError
from urllib.request import Request, urlopen

from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from apps.geography import catalog
from apps.geography.models import Department, Municipality


def fetch(path: str):
    request = Request(f"{catalog.API_URL}/{path}", headers={"User-Agent": "ErgoPostura"})
    with urlopen(request, timeout=60) as response:  # noqa: S310 - URL fija de la API
        return json.load(response)


class Command(BaseCommand):
    help = "Actualiza departamentos y municipios desde api-colombia.com. No borra registros."

    def add_arguments(self, parser):
        parser.add_argument(
            "--write-snapshot",
            action="store_true",
            help="Guarda también la respuesta en apps/geography/data/colombia.json.",
        )

    def handle(self, *args, **options):
        try:
            data = catalog.from_api(fetch("Department"), fetch("City"))
        except (URLError, TimeoutError, ValueError, KeyError) as error:
            raise CommandError(f"No se pudo consultar la API: {error}") from error
        if len(data["departments"]) < 33 or len(data["municipalities"]) < 1000:
            # Una respuesta incompleta no debe pasar por un catalogo valido.
            raise CommandError("La API devolvió menos datos de los esperados; no se cambió nada.")

        with transaction.atomic():
            created = catalog.load(data, Department, Municipality)
        self.stdout.write(
            self.style.SUCCESS(
                f"Catálogo actualizado: {created['departments']} departamentos y "
                f"{created['municipalities']} municipios nuevos."
            )
        )
        if options["write_snapshot"]:
            catalog.write_snapshot(data)
            self.stdout.write(f"Copia guardada en {catalog.SNAPSHOT}")
