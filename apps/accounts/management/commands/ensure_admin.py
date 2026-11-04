import os

from django.contrib.auth import get_user_model
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError
from django.core.management.base import BaseCommand, CommandError


class Command(BaseCommand):
    help = "Crea el administrador inicial desde variables de entorno. No altera una cuenta existente."

    def handle(self, *args, **options):
        email = os.environ.get("DJANGO_ADMIN_EMAIL", "").strip().lower()
        password = os.environ.get("DJANGO_ADMIN_PASSWORD", "")
        if not email or not password:
            self.stdout.write("Sin DJANGO_ADMIN_EMAIL o DJANGO_ADMIN_PASSWORD: no se crea administrador.")
            return

        User = get_user_model()
        if User.objects.filter(email=email).exists():
            self.stdout.write("El administrador ya existe; no se modifica.")
            return

        try:
            validate_password(password, User(email=email))
        except ValidationError as error:
            raise CommandError(f"DJANGO_ADMIN_PASSWORD no es válida: {' '.join(error.messages)}") from error

        User.objects.create_superuser(email=email, password=password)
        self.stdout.write(self.style.SUCCESS("Administrador creado."))
