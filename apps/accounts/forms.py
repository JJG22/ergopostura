from django import forms
from django.contrib.auth import password_validation
from django.contrib.auth.forms import AuthenticationForm, PasswordChangeForm, SetPasswordForm

from apps.companies.models import Company

from .models import Role, User
from .permissions import Capability, has_capability


class LoginForm(AuthenticationForm):
    username = forms.EmailField(
        label="Correo electrónico",
        widget=forms.EmailInput(
            attrs={"autofocus": True, "autocomplete": "email", "placeholder": "nombre@empresa.com"}
        ),
    )
    remember = forms.BooleanField(label="Recordarme", required=False)

    error_messages = {
        **AuthenticationForm.error_messages,
        "invalid_login": "El correo o la contraseña no son correctos.",
        "inactive": "Esta cuenta está desactivada. Comunícate con quien te dio el acceso.",
    }

    def clean_username(self):
        return self.cleaned_data["username"].strip().lower()


def creatable_roles(actor) -> list[str]:
    """Soporte crea cuentas de soporte y de ingeniero; el ingeniero, las de sus empresas."""
    roles = []
    if has_capability(actor, Capability.USER_MANAGE):
        roles += [Role.ENGINEER, Role.ADMIN]
    if has_capability(actor, Capability.COMPANY_USER_MANAGE):
        roles.append(Role.COMPANY)
    return roles


class AccountForm(forms.ModelForm):
    """Datos de la cuenta. La empresa solo aplica, y es obligatoria, para el rol Empresa."""

    class Meta:
        model = User
        fields = ["first_name", "last_name", "email", "role", "company"]
        labels = {"first_name": "Nombres", "last_name": "Apellidos"}
        widgets = {
            "email": forms.EmailInput(attrs={"autocomplete": "off", "placeholder": "nombre@empresa.com"}),
        }

    def __init__(self, *args, actor, company=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.actor = actor
        self.fields["first_name"].required = True
        roles = creatable_roles(actor)

        if self.instance.pk:
            # El rol define permisos y datos asociados: para cambiarlo se crea otra cuenta.
            del self.fields["role"]
            if self.instance.role != Role.COMPANY:
                del self.fields["company"]
        else:
            self.fields["role"].choices = [(role.value, role.label) for role in map(Role, roles)]
            if len(roles) == 1:
                self.fields["role"].initial = roles[0]
                self.fields["role"].widget = forms.HiddenInput()

        if "company" in self.fields:
            companies = Company.objects.filter(is_active=True)
            if self.instance.pk and self.instance.company_id:
                companies = companies | Company.objects.filter(pk=self.instance.company_id)
            field = self.fields["company"]
            field.queryset = companies.order_by("name")
            field.empty_label = "Selecciona la empresa"
            field.help_text = "La cuenta solo verá los datos de esta empresa."
            if company is not None:
                field.initial = company.pk
            if Role.COMPANY not in roles and not self.instance.pk:
                del self.fields["company"]

    def clean_email(self):
        email = self.cleaned_data["email"].strip().lower()
        if User.objects.filter(email__iexact=email).exclude(pk=self.instance.pk).exists():
            raise forms.ValidationError("Ya existe una cuenta con este correo.")
        return email

    def clean(self):
        cleaned = super().clean()
        role = cleaned.get("role", self.instance.role)
        if role == Role.COMPANY:
            if not cleaned.get("company") and "company" in self.fields:
                self.add_error("company", "Elige la empresa a la que pertenece la cuenta.")
        else:
            cleaned["company"] = None
        return cleaned


class AccountCreateForm(AccountForm):
    password1 = forms.CharField(
        label="Contraseña temporal",
        strip=False,
        widget=forms.PasswordInput(attrs={"autocomplete": "new-password"}),
        help_text="Entrégala a la persona. Deberá cambiarla la primera vez que ingrese.",
    )
    password2 = forms.CharField(
        label="Repite la contraseña",
        strip=False,
        widget=forms.PasswordInput(attrs={"autocomplete": "new-password"}),
    )

    def clean(self):
        cleaned = super().clean()
        first, second = cleaned.get("password1"), cleaned.get("password2")
        if first and second and first != second:
            self.add_error("password2", "Las contraseñas no coinciden.")
        elif first:
            candidate = User(
                email=cleaned.get("email", ""),
                first_name=cleaned.get("first_name", ""),
                last_name=cleaned.get("last_name", ""),
            )
            try:
                password_validation.validate_password(first, candidate)
            except forms.ValidationError as error:
                self.add_error("password1", error)
        return cleaned

    def save(self, commit=True):
        user = super().save(commit=False)
        user.set_password(self.cleaned_data["password1"])
        user.must_change_password = True
        user.created_by = self.actor
        if commit:
            user.save()
        return user


class TemporaryPasswordForm(SetPasswordForm):
    """Quien gestiona la cuenta asigna una clave temporal; el titular la cambia al entrar."""

    def __init__(self, user, *args, **kwargs):
        super().__init__(user, *args, **kwargs)
        self.fields["new_password1"].label = "Nueva contraseña temporal"
        self.fields["new_password1"].help_text = "La persona deberá cambiarla al ingresar."
        self.fields["new_password2"].label = "Repite la contraseña"

    def save(self, commit=True):
        self.user.must_change_password = True
        return super().save(commit=commit)


class OwnPasswordForm(PasswordChangeForm):
    def save(self, commit=True):
        self.user.must_change_password = False
        return super().save(commit=commit)
