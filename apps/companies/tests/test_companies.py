from unittest import mock

from django.db import IntegrityError, transaction
from django.db.models import ProtectedError
from django.test import TestCase
from django.urls import reverse

from apps.accounts.models import Role
from apps.companies.forms import CompanyForm
from apps.companies.models import Area, Company, Position, Site
from apps.core.tests.factories import make_area, make_company, make_position, make_site, make_user

VALID_COMPANY = {
    "name": "Café Montaña S.A.S.",
    "nit": "900.123.456-8",
    "city": "Armenia",
    "department": "Quindío",
}
HTMX = {"HTTP_HX_REQUEST": "true"}


class DatabaseIntegrityTests(TestCase):
    def test_duplicate_nit_is_rejected_by_database(self):
        make_company(nit="900123456")
        with self.assertRaises(IntegrityError), transaction.atomic():
            make_company(nit="900123456")

    def test_malformed_nit_is_rejected_by_database(self):
        with self.assertRaises(IntegrityError), transaction.atomic():
            make_company(nit="90012345A")

    def test_child_names_are_unique_per_parent_ignoring_case(self):
        site = make_site()
        with self.assertRaises(IntegrityError), transaction.atomic():
            make_site(site.company, name=site.name.upper())
        area = make_area(site)
        with self.assertRaises(IntegrityError), transaction.atomic():
            make_area(site, name=area.name.upper())
        position = make_position(area)
        with self.assertRaises(IntegrityError), transaction.atomic():
            make_position(area, name=position.name.upper())

    def test_same_name_is_allowed_under_different_parents(self):
        make_site(make_company(), name="Principal")
        make_site(make_company(), name="Principal")
        self.assertEqual(Site.objects.filter(name="Principal").count(), 2)

    def test_parents_with_children_cannot_be_deleted(self):
        position = make_position()
        for parent in (position.area, position.area.site, position.company):
            with self.assertRaises(ProtectedError):
                parent.delete()

    def test_position_reaches_its_company_through_the_hierarchy(self):
        company = make_company()
        position = make_position(make_area(make_site(company)))
        self.assertEqual(position.company, company)


class CompanyFormTests(TestCase):
    def test_duplicate_nit_message(self):
        make_company(nit="900123456")
        form = CompanyForm(data=VALID_COMPANY)
        self.assertFalse(form.is_valid())
        self.assertIn("Ya existe una empresa con este NIT.", form.errors["nit"])

    def test_same_nit_written_differently_is_still_a_duplicate(self):
        make_company(nit="900123456")
        for raw in ("900123456", "900123456-8", "900 123 456"):
            form = CompanyForm(data={**VALID_COMPANY, "nit": raw})
            self.assertFalse(form.is_valid(), raw)
            self.assertIn("Ya existe una empresa con este NIT.", form.errors["nit"])

    def test_nit_is_saved_normalized(self):
        form = CompanyForm(data=VALID_COMPANY)
        self.assertTrue(form.is_valid(), form.errors)
        self.assertEqual(form.save().nit, "900123456")

    def test_missing_nit(self):
        form = CompanyForm(data={**VALID_COMPANY, "nit": "  "})
        self.assertIn("El NIT es obligatorio.", form.errors["nit"])

    def test_editing_a_company_keeps_its_own_nit(self):
        company = make_company(nit="900123456")
        form = CompanyForm(data={**VALID_COMPANY, "is_active": "on"}, instance=company)
        self.assertTrue(form.is_valid(), form.errors)

    def test_editing_cannot_take_the_nit_of_another_company(self):
        make_company(nit="900123456")
        other = make_company(nit="901234567")
        form = CompanyForm(data=VALID_COMPANY, instance=other)
        self.assertIn("Ya existe una empresa con este NIT.", form.errors["nit"])

    def test_new_company_has_no_active_field_and_starts_active(self):
        form = CompanyForm(data=VALID_COMPANY)
        self.assertNotIn("is_active", form.fields)
        self.assertTrue(form.save().is_active)

    def test_spaces_in_name_are_normalized(self):
        form = CompanyForm(data={**VALID_COMPANY, "name": "  Café   Montaña  "})
        self.assertEqual(form.save().name, "Café Montaña")


