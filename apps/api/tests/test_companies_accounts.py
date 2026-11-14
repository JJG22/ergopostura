from apps.accounts.models import Role
from apps.companies.models import Company, Site, Worker
from apps.core.tests.factories import (
    PASSWORD,
    make_area,
    make_company,
    make_position,
    make_site,
    make_user,
    make_worker,
    municipality,
)

from .test_api import ApiTestCase


class CompaniesApiTests(ApiTestCase):
    def setUp(self):
        super().setUp()
        self.engineer = make_user(role=Role.ENGINEER, email="ing@ergopostura.test")
        self.company = make_company(name="Café Montaña S.A.S.")
        self.site = make_site(self.company)
        self.position = make_position(make_area(self.site))
        self.worker = make_worker(self.position)

    def as_engineer(self):
        self.login("ing@ergopostura.test")
        return self.csrf()

    def test_list_searches_and_paginates(self):
        make_company(name="Otra empresa")
        self.as_engineer()
        data = self.client.get("/api/v1/companies/?q=café").json()
        self.assertEqual(data["count"], 1)
        self.assertEqual(data["results"][0]["name"], "Café Montaña S.A.S.")
        self.assertEqual(data["results"][0]["site_count"], 1)
        self.assertEqual(data["pages"], 1)

    def test_detail_has_tree_counts_and_permissions(self):
        self.as_engineer()
        data = self.client.get(f"/api/v1/companies/{self.company.pk}/").json()
        self.assertEqual(data["counts"], {"sites": 1, "areas": 1, "positions": 1, "workers": 1})
        position = data["sites"][0]["areas"][0]["positions"][0]
        self.assertEqual(position["key"], f"puesto-{self.position.pk}")
        self.assertEqual(position["workers"][0]["document_number"], self.worker.document_number)
        self.assertTrue(data["permissions"]["manage"])
        self.assertEqual(data["accounts"], [])

    def test_company_user_sees_only_its_company_and_cannot_edit(self):
        own = make_user(role=Role.COMPANY, company=self.company, email="empresa@ergopostura.test")
        other = make_company(name="Ajena")
        self.login(own.email)
        headers = self.csrf()
        data = self.client.get(f"/api/v1/companies/{self.company.pk}/").json()
        self.assertFalse(data["permissions"]["manage"])
        self.assertIsNone(data["accounts"])
        self.assertEqual(self.client.get(f"/api/v1/companies/{other.pk}/").status_code, 404)
        self.assertEqual(self.client.get("/api/v1/companies/").status_code, 403)
        response = self.client.post(f"/api/v1/companies/{self.company.pk}/sites/", {"name": "Nueva"}, format="json", **headers)
        self.assertEqual(response.status_code, 403)

    def test_create_company_validates_nit_with_field_errors(self):
        headers = self.as_engineer()
        place = municipality()
        payload = {"name": "  Nueva   Empresa ", "nit": "123", "department": place.department_id, "municipality": place.pk}
        response = self.client.post("/api/v1/companies/", payload, format="json", **headers)
        self.assertEqual(response.status_code, 400)
        self.assertIn("nit", response.json()["error"]["fields"])

        payload["nit"] = "900.123.456-8"
        response = self.client.post("/api/v1/companies/", payload, format="json", **headers)
        self.assertEqual(response.status_code, 201, response.content)
        created = Company.objects.get(pk=response.json()["id"])
        self.assertEqual((created.name, created.nit, created.is_active), ("Nueva Empresa", "900123456", True))

    def test_update_company_can_deactivate_and_then_blocks_new_structure(self):
        headers = self.as_engineer()
        place = self.company.municipality
        payload = {"name": self.company.name, "nit": self.company.nit, "department": place.department_id,
                   "municipality": place.pk, "is_active": False}
        self.assertEqual(self.client.put(f"/api/v1/companies/{self.company.pk}/", payload, format="json", **headers).status_code, 200)
        response = self.client.post(f"/api/v1/companies/{self.company.pk}/sites/",
                                    {"name": "Bodega", "department": place.department_id, "municipality": place.pk},
                                    format="json", **headers)
        self.assertEqual(response.status_code, 403)
        self.assertIn("inactiva", response.json()["error"]["message"])

    def test_structure_rejects_duplicate_sibling_names(self):
        headers = self.as_engineer()
        place = self.site.municipality
        payload = {"name": self.site.name.upper(), "department": place.department_id, "municipality": place.pk}
        response = self.client.post(f"/api/v1/companies/{self.company.pk}/sites/", payload, format="json", **headers)
        self.assertEqual(response.status_code, 400)
        self.assertIn("name", response.json()["error"]["fields"])
        payload["name"] = "Bodega Pereira"
        response = self.client.post(f"/api/v1/companies/{self.company.pk}/sites/", payload, format="json", **headers)
        self.assertEqual(response.status_code, 201)
        self.assertTrue(Site.objects.filter(company=self.company, name="Bodega Pereira").exists())

    def test_worker_document_is_unique_in_the_company(self):
        headers = self.as_engineer()
        other_position = make_position(make_area(self.site, name="Bodega"), name="Auxiliar")
        payload = {"first_name": "Luis", "last_name": "Pérez", "document_type": "CC",
                   "document_number": self.worker.document_number}
        response = self.client.post(f"/api/v1/positions/{other_position.pk}/workers/", payload, format="json", **headers)
        self.assertEqual(response.status_code, 400)
        self.assertIn("document_number", response.json()["error"]["fields"])
        payload["document_number"] = "1.094.555.111"
        response = self.client.post(f"/api/v1/positions/{other_position.pk}/workers/", payload, format="json", **headers)
        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.json()["key"], other_position.node_key)
        self.assertTrue(Worker.objects.filter(document_number="1094555111").exists())

    def test_cannot_reach_structure_of_out_of_scope_company(self):
        own = make_user(role=Role.COMPANY, company=self.company, email="empresa@ergopostura.test")
        self.login(own.email)
        self.assertEqual(self.client.get("/api/v1/geography/departments/").status_code, 200)
        headers = self.csrf()
        response = self.client.put(f"/api/v1/workers/{self.worker.pk}/", {}, format="json", **headers)
        self.assertEqual(response.status_code, 403)

    def test_municipalities_depend_on_department(self):
        self.as_engineer()
        place = municipality()
        names = [m["name"] for m in self.client.get(f"/api/v1/geography/municipalities/?department={place.department_id}").json()]
        self.assertIn(place.name, names)
        self.assertEqual(self.client.get("/api/v1/geography/municipalities/?department=abc").json(), [])


