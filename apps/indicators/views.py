from django.views.generic import TemplateView

from apps.accounts.mixins import CapabilityRequiredMixin
from apps.accounts.permissions import Capability, has_capability

from . import selectors
from .metrics import distribution


class IndicatorsView(CapabilityRequiredMixin, TemplateView):
    required_capabilities = (Capability.INDICATORS_VIEW,)
    template_name = "indicators/home.html"

    @property
    def limited_to_own_company(self) -> bool:
        """Quien no puede ver las evaluaciones de todas las empresas ve solo la suya."""
        return not has_capability(self.request.user, Capability.EVALUATION_VIEW_ALL)

    def _selected_company_id(self, companies: dict[int, str]) -> int | None:
        user = self.request.user
        if self.limited_to_own_company:
            return user.company_id
        value = self.request.GET.get("empresa", "")
        # Solo se aceptan empresas presentes en los datos que el usuario ya puede ver.
        return int(value) if value.isdigit() and int(value) in companies else None

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        rows = selectors.evaluated_rows(self.request.user)
        companies = {row.company_id: row.company_name for row in rows}
        selected_id = self._selected_company_id(companies)

        context.update(
            totals=distribution(rows),
            company_count=len(companies),
            area_count=len({row.area_id for row in rows}),
            shows_all_companies=not self.limited_to_own_company,
            selected_company_id=selected_id,
            selected_company_name=companies.get(selected_id, ""),
            company_rows=[
                {
                    "id": company_id,
                    "label": name,
                    "risk": distribution([row for row in rows if row.company_id == company_id]),
                }
                for company_id, name in sorted(companies.items(), key=lambda item: item[1].casefold())
            ],
        )
        if selected_id is not None:
            context["area_rows"] = [
                {
                    "label": f"{area.site.name} · {area.name}",
                    "risk": distribution([row for row in rows if row.area_id == area.pk]),
                }
                for area in selectors.company_areas(selected_id)
            ]
        return context
