"""Crea los datos de demostracion. Se puede ejecutar varias veces sin duplicar nada.

Sigue el mismo flujo del sistema real:
- Soporte, el ingeniero y dos empresas con acceso.
- Cada empresa tiene su estructura, sus trabajadores y un contrato con su PDF.
- Las visitas caen dentro del contrato, en horario de trabajo y sin cruzarse.
- Cada evaluacion sale de una visita realizada en la misma sede.

Cada bloque se identifica por un dato natural (NIT, correo, nombre dentro de su padre),
asi que una segunda ejecucion encuentra lo que ya existe. La historia de visitas se crea
solo para las sedes que aun no tienen visitas. Las fechas son relativas al dia de ejecucion.
"""
import hashlib
import random
from datetime import date, datetime, time, timedelta
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.utils import timezone

from apps.accounts.models import Role
from apps.companies.models import Area, Company, Position, Site, Worker
from apps.contracts.models import Contract
from apps.evaluations.models import Evaluation, Posture, PosturePhoto, Recommendation, RulaAssessment
from apps.geography.models import Municipality
from apps.visits.models import Visit

from . import data
from .figures import draw_posture
from .pdf import text_pdf

# Semilla fija: dos instalaciones nuevas tienen los mismos datos de demostracion.
SEED = 2026
VISIT_HOURS = (8, 9, 10, 14, 15)
VISIT_MINUTES = 120


def place(name: str, department: str) -> Municipality:
    return Municipality.objects.get(name=name, department__name=department)


def working_day(day: date) -> date:
    """Corre los domingos al lunes: de lunes a sabado se atiende."""
    return day + timedelta(days=1) if day.weekday() == 6 else day


