from django.db import IntegrityError, transaction
from django.test import TestCase
from django.urls import reverse

from apps.accounts.models import Role, User
from apps.accounts.permissions import ROLE_CAPABILITIES, Capability, has_capability
from apps.core.tests.factories import PASSWORD, make_company, make_user


class UserModelTests(TestCase):
    def test_email_is_stored_in_lowercase_and_unique_regardless_of_case(self):
        make_user(email="Laura@Empresa.COM")
        self.assertTrue(User.objects.filter(email="laura@empresa.com").exists())
        with self.assertRaises(IntegrityError), transaction.atomic():
            make_user(email="LAURA@empresa.com")

    def test_company_role_requires_company_at_database_level(self):
        with self.assertRaises(IntegrityError), transaction.atomic():
            User.objects.create_user(email="a@b.test", password=PASSWORD, role=Role.COMPANY)

    def test_other_roles_cannot_have_company(self):
        with self.assertRaises(IntegrityError), transaction.atomic():
            User.objects.create_user(
                email="a@b.test", password=PASSWORD, role=Role.ENGINEER, company=make_company()
            )

    def test_invalid_role_is_rejected_by_database(self):
        with self.assertRaises(IntegrityError), transaction.atomic():
            User.objects.create_user(email="a@b.test", password=PASSWORD, role="inventado")

    def test_staff_flags_follow_the_role(self):
        admin = make_user(role=Role.ADMIN)
        self.assertTrue(admin.is_staff and admin.is_superuser)
        admin.role = Role.ENGINEER
        admin.save()
        admin.refresh_from_db()
        self.assertFalse(admin.is_staff or admin.is_superuser)

    def test_create_superuser_is_admin(self):
        user = User.objects.create_superuser(email="root@b.test", password=PASSWORD)
        self.assertEqual(user.role, Role.ADMIN)
        self.assertTrue(user.is_superuser)


class PermissionPolicyTests(TestCase):
    def test_every_role_has_a_policy(self):
        self.assertEqual(set(ROLE_CAPABILITIES), set(Role))

    def test_support_only_manages_accounts(self):
        """Soporte no evalua, no agenda ni ve datos de las empresas: solo gestiona cuentas."""
        self.assertEqual(ROLE_CAPABILITIES[Role.ADMIN], frozenset({Capability.USER_MANAGE}))

    def holders(self, capability):
        return {role for role, capabilities in ROLE_CAPABILITIES.items() if capability in capabilities}

    def test_each_job_belongs_to_one_role(self):
        self.assertEqual(self.holders(Capability.EVALUATION_MANAGE), {Role.ENGINEER})
        self.assertEqual(self.holders(Capability.COMPANY_MANAGE), {Role.ENGINEER})
        self.assertEqual(self.holders(Capability.CONTRACT_MANAGE), {Role.ENGINEER})
        self.assertEqual(self.holders(Capability.VISIT_ATTEND), {Role.ENGINEER})
        self.assertEqual(self.holders(Capability.VISIT_SCHEDULE), {Role.COMPANY})
        self.assertEqual(self.holders(Capability.TASK_ATTEND), {Role.COMPANY})

    def test_user_read_from_database_keeps_capabilities(self):
        pk = make_user(role=Role.ENGINEER).pk
        self.assertTrue(has_capability(User.objects.get(pk=pk), Capability.COMPANY_MANAGE))

    def test_inactive_user_has_no_capabilities(self):
        self.assertFalse(has_capability(make_user(role=Role.ADMIN, is_active=False), Capability.USER_MANAGE))


