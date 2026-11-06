"""Crea los datos de demostracion. Se puede ejecutar varias veces sin duplicar nada.

Cada bloque se identifica por un dato natural (NIT, correo, nombre dentro de su padre),
asi que una segunda ejecucion encuentra lo que ya existe. Las visitas y evaluaciones se
crean solo la primera vez que aparece cada puesto, para no acumular datos en cada despliegue.
Las fechas son relativas al dia en que se ejecuta.
"""
import random
from datetime import datetime, time, timedelta
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.utils import timezone

from apps.accounts.models import Role
from apps.companies.models import Area, Company, Position, Site
from apps.evaluations.models import Evaluation, Posture, PosturePhoto, Recommendation, RulaAssessment
from apps.geography.models import Municipality
from apps.visits.models import Visit

from . import data
from .figures import draw_posture

# Semilla fija: dos instalaciones nuevas tienen los mismos datos de demostracion.
SEED = 2026
VISIT_HOURS = (8, 9, 10, 11, 14, 15, 16)


def place(name: str, department: str) -> Municipality:
    return Municipality.objects.get(name=name, department__name=department)


def working_day(day):
    """Corre sabados y domingos al lunes siguiente."""
    return day + timedelta(days=(7 - day.weekday()) % 7) if day.weekday() >= 5 else day


class DemoBuilder:
    def __init__(self, password: str):
        self.password = password
        self.random = random.Random(SEED)
        self.today = timezone.localdate()
        self.counts = {"empresas": 0, "puestos": 0, "visitas": 0, "evaluaciones": 0, "usuarios": 0}
        self.new_positions: list[tuple[Position, str]] = []

    def build(self) -> dict[str, int]:
        companies = {row[0]: self.company(*row) for row in data.COMPANIES}
        users = self.users(companies)
        evaluators = [users["evaluador@ergopostura.test"], users["ingeniero@ergopostura.test"],
                      users["evaluador2@ergopostura.test"]]
        followers = [users["tareas@ergopostura.test"], users["empresa@ergopostura.test"]]
        authors = {"900123456": users["empresa@ergopostura.test"], None: users["admin@ergopostura.test"]}
        for index, (position, contact) in enumerate(self.new_positions):
            self.history(index, position, contact, evaluators, followers, authors)
        return self.counts

    # Estructura -------------------------------------------------------------------------

    def company(self, nit, name, city, department, active, contact, sites) -> Company:
        company, created = Company.objects.get_or_create(
            nit=nit, defaults={"name": name, "municipality": place(city, department), "is_active": active}
        )
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
                    position, created = Position.objects.get_or_create(
                        area=area, name=position_name, defaults={"description": description}
                    )
                    # Un puesto sin evaluaciones aun no tiene historia de demostracion.
                    if not position.evaluations.exists():
                        self.new_positions.append((position, contact))
                        self.counts["puestos"] += created
        return company

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

    # Historia de cada puesto: visitas, evaluaciones y seguimiento ---------------------------

    def history(self, index, position, contact, evaluators, followers, authors):
        """Una visita pasada con su evaluacion, otra futura, y a veces una evaluacion en curso."""
        company = position.company
        evaluator = evaluators[index % len(evaluators)]
        author = authors.get(company.nit, authors[None])

        past_day = working_day(self.today - timedelta(days=self.random.randint(5, 50)))
        past_visit = self.visit(position, past_day, contact, author)
        if company.is_active:
            future_day = working_day(self.today + timedelta(days=self.random.randint(1, 28)))
            self.visit(position, future_day, contact, author)

        keys = data.POSITION_POSTURES.get(position.name, ("mostrador",))
        self.evaluation(position, past_visit, evaluator, keys, complete=True, followers=followers)
        if company.is_active and index % 4 == 1:
            # Reevaluacion pendiente: aparece en las tareas del profesional que la lleva.
            self.evaluation(position, None, evaluator, keys[:1], complete=False, followers=followers)

    def visit(self, position, day, contact, author) -> Visit:
        hour = self.random.choice(VISIT_HOURS)
        moment = timezone.make_aware(datetime.combine(day, time(hour, self.random.choice((0, 30)))))
        visit, created = Visit.objects.get_or_create(
            position=position, scheduled_at=moment, defaults={"contact_name": contact, "created_by": author}
        )
        self.counts["visitas"] += created
        return visit

    def evaluation(self, position, visit, evaluator, keys, *, complete, followers):
        evaluated_on = timezone.localtime(visit.scheduled_at).date() if visit else self.today
        heavy = "levantar" in keys or "paciente" in keys
        evaluation = Evaluation.objects.create(
            position=position,
            visit=visit,
            evaluator=evaluator,
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
                for position_in_list, text in enumerate(recommendations or ("Revisar la organización del puesto.",)):
                    recommendation = Recommendation.objects.create(posture=posture, text=text, author=evaluator)
                    if complete and position_in_list == 0 and self.random.random() < 0.5:
                        recommendation.attended_at = timezone.now() - timedelta(days=self.random.randint(1, 4))
                        recommendation.attended_by = self.random.choice(followers)
                        recommendation.save(update_fields=["attended_at", "attended_by"])

        if complete:
            evaluation.status = Evaluation.Status.COMPLETED
            evaluation.completed_at = timezone.make_aware(datetime.combine(evaluated_on, time(17)))
            evaluation.save(update_fields=["status", "completed_at"])
        return evaluation
