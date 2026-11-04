from django import forms
from django.contrib.auth.forms import AuthenticationForm


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
    }

    def clean_username(self):
        return self.cleaned_data["username"].strip().lower()
