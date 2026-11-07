import base64
import json
from datetime import date, timedelta
from types import SimpleNamespace
from unittest import mock

import anthropic
import httpx2
from django.core.files.uploadedfile import SimpleUploadedFile
from django.db import IntegrityError, transaction
from django.test import SimpleTestCase, TestCase, override_settings
from django.urls import reverse
from django.utils import timezone

from apps.accounts.models import Role
from apps.contracts import reader, services
from apps.contracts.forms import ContractForm
from apps.contracts.models import Contract, ContractReading, ContractStatus, duration_label
from apps.core.tests.factories import at, make_company, make_contract, make_site, make_user, make_visit, sample_pdf
from apps.visits.models import Visit

TODAY = date(2026, 11, 6)


def pdf_upload(content=None, name="contrato.pdf"):
    return SimpleUploadedFile(name, content if content is not None else sample_pdf(), "application/pdf")


def reading_json(**changes):
    data = {
        "summary": "Café Montaña contrata la evaluación ergonómica de sus puestos durante un año.",
        "contract_type": "prestacion_servicios",
        "contract_type_text": "Contrato de prestación de servicios profesionales",
        "contract_code": "CPS-2026-001",
        "service": "Evaluación ergonómica con RULA.",
        "client_name": "Café Montaña S.A.S.",
        "client_nit": "900.123.456-8",
        "provider_name": "Andrés Ríos",
        "responsible_name": "Marta Salazar",
        "responsible_role": "Jefe de SST",
        "responsible_email": "marta@cafe.com",
        "responsible_phone": None,
        "start_date": "2026-01-01",
        "end_date": "2026-12-31",
        "duration_text": "Doce meses",
        "value_cop": 12000000,
        "payment_terms": "Cuotas mensuales",
        "provider_obligations": ["Visitar la planta", "Entregar informes"],
        "client_obligations": ["Dar acceso a los puestos"],
        "termination": "Aviso de treinta días",
        "data_protection": "Ley 1581 de 2012",
        "alerts": [],
    }
    data.update(changes)
    return json.dumps(data)


def fake_response(text=None, stop_reason="end_turn"):
    return SimpleNamespace(
        stop_reason=stop_reason,
        content=[SimpleNamespace(type="text", text=text if text is not None else reading_json())],
        model="claude-opus-5-5",
    )


def fake_client(response=None, error=None):
    create = mock.Mock(return_value=response or fake_response(), side_effect=error)
    client = SimpleNamespace(beta=SimpleNamespace(messages=SimpleNamespace(create=create)))
    return mock.patch.object(reader.anthropic, "Anthropic", return_value=client), create


def api_error(cls, status):
    request = httpx2.Request("POST", "https://api.anthropic.com/v1/messages")
    return cls("error", response=httpx2.Response(status, request=request), body=None)


class DurationAndStatusTests(SimpleTestCase):
    def test_duration_reads_like_a_contract(self):
        self.assertEqual(duration_label(date(2026, 1, 1), date(2026, 12, 31)), "12 meses")
        self.assertEqual(duration_label(date(2026, 1, 15), date(2026, 3, 14)), "2 meses")
        self.assertEqual(duration_label(date(2026, 1, 15), date(2026, 3, 20)), "2 meses y 6 días")
        self.assertEqual(duration_label(date(2026, 2, 1), date(2026, 2, 28)), "1 mes")
        self.assertEqual(duration_label(date(2026, 3, 1), date(2026, 3, 1)), "1 día")

    def test_status_depends_on_the_day(self):
        contract = Contract(start_date=date(2026, 1, 1), end_date=date(2026, 12, 31))
        self.assertEqual(contract.status_on(date(2025, 12, 31)), ContractStatus.UPCOMING)
        self.assertEqual(contract.status_on(date(2026, 6, 1)), ContractStatus.ACTIVE)
        self.assertEqual(contract.status_on(date(2026, 12, 10)), ContractStatus.EXPIRING)
        self.assertEqual(contract.status_on(date(2027, 1, 1)), ContractStatus.EXPIRED)


