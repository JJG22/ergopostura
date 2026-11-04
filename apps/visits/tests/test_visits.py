from datetime import timedelta
from unittest import mock

from django.db import IntegrityError, transaction
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from apps.accounts.models import Role
from apps.core.tests.factories import make_area, make_company, make_position, make_site, make_user
from apps.visits.forms import VisitForm
from apps.visits.models import Visit

HTMX = {"HTTP_HX_REQUEST": "true"}


def future(days=5):
    return timezone.localtime(timezone.now() + timedelta(days=days)).replace(
        hour=9, minute=0, second=0, microsecond=0
    )


def make_visit(position=None, when=None, **fields):
    return Visit.objects.create(position=position or make_position(), scheduled_at=when or future(), **fields)


class VisitTestCase(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.company = make_company(name="Mi empresa")
        cls.site = make_site(cls.company)
        cls.area = make_area(cls.site)
        cls.position = make_position(cls.area)
        cls.foreign_position = make_position(make_area(make_site(make_company(name="Ajena")), name="Ajena"))

    def payload(self, **changes):
        when = future()
        data = {
            "date": when.strftime("%Y-%m-%d"),
            "time": "09:00",
            "company": self.company.pk,
            "site": self.site.pk,
            "area": self.area.pk,
            "position": self.position.pk,
            "contact_name": "Marta Salazar",
        }
        return {**data, **changes}


class VisitModelTests(VisitTestCase):
    def test_company_and_site_come_from_the_hierarchy(self):
        visit = make_visit(self.position)
        self.assertEqual((visit.company, visit.site, visit.area), (self.company, self.site, self.area))

    def test_duplicate_is_rejected_by_database(self):
        when = future()
        make_visit(self.position, when)
        with self.assertRaises(IntegrityError), transaction.atomic():
            make_visit(self.position, when)

    def test_position_with_visits_cannot_be_deleted(self):
        make_visit(self.position)
        from django.db.models import ProtectedError

        with self.assertRaises(ProtectedError):
            self.position.delete()


class VisitFormTests(VisitTestCase):
    def setUp(self):
        self.admin = make_user(role=Role.ADMIN)
        self.company_user = make_user(role=Role.COMPANY, company=self.company)

    def test_valid_visit_saves_local_time_and_author(self):
        form = VisitForm(data=self.payload(), user=self.admin)
        self.assertTrue(form.is_valid(), form.errors)
        visit = form.save()
        self.assertEqual(timezone.localtime(visit.scheduled_at).hour, 9)
        self.assertEqual(visit.created_by, self.admin)
        self.assertEqual(visit.position, self.position)

    def test_past_date_is_rejected(self):
        yesterday = (timezone.localdate() - timedelta(days=1)).strftime("%Y-%m-%d")
        form = VisitForm(data=self.payload(date=yesterday), user=self.admin)
        self.assertIn("La fecha y la hora de la visita ya pasaron.", form.errors["date"])

    def test_duplicate_shows_a_clear_message(self):
        make_visit(self.position, future())
        form = VisitForm(data=self.payload(), user=self.admin)
        self.assertIn("Ya hay una visita registrada", form.non_field_errors()[0])

    def test_same_time_in_other_position_is_allowed(self):
        make_visit(make_position(self.area, name="Otro puesto"), future())
        self.assertTrue(VisitForm(data=self.payload(), user=self.admin).is_valid())

    def test_position_of_another_area_is_rejected(self):
        other = make_position(make_area(self.site, name="Otra área"), name="Otro")
        form = VisitForm(data=self.payload(position=other.pk), user=self.admin)
        self.assertIn("position", form.errors)

    def test_area_of_another_site_is_rejected(self):
        other = make_area(make_site(self.company, name="Otra sede"), name="Otra")
        form = VisitForm(data=self.payload(area=other.pk), user=self.admin)
        self.assertIn("area", form.errors)

    def test_inactive_company_is_not_offered(self):
        inactive = make_company(name="Inactiva", is_active=False)
        form = VisitForm(data=self.payload(company=inactive.pk), user=self.admin)
        self.assertIn("company", form.errors)

    def test_company_user_has_no_company_field_and_stays_in_its_company(self):
        form = VisitForm(data=self.payload(), user=self.company_user)
        self.assertNotIn("company", form.fields)
        self.assertTrue(form.is_valid(), form.errors)
        self.assertEqual(form.save().company, self.company)

    def test_company_user_cannot_send_a_foreign_position(self):
        area = self.foreign_position.area
        form = VisitForm(
            data=self.payload(site=area.site.pk, area=area.pk, position=self.foreign_position.pk),
            user=self.company_user,
        )
        self.assertFalse(form.is_valid())
        self.assertIn("site", form.errors)
        self.assertIn("position", form.errors)

    def test_garbage_ids_do_not_crash(self):
        form = VisitForm(data=self.payload(company="x", site="'; DROP", area="", position="None"), user=self.admin)
        self.assertFalse(form.is_valid())

    def test_past_visit_can_be_corrected_without_changing_its_date(self):
        past = timezone.localtime(timezone.now() - timedelta(days=3)).replace(second=0, microsecond=0)
        visit = make_visit(self.position, past)
        form = VisitForm(
            data=self.payload(
                date=past.strftime("%Y-%m-%d"), time=past.strftime("%H:%M"), contact_name="Otro contacto"
            ),
            instance=visit,
            user=self.admin,
        )
        self.assertTrue(form.is_valid(), form.errors)
        self.assertEqual(form.save().contact_name, "Otro contacto")

    def test_editing_loads_the_whole_chain(self):
        form = VisitForm(instance=make_visit(self.position), user=self.admin)
        self.assertEqual(form.initial["company"], self.company.pk)
        self.assertEqual(form.initial["site"], self.site.pk)
        self.assertEqual(form.initial["area"], self.area.pk)
        self.assertIn(self.position, form.fields["position"].queryset)


class VisitAccessTests(VisitTestCase):
    def setUp(self):
        self.visit = make_visit(self.position)
        self.foreign_visit = make_visit(self.foreign_position)

    def manage_urls(self):
        return [
            reverse("visits:create"),
            reverse("visits:cascade"),
            reverse("visits:update", args=[self.visit.pk]),
        ]

    def test_anonymous_is_sent_to_login(self):
        for url in [reverse("visits:list"), *self.manage_urls()]:
            self.assertIn("/ingresar/", self.client.get(url)["Location"])

    def test_roles_that_read_all(self):
        for role in (Role.ADMIN, Role.ENGINEER, Role.EVALUATOR):
            self.client.force_login(make_user(role=role))
            visits = self.client.get(reverse("visits:list")).context["visits"]
            self.assertEqual(len(visits), 2, role)

    def test_roles_without_access_get_403(self):
        for role in (Role.RESULTS, Role.TASKS):
            self.client.force_login(make_user(role=role))
            self.assertEqual(self.client.get(reverse("visits:list")).status_code, 403, role)

    def test_only_admin_and_company_can_manage(self):
        for role in (Role.ENGINEER, Role.EVALUATOR, Role.RESULTS, Role.TASKS):
            self.client.force_login(make_user(role=role))
            for url in self.manage_urls():
                self.assertEqual(self.client.get(url).status_code, 403, f"{role} {url}")
        for user in (make_user(role=Role.ADMIN), make_user(role=Role.COMPANY, company=self.company)):
            self.client.force_login(user)
            for url in self.manage_urls():
                self.assertEqual(self.client.get(url).status_code, 200, f"{user.role} {url}")

    def test_read_only_roles_do_not_see_actions(self):
        self.client.force_login(make_user(role=Role.EVALUATOR))
        response = self.client.get(reverse("visits:list"))
        self.assertNotContains(response, "Registrar visita")
        self.assertNotContains(response, "Editar")

    def test_company_user_only_sees_and_edits_its_own_visits(self):
        self.client.force_login(make_user(role=Role.COMPANY, company=self.company))
        visits = self.client.get(reverse("visits:list")).context["visits"]
        self.assertEqual(list(visits), [self.visit])
        response = self.client.get(reverse("visits:update", args=[self.foreign_visit.pk]))
        self.assertEqual(response.status_code, 404)

    def test_forbidden_post_does_not_write(self):
        self.client.force_login(make_user(role=Role.ENGINEER))
        before = Visit.objects.count()
        self.assertEqual(self.client.post(reverse("visits:create"), self.payload()).status_code, 403)
        self.assertEqual(Visit.objects.count(), before)


class VisitViewTests(VisitTestCase):
    def setUp(self):
        self.user = make_user(role=Role.ADMIN)
        self.client.force_login(self.user)

    def test_create_from_modal_redirects_whole_page(self):
        response = self.client.post(reverse("visits:create"), self.payload(), **HTMX)
        self.assertEqual(response.status_code, 204)
        self.assertEqual(response["HX-Redirect"], reverse("visits:list"))
        self.assertEqual(Visit.objects.get().created_by, self.user)

    def test_errors_stay_in_the_modal(self):
        response = self.client.post(reverse("visits:create"), self.payload(position=""), **HTMX)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'class="overlay"')

    def test_concurrent_duplicate_becomes_form_error(self):
        with mock.patch.object(VisitForm, "save", side_effect=IntegrityError):
            response = self.client.post(reverse("visits:create"), self.payload())
        self.assertContains(response, "Ya hay una visita registrada")

    def test_cascade_offers_only_children_of_the_selection(self):
        other_site = make_site(make_company(name="Otra"), name="Sede de otra")
        response = self.client.get(reverse("visits:cascade"), {"company": self.company.pk}, **HTMX)
        self.assertContains(response, self.site.name)
        self.assertNotContains(response, other_site.name)
        self.assertContains(response, "Selecciona primero una sede")

    def test_cascade_keeps_what_was_typed(self):
        response = self.client.get(
            reverse("visits:cascade"), {"company": self.company.pk, "contact_name": "Marta", "time": "10:30"}, **HTMX
        )
        self.assertContains(response, 'value="Marta"')
        self.assertContains(response, 'value="10:30"')

    def test_changing_company_clears_stale_children(self):
        other = make_company(name="Otra")
        response = self.client.get(
            reverse("visits:cascade"),
            {"company": other.pk, "site": self.site.pk, "area": self.area.pk, "position": self.position.pk},
            **HTMX,
        )
        self.assertNotContains(response, self.site.name)
        self.assertNotContains(response, self.area.name)

    def test_list_separates_upcoming_and_past(self):
        upcoming = make_visit(self.position, future())
        past = make_visit(self.position, timezone.now() - timedelta(days=2))
        url = reverse("visits:list")
        self.assertEqual(list(self.client.get(url).context["visits"]), [upcoming])
        self.assertEqual(list(self.client.get(url, {"ver": "pasadas"}).context["visits"]), [past])

    def test_list_shows_time_in_colombia(self):
        make_visit(self.position, future())
        self.assertContains(self.client.get(reverse("visits:list")), "9:00")

    def test_list_query_count_does_not_grow_with_visits(self):
        for days in range(1, 6):
            make_visit(self.position, future(days))
        # sesion, usuario, conteo de la paginacion y visitas con su jerarquia
        with self.assertNumQueries(4):
            self.client.get(reverse("visits:list"))