class AccessControlTests(TestCase):
    """Matriz de quien puede hacer que, recorriendo todos los roles."""

    @classmethod
    def setUpTestData(cls):
        cls.position = make_position()
        cls.area = cls.position.area
        cls.site = cls.area.site
        cls.company = cls.site.company
        cls.other_company = make_company(name="Otra empresa")

    def manage_urls(self):
        return [
            reverse("companies:create"),
            reverse("companies:update", args=[self.company.pk]),
            reverse("companies:site_create", args=[self.company.pk]),
            reverse("companies:site_update", args=[self.site.pk]),
            reverse("companies:area_create", args=[self.site.pk]),
            reverse("companies:area_update", args=[self.area.pk]),
            reverse("companies:position_create", args=[self.area.pk]),
            reverse("companies:position_update", args=[self.position.pk]),
        ]

    def read_urls(self):
        return [reverse("companies:list"), reverse("companies:detail", args=[self.company.pk])]

    def test_anonymous_is_sent_to_login(self):
        for url in [*self.read_urls(), *self.manage_urls(), reverse("dashboard:home")]:
            response = self.client.get(url)
            self.assertEqual(response.status_code, 302, url)
            self.assertIn("/ingresar/", response["Location"])

    def test_admin_and_engineer_can_read_and_manage(self):
        for role in (Role.ADMIN, Role.ENGINEER):
            self.client.force_login(make_user(role=role))
            for url in [*self.read_urls(), *self.manage_urls()]:
                self.assertEqual(self.client.get(url).status_code, 200, f"{role} {url}")

    def test_roles_without_permission_get_403_everywhere(self):
        for role in (Role.EVALUATOR, Role.RESULTS, Role.TASKS):
            self.client.force_login(make_user(role=role))
            for url in [*self.read_urls(), *self.manage_urls()]:
                self.assertEqual(self.client.get(url).status_code, 403, f"{role} {url}")

    def test_forbidden_post_does_not_write(self):
        self.client.force_login(make_user(role=Role.EVALUATOR))
        response = self.client.post(reverse("companies:create"), {**VALID_COMPANY, "nit": "901234567"})
        self.assertEqual(response.status_code, 403)
        self.assertFalse(Company.objects.filter(nit="901234567").exists())

    def test_company_user_sees_own_company_read_only(self):
        self.client.force_login(make_user(role=Role.COMPANY, company=self.company))
        response = self.client.get(reverse("companies:detail", args=[self.company.pk]))
        self.assertEqual(response.status_code, 200)
        self.assertNotContains(response, "Editar")
        self.assertNotContains(response, "Agregar sede")
        self.assertNotContains(response, "Volver a empresas")
        for url in self.manage_urls():
            self.assertEqual(self.client.get(url).status_code, 403, url)

    def test_company_user_cannot_see_list_or_other_company(self):
        self.client.force_login(make_user(role=Role.COMPANY, company=self.company))
        self.assertEqual(self.client.get(reverse("companies:list")).status_code, 403)
        response = self.client.get(reverse("companies:detail", args=[self.other_company.pk]))
        self.assertEqual(response.status_code, 404)

    def test_navigation_only_shows_what_the_role_can_open(self):
        self.client.force_login(make_user(role=Role.EVALUATOR))
        response = self.client.get(reverse("dashboard:home"))
        labels = [item["label"] for item in response.context["nav_items"]]
        self.assertEqual(labels, ["Panel principal", "Visitas", "Evaluaciones"])

        self.client.force_login(make_user(role=Role.TASKS))
        response = self.client.get(reverse("dashboard:home"))
        labels = [item["label"] for item in response.context["nav_items"]]
        self.assertEqual(labels, ["Panel principal"])

        self.client.force_login(make_user(role=Role.ADMIN))
        response = self.client.get(reverse("dashboard:home"))
        labels = [item["label"] for item in response.context["nav_items"]]
        self.assertEqual(labels, ["Panel principal", "Empresas", "Visitas", "Evaluaciones", "Usuarios"])

    def test_session_expired_in_modal_redirects_whole_page(self):
        response = self.client.get(reverse("companies:create"), **HTMX)
        self.assertEqual(response.status_code, 204)
        self.assertIn("/ingresar/", response["HX-Redirect"])