class ContractRuleTests(TestCase):
    def setUp(self):
        self.engineer = make_user(role=Role.ENGINEER)
        self.company = make_company()

    def form(self, instance=None, files=None, **changes):
        data = {
            "company": self.company.pk,
            "kind": Contract.Kind.SERVICES,
            "service": "Evaluación ergonómica",
            "start_date": "2026-01-01",
            "end_date": "2026-12-31",
            "responsible_name": "Marta Salazar",
            **changes,
        }
        if files is None:
            files = {} if instance else {"document": pdf_upload()}
        return ContractForm(data=data, files=files, actor=self.engineer, instance=instance)

    def test_saves_the_pdf_in_the_database(self):
        form = self.form()
        self.assertTrue(form.is_valid(), form.errors)
        contract = form.save()
        self.assertTrue(bytes(contract.file_data).startswith(b"%PDF-"))
        self.assertEqual(len(contract.file_sha256), 64)
        self.assertEqual(contract.created_by, self.engineer)

    def test_only_real_pdfs_are_accepted(self):
        form = self.form(files={"document": pdf_upload(b"MZ ejecutable", name="contrato.pdf")})
        self.assertIn("formato PDF", str(form.errors["document"]))
        big = pdf_upload()
        big.size = 11 * 1024 * 1024
        self.assertIn("10 MB", str(self.form(files={"document": big}).errors["document"]))

    def test_document_is_required_when_creating(self):
        self.assertIn("document", self.form(files={}).errors)

    def test_dates_must_be_in_order(self):
        self.assertIn("end_date", self.form(end_date="2025-12-31").errors)
        with self.assertRaises(IntegrityError), transaction.atomic():
            make_contract(self.company, start=date(2026, 5, 1), end=date(2026, 4, 1))

    def test_one_contract_at_a_time_per_company(self):
        make_contract(self.company, start=date(2026, 1, 1), end=date(2026, 6, 30))
        form = self.form(start_date="2026-06-01", end_date="2027-05-31")
        self.assertFalse(form.is_valid())
        self.assertIn("01/07/2026", str(form.errors["start_date"]))
        # Una renovacion que empieza al dia siguiente si se acepta.
        self.assertTrue(self.form(start_date="2026-07-01", end_date="2027-06-30").is_valid())
        # Otra empresa puede tener las mismas fechas.
        self.assertTrue(self.form(company=make_company(name="Otra").pk).is_valid())

    def test_shortening_cannot_leave_scheduled_visits_without_contract(self):
        today = timezone.localdate()
        contract = make_contract(self.company, start=today - timedelta(days=10), end=today + timedelta(days=60))
        make_visit(make_site(self.company), at(today + timedelta(days=40)))
        form = self.form(instance=contract, start_date=contract.start_date.isoformat(),
                         end_date=(today + timedelta(days=20)).isoformat())
        self.assertFalse(form.is_valid())
        self.assertIn("quedarían sin contrato", " ".join(form.non_field_errors()))

    def test_company_cannot_change_once_registered(self):
        contract = make_contract(self.company)
        self.assertNotIn("company", self.form(instance=contract).fields)

    def test_new_document_discards_the_old_summary_unless_already_read(self):
        contract = make_contract(self.company, ai_summary={"summary": "Viejo"}, ai_model="x")
        other = sample_pdf("Otro documento")
        form = self.form(instance=contract, files={"document": pdf_upload(other)},
                         start_date=contract.start_date.isoformat(), end_date=contract.end_date.isoformat())
        self.assertTrue(form.is_valid(), form.errors)
        self.assertEqual(form.save().ai_summary, {})


