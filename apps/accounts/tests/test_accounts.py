from django.db import IntegrityError, transaction
from django.test import TestCase

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








class AccountManagementTests(TestCase):
    """Soporte crea al ingeniero; el ingeniero, los accesos de sus empresas cliente."""

    def setUp(self):
        self.support = make_user(role=Role.ADMIN, email="soporte@ergopostura.test")
        self.engineer = make_user(role=Role.ENGINEER, email="ingeniero@ergopostura.test")
        self.company = make_company()











    def test_last_active_support_account_is_detected(self):
        # Defensa adicional: aunque hoy solo soporte gestiona soporte, el sistema nunca
        # debe quedar sin una cuenta capaz de administrarlo.
        from apps.accounts.selectors import is_last_active_admin

        self.assertTrue(is_last_active_admin(self.support))
        make_user(role=Role.ADMIN)
        self.assertFalse(is_last_active_admin(self.support))




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