class CompanyViewTests(TestCase):
    def setUp(self):
        self.client.force_login(make_user(role=Role.ENGINEER))

    def test_create_redirects_to_detail(self):
        response = self.client.post(reverse("companies:create"), VALID_COMPANY)
        company = Company.objects.get(nit="900123456")
        self.assertRedirects(response, reverse("companies:detail", args=[company.pk]))

    def test_duplicate_nit_shows_error_and_creates_nothing(self):
        make_company(nit="900123456")
        response = self.client.post(reverse("companies:create"), VALID_COMPANY)
        self.assertContains(response, "Ya existe una empresa con este NIT.")
        self.assertEqual(Company.objects.filter(nit="900123456").count(), 1)

    def test_htmx_returns_modal_and_keeps_errors_inside_it(self):
        url = reverse("companies:create")
        modal = self.client.get(url, **HTMX)
        self.assertContains(modal, 'class="overlay"')
        self.assertNotContains(modal, "<html")

        make_company(nit="900123456")
        invalid = self.client.post(url, VALID_COMPANY, **HTMX)
        self.assertEqual(invalid.status_code, 200)
        self.assertContains(invalid, 'class="overlay"')
        self.assertContains(invalid, "Ya existe una empresa con este NIT.")

    def test_htmx_success_redirects_whole_page(self):
        response = self.client.post(
            reverse("companies:create"), {**VALID_COMPANY, "nit": "901234567"}, **HTMX
        )
        self.assertEqual(response.status_code, 204)
        company = Company.objects.get(nit="901234567")
        self.assertEqual(response["HX-Redirect"], reverse("companies:detail", args=[company.pk]))

    def test_concurrent_duplicate_becomes_form_error_not_server_error(self):
        # Simula que otra persona guarda el mismo NIT entre la validacion y el guardado.
        with mock.patch.object(CompanyForm, "save", side_effect=IntegrityError):
            response = self.client.post(reverse("companies:create"), VALID_COMPANY)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Ya existe una empresa con este NIT.")

    def test_search_by_name_and_by_any_nit_format(self):
        make_company(name="Café Montaña", nit="900123456")
        make_company(name="Muebles del Eje", nit="801234567")
        url = reverse("companies:list")
        for query in ("café", "900123456", "900.123.456-8"):
            names = [c.name for c in self.client.get(url, {"q": query}).context["companies"]]
            self.assertEqual(names, ["Café Montaña"], query)

    def test_list_counts_sites(self):
        company = make_company()
        make_site(company, name="A")
        make_site(company, name="B")
        listed = self.client.get(reverse("companies:list")).context["companies"][0]
        self.assertEqual(listed.site_count, 2)

    def test_list_is_sorted_by_name(self):
        make_company(name="Zeta")
        make_company(name="Alfa")
        names = [c.name for c in self.client.get(reverse("companies:list")).context["companies"]]
        self.assertEqual(names, ["Alfa", "Zeta"])

    def test_pagination_keeps_search(self):
        for index in range(16):
            make_company(name=f"Empresa {index}")
        response = self.client.get(reverse("companies:list"), {"q": "Empresa"})
        self.assertContains(response, "page=2&amp;q=Empresa")

    def test_user_content_is_escaped(self):
        make_company(name="<script>alert(1)</script>")
        response = self.client.get(reverse("companies:list"))
        self.assertNotContains(response, "<script>alert(1)</script>")
        self.assertContains(response, "&lt;script&gt;")


