from django.contrib import messages
from django.db import IntegrityError, transaction
from django.http import HttpResponse
from django.shortcuts import redirect


def is_htmx(request) -> bool:
    return request.headers.get("HX-Request") == "true"


class ModalFormMixin:
    """Formulario que abre en modal con HTMX y como pagina normal sin JavaScript.

    La validacion del formulario da el mensaje amable. La restriccion de la base
    de datos sigue siendo la garantia real: si dos personas guardan el mismo dato
    a la vez, el IntegrityError se convierte en un error visible y no en un 500.
    """

    template_name = "core/form_page.html"
    modal_template_name = "core/partials/modal_form.html"
    title = ""
    submit_label = "Guardar"
    note = ""
    success_title = "Cambios guardados"
    integrity_error_message = "Otro usuario acaba de registrar este dato. Revisa la información."

    def get_template_names(self):
        return [self.modal_template_name if is_htmx(self.request) else self.template_name]

    def get_cancel_url(self) -> str:
        raise NotImplementedError

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context.update(
            title=self.title,
            submit_label=self.submit_label,
            note=self.note,
            cancel_url=self.get_cancel_url(),
            is_modal=is_htmx(self.request),
        )
        return context

    def form_valid(self, form):
        try:
            with transaction.atomic():
                self.object = form.save()
        except IntegrityError:
            form.add_error(None, self.integrity_error_message)
            return self.form_invalid(form)

        messages.success(self.request, self.success_title)
        url = self.get_success_url()
        if is_htmx(self.request):
            return HttpResponse(status=204, headers={"HX-Redirect": url})
        return redirect(url)