class LoginTests(TestCase):
    url = "/ingresar/"

    def test_login_is_case_insensitive_on_email(self):
        make_user(email="laura@empresa.com")
        response = self.client.post(self.url, {"username": "LAURA@empresa.com", "password": PASSWORD})
        self.assertRedirects(response, reverse("dashboard:home"))

    def test_wrong_password_shows_generic_error(self):
        make_user(email="laura@empresa.com")
        response = self.client.post(self.url, {"username": "laura@empresa.com", "password": "mala"})
        self.assertContains(response, "El correo o la contraseña no son correctos.")
        self.assertNotIn("_auth_user_id", self.client.session)

    def test_session_ends_with_browser_unless_remember_is_checked(self):
        make_user(email="laura@empresa.com")
        self.client.post(self.url, {"username": "laura@empresa.com", "password": PASSWORD})
        self.assertTrue(self.client.session.get_expire_at_browser_close())

        self.client.logout()
        self.client.post(self.url, {"username": "laura@empresa.com", "password": PASSWORD, "remember": "on"})
        self.assertFalse(self.client.session.get_expire_at_browser_close())

    def test_inactive_user_cannot_log_in(self):
        make_user(email="laura@empresa.com", is_active=False)
        self.client.post(self.url, {"username": "laura@empresa.com", "password": PASSWORD})
        self.assertNotIn("_auth_user_id", self.client.session)

    def test_external_next_url_is_ignored(self):
        make_user(email="laura@empresa.com")
        response = self.client.post(
            self.url,
            {"username": "laura@empresa.com", "password": PASSWORD, "next": "https://malicioso.test/"},
        )
        self.assertRedirects(response, reverse("dashboard:home"))

    def test_logout_requires_post(self):
        self.client.force_login(make_user())
        self.assertEqual(self.client.get("/salir/").status_code, 405)
        self.assertIn("_auth_user_id", self.client.session)
        self.client.post("/salir/")
        self.assertNotIn("_auth_user_id", self.client.session)


class UserAdminTests(TestCase):
    def setUp(self):
        self.client.force_login(make_user(role=Role.ADMIN))

    def test_changelist_and_change_pages_open(self):
        user = make_user()
        self.assertEqual(self.client.get(reverse("admin:accounts_user_changelist")).status_code, 200)
        self.assertEqual(self.client.get(reverse("admin:accounts_user_change", args=[user.pk])).status_code, 200)

    def test_admin_creates_a_user_from_the_add_form(self):
        response = self.client.post(
            reverse("admin:accounts_user_add"),
            {
                "email": "Nuevo@Empresa.com",
                "first_name": "Nuevo",
                "last_name": "Usuario",
                "role": Role.ENGINEER,
                "company": "",
                "usable_password": "true",
                "password1": PASSWORD,
                "password2": PASSWORD,
            },
        )
        self.assertEqual(response.status_code, 302)
        self.assertTrue(User.objects.filter(email="nuevo@empresa.com").exists())

    def test_add_form_explains_missing_company_instead_of_crashing(self):
        response = self.client.post(
            reverse("admin:accounts_user_add"),
            {
                "email": "e@empresa.com",
                "role": Role.COMPANY,
                "company": "",
                "usable_password": "true",
                "password1": PASSWORD,
                "password2": PASSWORD,
            },
        )
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "El rol Empresa debe tener una empresa asociada.")

    def test_non_admin_cannot_enter_django_admin(self):
        self.client.force_login(make_user(role=Role.ENGINEER))
        response = self.client.get(reverse("admin:accounts_user_changelist"))
        self.assertEqual(response.status_code, 302)
        self.assertIn("/admin/login/", response["Location"])


class AdminPanelTests(TestCase):
    def test_anonymous_goes_to_the_system_login_and_comes_back(self):
        response = self.client.get("/admin/")
        self.assertRedirects(response, "/admin/login/?next=/admin/", fetch_redirect_response=False)
        login = self.client.get(response["Location"])
        self.assertRedirects(login, f"{reverse('accounts:login')}?next=/admin/", fetch_redirect_response=False)

    def test_logged_in_non_admin_gets_403_instead_of_a_redirect_loop(self):
        self.client.force_login(make_user(role=Role.ENGINEER))
        self.assertEqual(self.client.get("/admin/login/?next=/admin/").status_code, 403)

    def test_panel_shows_the_system_brand_and_hides_unused_groups(self):
        self.client.force_login(make_user(role=Role.ADMIN))
        response = self.client.get("/admin/")
        self.assertContains(response, "ErgoPostura")
        self.assertContains(response, "admin.css")
        self.assertNotContains(response, "Django")
        self.assertNotContains(response, "/admin/auth/group/")
        self.assertContains(response, reverse("accounts:logout"))