class StructureViewTests(TestCase):
    def setUp(self):
        self.client.force_login(make_user(role=Role.ENGINEER))
        self.company = make_company()

    def site_data(self, name="Planta Armenia"):
        return {"name": name, "city": "Armenia", "department": "Quindío"}

    def test_full_hierarchy_can_be_created(self):
        self.client.post(reverse("companies:site_create", args=[self.company.pk]), self.site_data())
        site = Site.objects.get(company=self.company)
        self.client.post(reverse("companies:area_create", args=[site.pk]), {"name": "Empaque"})
        area = Area.objects.get(site=site)
        self.client.post(reverse("companies:position_create", args=[area.pk]), {"name": "Operario"})
        self.assertEqual(Position.objects.get(area=area).company, self.company)

    def test_duplicate_child_shows_friendly_error(self):
        make_site(self.company, name="Planta Armenia")
        response = self.client.post(
            reverse("companies:site_create", args=[self.company.pk]), self.site_data("  planta   ARMENIA ")
        )
        self.assertContains(response, "Esta empresa ya tiene una sede con ese nombre.")
        self.assertEqual(self.company.sites.count(), 1)

    def test_editing_a_child_keeps_its_own_name(self):
        site = make_site(self.company)
        response = self.client.post(reverse("companies:site_update", args=[site.pk]), self.site_data(site.name))
        self.assertEqual(response.status_code, 302)

    def test_parent_cannot_be_changed_by_tampering_the_form(self):
        site = make_site(self.company)
        other = make_company(name="Otra")
        self.client.post(
            reverse("companies:site_update", args=[site.pk]), {**self.site_data(site.name), "company": other.pk}
        )
        site.refresh_from_db()
        self.assertEqual(site.company, self.company)

    def test_inactive_company_does_not_accept_new_structure(self):
        company = make_company(is_active=False)
        url = reverse("companies:site_create", args=[company.pk])
        self.assertEqual(self.client.get(url).status_code, 403)
        self.assertEqual(self.client.post(url, self.site_data()).status_code, 403)
        self.assertEqual(company.sites.count(), 0)

    def test_create_under_unknown_parent_is_404(self):
        self.assertEqual(self.client.get(reverse("companies:area_create", args=[99999])).status_code, 404)

    def test_detail_shows_selected_node(self):
        position = make_position(make_area(make_site(self.company)))
        url = reverse("companies:detail", args=[self.company.pk])
        response = self.client.get(url, {"nodo": position.node_key})
        self.assertEqual(response.context["selection"].name, position.name)

    def test_node_of_another_company_is_not_shown(self):
        foreign = make_site(make_company(name="Ajena"), name="Sede ajena")
        url = reverse("companies:detail", args=[self.company.pk])
        response = self.client.get(url, {"nodo": foreign.node_key})
        self.assertEqual(response.context["selection"].kind, "EMPRESA")
        self.assertNotContains(response, "Sede ajena")

    def test_garbage_node_falls_back_to_company(self):
        url = reverse("companies:detail", args=[self.company.pk])
        self.assertEqual(self.client.get(url, {"nodo": "'; DROP TABLE"}).status_code, 200)

    def test_detail_query_count_does_not_grow_with_structure(self):
        for site_index in range(3):
            site = make_site(self.company, name=f"Sede {site_index}")
            for area_index in range(3):
                make_position(make_area(site, name=f"Área {area_index}"))
        url = reverse("companies:detail", args=[self.company.pk])
        # sesion, usuario, empresa y un prefetch por cada nivel de la jerarquia
        with self.assertNumQueries(6):
            self.client.get(url)