class DemoBuilder:
    def __init__(self, password: str):
        self.password = password
        self.random = random.Random(SEED)
        self.today = timezone.localdate()
        self.now = timezone.now()
        self.counts = {
            "usuarios": 0, "empresas": 0, "trabajadores": 0, "contratos": 0, "visitas": 0, "evaluaciones": 0,
        }
        # Horarios ya tomados: el ingeniero no puede estar en dos visitas a la vez.
        self.taken = {
            (timezone.localtime(start).date(), timezone.localtime(start).hour)
            for start in Visit.objects.exclude(status=Visit.Status.CANCELLED).values_list("scheduled_at", flat=True)
        }
        self.worker_number = 0

    def build(self) -> dict[str, int]:
        companies = [self.company(*row) for row in data.COMPANIES]
        users = self.users({company.nit: company for company in companies})
        engineer = users["ingeniero@ergopostura.test"]
        followers = {user.company_id: user for user in users.values() if user.role == Role.COMPANY}
        for index, company in enumerate(companies):
            contract = self.contract(index, company, engineer)
            for site in company.sites.all():
                if not site.visits.exists():
                    self.history(index, site, contract, engineer, followers.get(company.pk))
        return self.counts

    # Estructura -------------------------------------------------------------------------

    def company(self, nit, name, city, department, active, contact, sites) -> Company:
        company, created = Company.objects.get_or_create(
            nit=nit, defaults={"name": name, "municipality": place(city, department), "is_active": active}
        )
        company.demo_contact = contact
        self.counts["empresas"] += created
        for site_name, site_city, site_department, address, areas in sites:
            site, _ = Site.objects.get_or_create(
                company=company,
                name=site_name,
                defaults={"municipality": place(site_city, site_department), "address": address},
            )
            for area_name, positions in areas:
                area, _ = Area.objects.get_or_create(site=site, name=area_name)
                for position_name, description in positions:
                    position, _ = Position.objects.get_or_create(
                        area=area, name=position_name, defaults={"description": description}
                    )
                    self.workers(position)
        return company

    def workers(self, position):
        if position.workers.exists():
            return
        for _ in range(self.random.choice((1, 2, 2, 3))):
            self.worker_number += 1
            # Documento ficticio estable: depende del puesto y del orden, no del azar.
            seed = int(hashlib.sha256(f"{position.pk}-{self.worker_number}".encode()).hexdigest(), 16)
            Worker.objects.create(
                position=position,
                first_name=self.random.choice(data.FIRST_NAMES),
                last_name=self.random.choice(data.LAST_NAMES),
                document_number=str(1_000_000_000 + seed % 99_000_000),
                hired_on=self.today - timedelta(days=self.random.randint(120, 2400)),
            )
            self.counts["trabajadores"] += 1

    def users(self, companies) -> dict:
        User = get_user_model()
        users = {}
        for email, first_name, last_name, role, nit in data.USERS:
            user = User.objects.filter(email=email).first()
            if user is None:
                user = User.objects.create_user(
                    email=email,
                    password=self.password,
                    first_name=first_name,
                    last_name=last_name,
                    role=role,
                    company=companies[nit] if role == Role.COMPANY else None,
                )
                self.counts["usuarios"] += 1
            users[email] = user
        return users

    # Contrato ---------------------------------------------------------------------------

    def contract(self, index, company, engineer) -> Contract:
        existing = Contract.objects.filter(company=company).order_by("-end_date").first()
        if existing is not None:
            return existing
        if not company.is_active:
            # Empresa inactiva: su contrato ya termino.
            start = self.today - timedelta(days=420)
            end = self.today - timedelta(days=55)
        elif index == 3:
            # Uno por vencer, para que el panel lo avise.
            start = self.today - timedelta(days=345)
            end = self.today + timedelta(days=20)
        else:
            start = self.today - timedelta(days=self.random.randint(60, 200))
            end = start.replace(year=start.year + 1, day=min(start.day, 28)) - timedelta(days=1)
        value = Decimal(self.random.choice((6_500_000, 9_800_000, 12_000_000, 18_400_000)))
        code = f"CPS-{start.year}-{index + 1:03d}"
        pdf = text_pdf(
            f"Contrato de prestación de servicios {code}",
            [
                f"Entre {company.name}, identificada con NIT {company.nit_display}, en adelante EL CONTRATANTE, "
                f"y {engineer.get_full_name()}, ingeniero industrial, en adelante EL CONTRATISTA, se celebra el "
                "presente contrato de prestación de servicios profesionales.",
                f"PRIMERA. OBJETO. {data.CONTRACT_SERVICE}",
                f"SEGUNDA. DURACIÓN. Desde el {start:%d/%m/%Y} hasta el {end:%d/%m/%Y}.",
                f"TERCERA. VALOR. ${int(value):,} pesos colombianos, pagaderos en cuotas mensuales.".replace(",", "."),
                f"CUARTA. SUPERVISIÓN. EL CONTRATANTE designa a {company.demo_contact}, jefe de seguridad y salud "
                "en el trabajo, para coordinar las visitas.",
                "QUINTA. DATOS PERSONALES. Las partes tratarán los datos de los trabajadores conforme a la Ley 1581 de 2012.",
                "SEXTA. TERMINACIÓN. Cualquiera de las partes podrá terminarlo con aviso escrito de treinta días.",
                "Documento ficticio generado para la demostración de ErgoPostura.",
            ],
        )
        contract = Contract.objects.create(
            company=company,
            code=code,
            kind=Contract.Kind.SERVICES,
            service=data.CONTRACT_SERVICE,
            start_date=start,
            end_date=end,
            value=value,
            responsible_name=company.demo_contact,
            responsible_role="Jefe de seguridad y salud en el trabajo",
            file_data=pdf,
            file_name=f"{code}.pdf",
            file_size=len(pdf),
            file_sha256=hashlib.sha256(pdf).hexdigest(),
            created_by=engineer,
        )
        self.counts["contratos"] += 1
        return contract

    # Historia de cada sede: visitas y evaluaciones -----------------------------------------

    def history(self, index, site, contract, engineer, follower):
        company = site.company
        contact = company.demo_contact
        requested_by = follower
        past_offset = self.random.randint(6, 45)
        past_day = min(max(contract.start_date, self.today - timedelta(days=past_offset)), contract.end_date)
        if past_day >= self.today:
            return
        visit = self.visit(site, working_day(past_day), contact, requested_by, Visit.Status.COMPLETED, engineer)
        if visit is None:
            return

        for number, area in enumerate(site.areas.all()):
            for position in area.positions.all():
                keys = data.POSITION_POSTURES.get(position.name, ("mostrador",))
                self.evaluation(position, visit, engineer, keys, complete=True, follower=follower)
                if company.is_active and (index + number) % 4 == 1:
                    # Reevaluacion en curso: aparece en las tareas del ingeniero.
                    self.evaluation(position, visit, engineer, keys[:1], complete=False, follower=follower)

        if not company.is_active:
            return
        # Una visita futura dentro del contrato, y a veces una que ya paso sin registrar.
        upcoming = working_day(self.today + timedelta(days=self.random.randint(1, 25)))
        if upcoming <= contract.end_date:
            self.visit(site, upcoming, contact, requested_by, Visit.Status.SCHEDULED, engineer)
        if index == 0:
            self.visit(site, working_day(self.today - timedelta(days=1)), contact, requested_by,
                       Visit.Status.SCHEDULED, engineer)
        if index == 2:
            cancelled = self.visit(site, working_day(self.today + timedelta(days=4)), contact, requested_by,
                                   Visit.Status.CANCELLED, engineer)
            if cancelled is not None:
                self.taken.discard((timezone.localtime(cancelled.scheduled_at).date(),
                                    timezone.localtime(cancelled.scheduled_at).hour))

    def visit(self, site, day, contact, requested_by, status, engineer) -> Visit | None:
        hours = [hour for hour in VISIT_HOURS if (day, hour) not in self.taken and (day, hour + 1) not in self.taken]
        if day == self.today:
            hours = [hour for hour in hours if hour > timezone.localtime(self.now).hour + 1]
        if not hours:
            return None
        hour = self.random.choice(hours)
        self.taken.update({(day, hour), (day, hour + 1)})
        start = timezone.make_aware(datetime.combine(day, time(hour)))
        visit = Visit(
            site=site,
            scheduled_at=start,
            duration_minutes=VISIT_MINUTES,
            purpose="Evaluar con RULA los puestos de la sede y revisar el avance de las recomendaciones.",
            contact_name=contact,
            contact_phone="300 555 0" + str(100 + site.pk % 900),
            status=status,
            requested_by=requested_by,
        )
        if status == Visit.Status.COMPLETED:
            visit.completed_at = start + timedelta(minutes=VISIT_MINUTES)
            visit.completed_by = engineer
            visit.completion_notes = "Se observaron los puestos de la sede con el encargado de SST."
        elif status == Visit.Status.CANCELLED:
            visit.cancelled_at = self.now - timedelta(days=1)
            visit.cancelled_by = requested_by or engineer
            visit.cancellation_reason = "La planta tendrá mantenimiento general ese día."
        visit.save()
        self.counts["visitas"] += 1
        return visit

    def evaluation(self, position, visit, engineer, keys, *, complete, follower):
        evaluated_on = timezone.localtime(visit.scheduled_at).date()
        heavy = "levantar" in keys or "paciente" in keys
        evaluation = Evaluation.objects.create(
            position=position,
            visit=visit,
            worker=position.workers.filter(is_active=True).first(),
            evaluator=engineer,
            evaluated_on=evaluated_on,
            activity_description=data.ACTIVITIES[keys[0]],
            worker_context="Turno diurno de 8 horas, con una pausa de 15 minutos a media mañana.",
            carries_load=heavy,
            load_weight_kg=Decimal("15.00") if heavy else None,
            repetitive_movements=any(key in ("coser", "empacar") for key in keys),
            repetition_notes="Ciclos de menos de 30 segundos." if "coser" in keys else "",
        )
        self.counts["evaluaciones"] += 1

        for number, key in enumerate(keys):
            name, duration, unit, rula, recommendations = data.POSTURES[key]
            posture = Posture.objects.create(
                evaluation=evaluation, name=name, duration_value=Decimal(duration), duration_unit=unit
            )
            image, width, height = draw_posture(rula)
            photo = PosturePhoto.objects.create(
                posture=posture, data=image, content_type="image/jpeg", width=width, height=height,
                original_name=f"figura-demo-{key}.jpg",
            )
            # Una evaluacion en curso deja su ultima postura sin analizar, como pasaria en campo.
            if not complete and number == len(keys) - 1 and len(keys) > 1:
                continue
            assessment = RulaAssessment(posture=posture, photo=photo, **rula)
            assessment.recalculate()
            assessment.save()
            if assessment.action_level > 1:
                for order, text in enumerate(recommendations or ("Revisar la organización del puesto.",)):
                    recommendation = Recommendation.objects.create(posture=posture, text=text, author=engineer)
                    # Las atiende la empresa: solo las que tienen acceso al sistema.
                    if complete and follower and order == 0 and self.random.random() < 0.5:
                        recommendation.attended_at = self.now - timedelta(days=self.random.randint(1, 4))
                        recommendation.attended_by = follower
                        recommendation.save(update_fields=["attended_at", "attended_by"])

        if complete:
            evaluation.status = Evaluation.Status.COMPLETED
            evaluation.completed_at = timezone.make_aware(datetime.combine(evaluated_on, time(17)))
            evaluation.save(update_fields=["status", "completed_at"])
        return evaluation