class AccountManagementTests(TestCase):
    """Soporte crea al ingeniero; el ingeniero, los accesos de sus empresas cliente."""

    def setUp(self):
        self.support = make_user(role=Role.ADMIN, email="soporte@ergopostura.test")
        self.engineer = make_user(role=Role.ENGINEER, email="ingeniero@ergopostura.test")
        self.company = make_company()

    def create(self, actor, **data):
        self.client.force_login(actor)
        payload = {
            "first_name": "Laura", "last_name": "Ríos", "email": "laura@cliente.com",
            "password1": "Clave-temporal-2026", "password2": "Clave-temporal-2026", **data,
        }
        return self.client.post(reverse("accounts:user_create"), payload)

    def test_support_creates_the_engineer_with_a_temporary_password(self):
        response = self.create(self.support, role=Role.ENGINEER, email="nuevo@ergopostura.test")
        self.assertEqual(response.status_code, 302)
        user = User.objects.get(email="nuevo@ergopostura.test")
        self.assertEqual(user.role, Role.ENGINEER)
        self.assertTrue(user.must_change_password)
        self.assertEqual(user.created_by, self.support)

    def test_support_cannot_create_company_accounts(self):
        response = self.create(self.support, role=Role.COMPANY, company=self.company.pk)
        self.assertEqual(response.status_code, 200)
        self.assertFalse(User.objects.filter(email="laura@cliente.com").exists())

    def test_engineer_creates_company_access_and_cannot_raise_privileges(self):
        # Un rol manipulado en el formulario no esta entre las opciones del ingeniero.
        self.assertEqual(self.create(self.engineer, role=Role.ADMIN, company=self.company.pk).status_code, 200)
        self.assertFalse(User.objects.filter(email="laura@cliente.com").exists())

        self.create(self.engineer, role=Role.COMPANY, company=self.company.pk)
        user = User.objects.get(email="laura@cliente.com")
        self.assertEqual(user.role, Role.COMPANY)
        self.assertEqual(user.company, self.company)
        self.assertFalse(user.is_staff)

    def test_company_account_needs_a_company(self):
        response = self.create(self.engineer, role=Role.COMPANY)
        self.assertContains(response, "Elige la empresa")

    def test_weak_or_mismatched_passwords_are_rejected(self):
        self.assertContains(self.create(self.engineer, company=self.company.pk, password1="123", password2="123"), "contraseña")
        self.assertContains(
            self.create(self.engineer, company=self.company.pk, password2="Otra-clave-2026"), "no coinciden"
        )
        self.assertFalse(User.objects.filter(email="laura@cliente.com").exists())

    def test_duplicate_email_ignores_case(self):
        response = self.create(self.support, role=Role.ENGINEER, email="INGENIERO@ergopostura.test")
        self.assertContains(response, "Ya existe una cuenta con este correo.")

    def test_engineer_only_sees_company_accounts(self):
        member = make_user(role=Role.COMPANY, company=self.company)
        self.client.force_login(self.engineer)
        listed = set(self.client.get(reverse("accounts:users")).context["accounts"])
        self.assertEqual(listed, {member})
        for target in (self.support, self.engineer):
            self.assertEqual(self.client.get(reverse("accounts:user_update", args=[target.pk])).status_code, 404)
            self.assertEqual(self.client.post(reverse("accounts:user_toggle", args=[target.pk])).status_code, 404)

    def test_company_users_cannot_manage_accounts(self):
        self.client.force_login(make_user(role=Role.COMPANY, company=self.company))
        self.assertEqual(self.client.get(reverse("accounts:users")).status_code, 403)

    def test_deactivation_rules(self):
        self.client.force_login(self.support)
        self.client.post(reverse("accounts:user_toggle", args=[self.support.pk]))
        self.support.refresh_from_db()
        self.assertTrue(self.support.is_active)
        self.client.post(reverse("accounts:user_toggle", args=[self.engineer.pk]))
        self.engineer.refresh_from_db()
        self.assertFalse(self.engineer.is_active)

    def test_last_active_support_account_is_detected(self):
        # Defensa adicional: aunque hoy solo soporte gestiona soporte, el sistema nunca
        # debe quedar sin una cuenta capaz de administrarlo.
        from apps.accounts.selectors import is_last_active_admin

        self.assertTrue(is_last_active_admin(self.support))
        make_user(role=Role.ADMIN)
        self.assertFalse(is_last_active_admin(self.support))

    def test_temporary_password_forces_a_change_before_anything_else(self):
        self.client.force_login(self.support)
        self.client.post(
            reverse("accounts:user_password", args=[self.engineer.pk]),
            {"new_password1": "Temporal-segura-26", "new_password2": "Temporal-segura-26"},
        )
        self.engineer.refresh_from_db()
        self.assertTrue(self.engineer.must_change_password)

        self.client.force_login(self.engineer)
        self.assertRedirects(self.client.get(reverse("companies:list")), reverse("accounts:password_change"))
        response = self.client.get(reverse("companies:list"), HTTP_HX_REQUEST="true")
        self.assertEqual(response["HX-Redirect"], reverse("accounts:password_change"))
        self.client.post(
            reverse("accounts:password_change"),
            {"old_password": "Temporal-segura-26", "new_password1": "Mi-clave-propia-77", "new_password2": "Mi-clave-propia-77"},
        )
        self.engineer.refresh_from_db()
        self.assertFalse(self.engineer.must_change_password)
        self.assertEqual(self.client.get(reverse("companies:list")).status_code, 200)

    def test_company_detail_lists_its_accesses(self):
        member = make_user(role=Role.COMPANY, company=self.company, email="acceso@cliente.com")
        self.client.force_login(self.engineer)
        response = self.client.get(reverse("companies:detail", args=[self.company.pk]))
        self.assertContains(response, "acceso@cliente.com")
        self.assertContains(response, f"{reverse('accounts:user_create')}?empresa={self.company.pk}")
        self.client.force_login(member)
        self.assertNotContains(self.client.get(reverse("companies:detail", args=[self.company.pk])), "Crear acceso")