class AccountsApiTests(ApiTestCase):
    def setUp(self):
        super().setUp()
        self.admin = make_user(role=Role.ADMIN, email="admin@ergopostura.test")
        self.engineer = make_user(role=Role.ENGINEER, email="ing@ergopostura.test")
        self.company = make_company()

    def test_engineer_only_sees_and_creates_company_accounts(self):
        client_account = make_user(role=Role.COMPANY, company=self.company, email="cliente@ergopostura.test")
        self.login(self.engineer.email)
        headers = self.csrf()
        data = self.client.get("/api/v1/accounts/").json()
        self.assertEqual([a["email"] for a in data["results"]], [client_account.email])
        self.assertEqual([r["value"] for r in data["creatable_roles"]], ["empresa"])
        self.assertEqual(data["role_filter"], [])

        payload = {"first_name": "Ana", "last_name": "Ríos", "email": "ana@cafe.test", "role": "ingeniero",
                   "company": self.company.pk, "password1": "Una-Clave-Larga-77", "password2": "Una-Clave-Larga-77"}
        response = self.client.post("/api/v1/accounts/", payload, format="json", **headers)
        self.assertEqual(response.status_code, 400, "el ingeniero no puede crear otro ingeniero")
        self.assertIn("role", response.json()["error"]["fields"])

        payload["role"] = "empresa"
        response = self.client.post("/api/v1/accounts/", payload, format="json", **headers)
        self.assertEqual(response.status_code, 201, response.content)
        self.assertTrue(response.json()["must_change_password"])
        self.assertEqual(self.client.put(f"/api/v1/accounts/{self.admin.pk}/", {}, format="json", **headers).status_code, 404)

    def test_support_cannot_deactivate_itself_or_last_admin(self):
        self.login(self.admin.email)
        headers = self.csrf()
        response = self.client.post(f"/api/v1/accounts/{self.admin.pk}/active/", {"is_active": False}, format="json", **headers)
        self.assertEqual(response.status_code, 409)
        self.assertEqual(response.json()["error"]["code"], "conflict")
        response = self.client.post(f"/api/v1/accounts/{self.engineer.pk}/active/", {"is_active": False}, format="json", **headers)
        self.assertEqual(response.status_code, 200)
        self.assertFalse(response.json()["is_active"])

    def test_temporary_password_forces_change(self):
        account = make_user(role=Role.COMPANY, company=self.company)
        self.login(self.engineer.email)
        headers = self.csrf()
        response = self.client.post(f"/api/v1/accounts/{account.pk}/password/",
                                    {"new_password1": "Temporal-Nueva-55", "new_password2": "Temporal-Nueva-55"},
                                    format="json", **headers)
        self.assertEqual(response.status_code, 200, response.content)
        account.refresh_from_db()
        self.assertTrue(account.must_change_password)
        self.assertTrue(account.check_password("Temporal-Nueva-55"))
        self.assertFalse(account.check_password(PASSWORD))

    def test_update_keeps_role_and_validates_email(self):
        account = make_user(role=Role.COMPANY, company=self.company, email="cliente@ergopostura.test")
        self.login(self.engineer.email)
        headers = self.csrf()
        payload = {"first_name": "Cliente", "last_name": "", "email": "ING@ergopostura.test", "company": self.company.pk}
        response = self.client.put(f"/api/v1/accounts/{account.pk}/", payload, format="json", **headers)
        self.assertEqual(response.status_code, 400)
        self.assertIn("email", response.json()["error"]["fields"])
        payload["email"] = "Nuevo@Cafe.test"
        response = self.client.put(f"/api/v1/accounts/{account.pk}/", payload, format="json", **headers)
        self.assertEqual(response.json()["email"], "nuevo@cafe.test")
        self.assertEqual(response.json()["role"], "empresa")