class ReaderTests(TestCase):
    @override_settings(ANTHROPIC_API_KEY="")
    def test_without_key_the_reader_is_unavailable(self):
        self.assertFalse(reader.is_configured())
        with self.assertRaises(reader.ReaderUnavailable):
            reader.read_contract(sample_pdf())

    @override_settings(ANTHROPIC_API_KEY="clave-de-prueba", CONTRACT_AI_MODEL="claude-opus-5-5")
    def test_sends_the_pdf_with_a_fixed_schema_and_a_fallback(self):
        patcher, create = fake_client()
        pdf = sample_pdf()
        with patcher:
            result = reader.read_contract(pdf)
        kwargs = create.call_args.kwargs
        self.assertEqual(kwargs["model"], "claude-opus-5-5")
        self.assertEqual(kwargs["fallbacks"], "default")
        self.assertIn(reader.FALLBACK_BETA, kwargs["betas"])
        self.assertEqual(kwargs["output_config"]["format"]["schema"], reader.SCHEMA)
        document = kwargs["messages"][0]["content"][0]
        self.assertEqual(document["source"]["media_type"], "application/pdf")
        self.assertEqual(base64.b64decode(document["source"]["data"]), pdf)
        self.assertNotIn("temperature", kwargs)
        self.assertEqual(result.summary["client_nit"], "900123456")
        self.assertEqual(result.summary["start_date"], "2026-01-01")

    @override_settings(ANTHROPIC_API_KEY="clave-de-prueba")
    def test_api_errors_become_messages_for_the_user(self):
        request = httpx2.Request("POST", "https://api.anthropic.com/v1/messages")
        cases = [
            (api_error(anthropic.AuthenticationError, 401), "clave de la API"),
            (api_error(anthropic.RateLimitError, 429), "límite de uso"),
            (api_error(anthropic.BadRequestError, 400), "no pudo abrir el documento"),
            (api_error(anthropic.InternalServerError, 500), "no está disponible"),
            (anthropic.APITimeoutError(request=request), "tardó demasiado"),
            (anthropic.APIConnectionError(request=request), "No se pudo conectar"),
        ]
        for error, message in cases:
            patcher, _ = fake_client(error=error)
            with patcher, self.assertRaisesMessage(reader.ReadingFailed, message):
                reader.read_contract(sample_pdf())

    @override_settings(ANTHROPIC_API_KEY="clave-de-prueba")
    def test_refusals_truncation_and_broken_json_are_reported(self):
        for response, message in (
            (fake_response(stop_reason="refusal"), "no pudo procesar"),
            (fake_response(stop_reason="max_tokens"), "demasiado extenso"),
            (fake_response(text="{no es json"), "incompleta"),
        ):
            patcher, _ = fake_client(response)
            with patcher, self.assertRaisesMessage(reader.ReadingFailed, message):
                reader.read_contract(sample_pdf())

    def test_untrusted_values_are_cleaned(self):
        summary = reader.clean_summary(json.loads(reading_json(
            contract_type="borrar_todo",
            client_nit="900.123.456-9",  # digito de verificacion incorrecto
            start_date="31/12/2026",
            end_date="2025-01-01",
            value_cop=True,
            alerts=["x" * 900, 5, None],
            summary="  Texto   con   espacios  ",
        )))
        self.assertEqual(summary["contract_type"], Contract.Kind.OTHER)
        self.assertIsNone(summary["client_nit"])
        self.assertEqual(summary["client_nit_text"], "900.123.456-9")
        self.assertIsNone(summary["start_date"])
        self.assertIsNone(summary["value_cop"])
        self.assertEqual(summary["summary"], "Texto con espacios")
        self.assertEqual(len(summary["alerts"][0]), 300)
        self.assertEqual(len(summary["alerts"]), 1)

    def test_inverted_dates_add_an_alert(self):
        summary = reader.clean_summary(json.loads(reading_json(start_date="2026-12-31", end_date="2026-01-01")))
        self.assertIn("anterior a la inicial", summary["alerts"][-1])


