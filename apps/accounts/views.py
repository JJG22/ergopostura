from django.contrib.auth.views import LoginView

from .forms import LoginForm


class UserLoginView(LoginView):
    template_name = "accounts/login.html"
    authentication_form = LoginForm
    redirect_authenticated_user = True

    def form_valid(self, form):
        response = super().form_valid(form)
        if not form.cleaned_data["remember"]:
            self.request.session.set_expiry(0)
        return response
