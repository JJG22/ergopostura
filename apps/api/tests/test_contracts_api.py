from datetime import timedelta

from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import override_settings
from django.utils import timezone

from apps.accounts.models import Role
from apps.contracts.models import Contract
from apps.contracts.tests.test_contracts import fake_client
from apps.core.tests.factories import at, make_company, make_contract, make_site, make_user, make_visit, sample_pdf

from .test_api import ApiTestCase


def upload(content=None):
    return SimpleUploadedFile("contrato.pdf", content if content is not None else sample_pdf(), "application/pdf")


class ContractsApiTests(ApiTestCase):
    def setUp(self):
        super().setUp()
        self.engineer = make_user(role=Role.ENGINEER, email="ing@ergopostura.test")
        self.company = make_company(name="Café Montaña S.A.S.", nit="900123456")
        self.today = timezone.localdate()

    def as_engineer(self):
        self.login(self.engineer.email)
        return self.csrf()

    def payload(self, **changes):
        data = {
            "company": self.company.pk, "code": "CPS-1", "kind": "prestacion_servicios",
            "start_date": self.today.isoformat(), "end_date": (self.today + timedelta(days=364)).isoformat(),
            "service": "Evaluación ergonómica.", "responsible_name": "Marta Salazar", "document": upload(),
        }
        data.update(changes)
        return data

    def test_create_with_pdf_and_reject_overlap(self):
        headers = self.as_engineer()
        response = self.client.post("/api/v1/contracts/", self.payload(), format="multipart", **headers)
        self.assertEqual(response.status_code, 201, response.content)
        contract = Contract.objects.get(pk=response.json()["id"])
        self.assertEqual(contract.created_by, self.engineer)

        response = self.client.post("/api/v1/contracts/", self.payload(code="CPS-2"), format="multipart", **headers)
        self.assertEqual(response.status_code, 400)
        self.assertIn("Se cruza con el contrato CPS-1", response.json()["error"]["fields"]["start_date"][0])

    def test_document_must_be_a_real_pdf(self):
        headers = self.as_engineer()
        response = self.client.post("/api/v1/contracts/", self.payload(document=upload(b"hola")), format="multipart", **headers)
        self.assertEqual(response.status_code, 400)
        self.assertIn("document", response.json()["error"]["fields"])

    def test_update_keeps_document_when_none_is_sent(self):
        contract = make_contract(self.company, start=self.today)
        headers = self.as_engineer()
        data = self.payload(code="NUEVO")
        del data["document"], data["company"]
        response = self.client.put(f"/api/v1/contracts/{contract.pk}/", data, format="multipart", **headers)
        self.assertEqual(response.status_code, 200, response.content)
        contract.refresh_from_db()
        self.assertEqual(contract.code, "NUEVO")
        self.assertTrue(bytes(contract.file_data).startswith(b"%PDF-"))

    def test_list_has_status_tabs_and_filters(self):
        make_contract(self.company, start=self.today - timedelta(days=400), end=self.today - timedelta(days=40))
        make_contract(self.company, start=self.today - timedelta(days=10))
        self.as_engineer()
        data = self.client.get("/api/v1/contracts/").json()
        totals = {s["value"]: s["total"] for s in data["statuses"]}
        self.assertEqual((totals["vencido"], totals["vigente"]), (1, 1))
        expired = self.client.get("/api/v1/contracts/?status=vencido").json()
        self.assertEqual([c["status"] for c in expired["results"]], ["vencido"])

    def test_company_sees_own_contract_without_ai_or_management(self):
        own = make_contract(self.company)
        other = make_contract(make_company(name="Otra"))
        user = make_user(role=Role.COMPANY, company=self.company)
        self.login(user.email)
        data = self.client.get(f"/api/v1/contracts/{own.pk}/").json()
        self.assertFalse(data["can_manage"])
        self.assertNotIn("ai_summary", data)
        self.assertNotIn("history", data)
        self.assertEqual(self.client.get(f"/api/v1/contracts/{other.pk}/").status_code, 404)
        self.assertEqual(self.client.get("/api/v1/contracts/").status_code, 403)
        pdf = self.client.get(f"/api/v1/contracts/{own.pk}/file/")
        self.assertEqual(pdf.status_code, 200)
        self.assertEqual(pdf["Content-Type"], "application/pdf")
        self.assertIn("no-store", pdf["Cache-Control"])
        self.assertEqual(self.client.get(f"/api/v1/contracts/{other.pk}/file/").status_code, 404)

    def test_delete_is_blocked_by_scheduled_visits(self):
        contract = make_contract(self.company)
        site = make_site(self.company)
        make_visit(site=site, scheduled_at=at(self.today + timedelta(days=7), 9))
        headers = self.as_engineer()
        response = self.client.delete(f"/api/v1/contracts/{contract.pk}/", **headers)
        self.assertEqual(response.status_code, 409)
        self.assertEqual(response.json()["error"]["code"], "conflict")
        free = make_contract(make_company(name="Sin visitas"))
        self.assertEqual(self.client.delete(f"/api/v1/contracts/{free.pk}/", **headers).status_code, 204)

    @override_settings(ANTHROPIC_API_KEY="clave-de-prueba")
    def test_read_proposes_fields_and_finds_company(self):
        headers = self.as_engineer()
        patch, create = fake_client()
        with patch:
            response = self.client.post("/api/v1/contracts/read/", {"document": upload()}, format="multipart", **headers)
        self.assertEqual(response.status_code, 200, response.content)
        data = response.json()
        self.assertEqual(data["fields"]["company"], self.company.pk)
        self.assertEqual(data["fields"]["start_date"], "2026-01-01")
        self.assertTrue(data["company_found"])
        create.assert_called_once()

    def test_read_without_key_is_unavailable(self):
        headers = self.as_engineer()
        with override_settings(ANTHROPIC_API_KEY=""):
            response = self.client.post("/api/v1/contracts/read/", {"document": upload()}, format="multipart", **headers)
        self.assertEqual(response.status_code, 503)
        self.assertEqual(response.json()["error"]["code"], "ai_unavailable")