class KeepOnlySupportMigrationTests(TestCase):
    """La migracion que limpia la base conserva solo la cuenta de DJANGO_ADMIN_EMAIL."""

    def run_cleanup(self, email):
        from importlib import import_module
        from unittest import mock

        from django.apps import apps

        migration = import_module("apps.accounts.migrations.0002_keep_only_support_admin")
        with mock.patch.dict("os.environ", {"DJANGO_ADMIN_EMAIL": email}):
            with mock.patch.object(migration, "DATA_MODELS", ()):
                migration.keep_only_admin(apps, None)

    def test_keeps_the_configured_admin_and_deletes_everyone_else(self):
        keep = make_user(role=Role.ADMIN, email="duenio@ergopostura.com")
        make_user(role=Role.ADMIN, email="admin@ergopostura.test")
        make_user(role=Role.ENGINEER)
        make_user(role=Role.COMPANY)
        self.run_cleanup("Duenio@ErgoPostura.com")
        self.assertEqual(list(User.objects.values_list("pk", flat=True)), [keep.pk])

    def test_without_the_variable_keeps_support_accounts(self):
        admins = {make_user(role=Role.ADMIN).pk, make_user(role=Role.ADMIN).pk}
        make_user(role=Role.ENGINEER)
        self.run_cleanup("")
        self.assertEqual(set(User.objects.values_list("pk", flat=True)), admins)