@override_settings(ANTHROPIC_API_KEY="clave-de-prueba")
class ContractViewTests(TestCase):
    def setUp(self):
        self.engineer = make_user(role=Role.ENGINEER)
        self.company = make_company(name="Café Montaña S.A.S.", nit="900123456")
        self.contract = make_contract(self.company, start=date(2026, 1, 1), end=date(2026, 12, 31),
                                      responsible_name="Marta Salazar", value=12_000_000)
        self.foreign = make_contract(make_company(name="Ajena"))

    def test_engineer_manages_contracts_and_others_do_not(self):
        self.client.force_login(self.engineer)
        for name in ("contracts:list", "contracts:create"):
            self.assertEqual(self.client.get(reverse(name)).status_code, 200, name)
        for user in (make_user(role=Role.ADMIN), make_user(role=Role.COMPANY, company=self.company)):
            self.client.force_login(user)
            self.assertEqual(self.client.get(reverse("contracts:list")).status_code, 403, user.role)
            self.assertEqual(self.client.get(reverse("contracts:update", args=[self.contract.pk])).status_code, 403)
            self.assertEqual(self.client.post(reverse("contracts:delete", args=[self.contract.pk])).status_code, 403)
        self.assertTrue(Contract.objects.filter(pk=self.contract.pk).exists())

    def test_company_sees_only_its_contract_and_its_pdf(self):
        self.client.force_login(make_user(role=Role.COMPANY, company=self.company))
        response = self.client.get(reverse("contracts:detail", args=[self.contract.pk]))
        self.assertContains(response, self.contract.display_code)
        self.assertNotContains(response, "Resumen con IA")
        pdf = self.client.get(reverse("contracts:file", args=[self.contract.pk]))
        self.assertEqual(pdf["Content-Type"], "application/pdf")
        self.assertIn("no-store", pdf["Cache-Control"])
        self.assertEqual(self.client.get(reverse("contracts:detail", args=[self.foreign.pk])).status_code, 404)
        self.assertEqual(self.client.get(reverse("contracts:file", args=[self.foreign.pk])).status_code, 404)

    def test_support_cannot_download_contracts(self):
        self.client.force_login(make_user(role=Role.ADMIN))
        self.assertEqual(self.client.get(reverse("contracts:file", args=[self.contract.pk])).status_code, 403)

    def test_list_filters_by_status(self):
        self.client.force_login(self.engineer)
        today = timezone.localdate()
        expiring = make_contract(make_company(name="Por vencer"), start=today - timedelta(days=300), end=today + timedelta(days=10))
        listed = list(self.client.get(reverse("contracts:list"), {"estado": "por_vencer"}).context["contracts"])
        self.assertIn(expiring, listed)
        self.assertNotIn(self.foreign, listed)

    def test_summary_is_generated_once_per_document_and_compared(self):
        self.client.force_login(self.engineer)
        patcher, create = fake_client(fake_response(reading_json(end_date="2027-01-31", value_cop=15000000)))
        with patcher:
            self.client.post(reverse("contracts:summarize", args=[self.contract.pk]))
            self.client.post(reverse("contracts:summarize", args=[self.contract.pk]))
        self.assertEqual(create.call_count, 1)
        self.contract.refresh_from_db()
        self.assertEqual(self.contract.ai_model, "claude-opus-5-5")

        response = self.client.get(reverse("contracts:detail", args=[self.contract.pk]))
        rows = {row["label"]: row for row in response.context["comparison"]}
        self.assertFalse(rows["NIT"]["differs"])
        self.assertTrue(rows["Fin"]["differs"])
        self.assertTrue(rows["Valor"]["differs"])
        self.assertFalse(rows["Encargado"]["differs"])
        self.assertContains(response, "No coincide")
        self.assertFalse(response.context["nit_mismatch"])

    def test_document_of_another_company_is_flagged(self):
        self.client.force_login(self.engineer)
        patcher, _ = fake_client(fake_response(reading_json(client_nit="860.002.964-4")))
        with patcher:
            self.client.post(reverse("contracts:summarize", args=[self.contract.pk]))
        response = self.client.get(reverse("contracts:detail", args=[self.contract.pk]))
        self.assertTrue(response.context["nit_mismatch"])
        self.assertContains(response, "no es el de")

    def test_failed_reading_shows_a_message_and_keeps_the_contract(self):
        self.client.force_login(self.engineer)
        patcher, _ = fake_client(error=api_error(anthropic.RateLimitError, 429))
        with patcher:
            response = self.client.post(reverse("contracts:summarize", args=[self.contract.pk]), follow=True)
        self.assertContains(response, "límite de uso")
        self.contract.refresh_from_db()
        self.assertEqual(self.contract.ai_summary, {})

    def test_form_reading_fills_fields_and_is_reused_when_saving(self):
        self.client.force_login(self.engineer)
        other = make_company(name="Cliente nuevo", nit="860002964")
        pdf = sample_pdf("Contrato del cliente nuevo")
        patcher, create = fake_client(fake_response(reading_json(client_nit="860.002.964-4", start_date="2027-01-01", end_date="2027-12-31")))
        with patcher:
            response = self.client.post(reverse("contracts:read"), {"document": pdf_upload(pdf)})
        body = response.json()
        self.assertEqual(body["fields"]["company"], other.pk)
        self.assertEqual(body["fields"]["start_date"], "2027-01-01")
        self.assertTrue(body["company_found"])
        self.assertEqual(ContractReading.objects.count(), 1)

        self.client.post(reverse("contracts:create"), {
            "document": pdf_upload(pdf), "company": other.pk, "kind": "prestacion_servicios",
            "service": "RULA", "start_date": "2027-01-01", "end_date": "2027-12-31", "responsible_name": "Marta",
        })
        contract = Contract.objects.get(company=other)
        self.assertEqual(contract.ai_summary["client_nit"], "860002964")
        self.assertEqual(create.call_count, 1)

    def test_form_reading_rejects_non_pdf_and_reports_api_errors(self):
        self.client.force_login(self.engineer)
        response = self.client.post(reverse("contracts:read"), {"document": pdf_upload(b"hola")})
        self.assertEqual(response.status_code, 400)
        patcher, _ = fake_client(error=api_error(anthropic.AuthenticationError, 401))
        with patcher:
            response = self.client.post(reverse("contracts:read"), {"document": pdf_upload()})
        self.assertEqual(response.status_code, 502)
        self.assertIn("clave", response.json()["error"])

    @override_settings(ANTHROPIC_API_KEY="")
    def test_without_key_the_pages_work_without_ai(self):
        self.client.force_login(self.engineer)
        self.assertContains(self.client.get(reverse("contracts:create")), "no está configurada")
        response = self.client.post(reverse("contracts:read"), {"document": pdf_upload()})
        self.assertEqual(response.status_code, 503)

    def test_contract_with_pending_visits_cannot_be_deleted(self):
        today = timezone.localdate()
        contract = make_contract(make_company(name="Con visitas"), start=today - timedelta(days=5), end=today + timedelta(days=90))
        make_visit(make_site(contract.company), at(today + timedelta(days=10)))
        self.client.force_login(self.engineer)
        response = self.client.post(reverse("contracts:delete", args=[contract.pk]), follow=True)
        self.assertContains(response, "Deben cancelarse o reprogramarse")
        self.assertTrue(Contract.objects.filter(pk=contract.pk).exists())
        Visit.objects.update(status=Visit.Status.CANCELLED, cancelled_at=timezone.now(), cancellation_reason="x")
        self.client.post(reverse("contracts:delete", args=[contract.pk]))
        self.assertFalse(Contract.objects.filter(pk=contract.pk).exists())

    def test_company_page_shows_the_current_contract(self):
        self.client.force_login(self.engineer)
        empty = make_company(name="Sin contrato")
        self.assertContains(self.client.get(reverse("companies:detail", args=[empty.pk])), "Sin contrato vigente")
        today = timezone.localdate()
        current = make_contract(empty, start=today - timedelta(days=1), end=today + timedelta(days=200))
        self.assertContains(self.client.get(reverse("companies:detail", args=[empty.pk])), current.display_code)
