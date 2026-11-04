from django.contrib.auth.models import AbstractUser, BaseUserManager
from django.core.exceptions import ValidationError
from django.db import models
from django.db.models import Q


class Role(models.TextChoices):
    ADMIN = "admin", "Administrador"
    ENGINEER = "ingeniero", "Ingeniero industrial"
    EVALUATOR = "evaluador", "Evaluador"
    COMPANY = "empresa", "Empresa"
    RESULTS = "consulta", "Consulta de resultados"
    TASKS = "tareas", "Responsable de tarea"


class UserManager(BaseUserManager):
    use_in_migrations = True

    def _create(self, email, password, **fields):
        if not email:
            raise ValueError("El correo es obligatorio.")
        user = self.model(email=email, **fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_user(self, email, password=None, **fields):
        return self._create(email, password, **fields)

    def create_superuser(self, email, password=None, **fields):
        fields["role"] = Role.ADMIN
        return self._create(email, password, **fields)

    def get_by_natural_key(self, email):
        return self.get(email__iexact=email)


class User(AbstractUser):
    """El rol es la unica fuente de permisos; is_staff e is_superuser se derivan de el."""

    username = None
    email = models.EmailField(
        "correo electrónico",
        unique=True,
        error_messages={"unique": "Ya existe un usuario con este correo."},
    )
    role = models.CharField("rol", max_length=20, choices=Role.choices)
    company = models.ForeignKey(
        "companies.Company",
        verbose_name="empresa",
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="users",
        help_text="Obligatoria solo para el rol Empresa.",
    )

    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = []

    objects = UserManager()

    class Meta:
        verbose_name = "usuario"
        verbose_name_plural = "usuarios"
        ordering = ["email"]
        constraints = [
            models.CheckConstraint(name="user_role_valid", condition=Q(role__in=Role.values)),
            models.CheckConstraint(
                name="user_company_only_for_company_role",
                condition=(
                    Q(role="empresa", company__isnull=False)
                    | (~Q(role="empresa") & Q(company__isnull=True))
                ),
                violation_error_message="Solo el rol Empresa se asocia a una empresa, y es obligatoria.",
            ),
        ]

    def __str__(self):
        return self.get_full_name() or self.email

    def clean(self):
        super().clean()
        self.email = self.email.strip().lower()
        if self.role == Role.COMPANY and self.company_id is None:
            raise ValidationError({"company": "El rol Empresa debe tener una empresa asociada."})
        if self.role != Role.COMPANY and self.company_id is not None:
            raise ValidationError({"company": "Solo el rol Empresa se asocia a una empresa."})

    def save(self, *args, **kwargs):
        self.email = self.email.strip().lower()
        self.is_staff = self.is_superuser = self.role == Role.ADMIN
        super().save(*args, **kwargs)

    @property
    def initials(self) -> str:
        names = [self.first_name, self.last_name]
        letters = "".join(name[0] for name in names if name)
        return (letters or self.email[0]).upper()
