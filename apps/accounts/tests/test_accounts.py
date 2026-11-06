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
                email="a@b.test", password=PASSWORD, role=Role.EVALUATOR, company=make_company()
            )

    def test_invalid_role_is_rejected_by_database(self):
        with self.assertRaises(IntegrityError), transaction.atomic():
            User.objects.create_user(email="a@b.test", password=PASSWORD, role="inventado")

    def test_staff_flags_follow_the_role(self):
        admin = make_user(role=Role.ADMIN)
        self.assertTrue(admin.is_staff and admin.is_superuser)
        admin.role = Role.EVALUATOR
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

    def test_admin_sees_everything_but_does_not_apply_rula(self):
        admin = make_user(role=Role.ADMIN)
        for capability in set(Capability) - {Capability.EVALUATION_MANAGE}:
            self.assertTrue(has_capability(admin, capability), capability)
        self.assertFalse(has_capability(admin, Capability.EVALUATION_MANAGE))

    def test_only_engineer_and_evaluator_apply_rula(self):
        allowed = {
            role for role, capabilities in ROLE_CAPABILITIES.items()
            if Capability.EVALUATION_MANAGE in capabilities
        }
        self.assertEqual(allowed, {Role.ENGINEER, Role.EVALUATOR})

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
                "role": Role.EVALUATOR,
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
