from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.contrib.staticfiles import finders
from django.test import TestCase
from django.urls import reverse


class LoginViewTests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(
            username="operador",
            email="operador@empresa.com",
            password="clave-segura-2026",
        )

    def test_login_page_is_available(self):
        response = self.client.get(reverse("login"))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "usuarios/login.html")
        self.assertContains(response, "Diseñado por Alejandro Romero - Logística SV", count=2)
        self.assertNotContains(response, "Gestión inteligente")
        self.assertNotContains(response, "Todo bajo control")
        self.assertIsNotNone(finders.find("usuarios/images/equipo-logistica-sv.jpeg"))

    def test_protected_home_redirects_anonymous_user(self):
        response = self.client.get(reverse("usuarios:inicio"))
        expected = f"{reverse('login')}?next={reverse('usuarios:inicio')}"
        self.assertRedirects(response, expected)

    def test_user_can_login_with_email(self):
        response = self.client.post(
            reverse("login"),
            {"username": self.user.email, "password": "clave-segura-2026"},
        )
        self.assertRedirects(response, reverse("usuarios:inicio"))
        self.assertEqual(int(self.client.session["_auth_user_id"]), self.user.pk)

    def test_invalid_credentials_show_error(self):
        response = self.client.post(
            reverse("login"),
            {"username": "operador", "password": "incorrecta"},
        )
        self.assertContains(response, "El usuario o la contraseña no son correctos.")

    def test_editor_is_sent_directly_to_inventory_count(self):
        self.user.groups.add(Group.objects.get(name="Editores"))
        response = self.client.post(
            reverse("login"),
            {"username": self.user.username, "password": "clave-segura-2026"},
        )
        self.assertRedirects(response, reverse("archivos:inventory_count_index"))


class UserManagementTests(TestCase):
    def setUp(self):
        User = get_user_model()
        self.admin = User.objects.create_superuser(
            username="noel.rivera",
            email="noel@empresa.com",
            password="admin-2026-seguro",
        )
        self.supervisor = User.objects.create_user(
            username="supervisor",
            email="supervisor@empresa.com",
            password="supervisor-2026",
        )
        self.supervisor.groups.add(Group.objects.get(name="Supervisores"))

    def test_admin_can_open_user_management(self):
        self.client.force_login(self.admin)
        response = self.client.get(reverse("usuarios:user_list"))
        self.assertEqual(response.status_code, 200)

    def test_non_admin_cannot_open_user_management(self):
        self.client.force_login(self.supervisor)
        response = self.client.get(reverse("usuarios:user_list"))
        self.assertEqual(response.status_code, 403)

    def test_admin_can_create_manager(self):
        self.client.force_login(self.admin)
        response = self.client.post(
            reverse("usuarios:user_create"),
            {
                "username": "gerencia",
                "first_name": "Usuario",
                "last_name": "Gerente",
                "email": "gerencia@empresa.com",
                "role": "Gerente",
                "is_active": "on",
                "password1": "clave-gerencial-2026",
                "password2": "clave-gerencial-2026",
            },
        )
        self.assertRedirects(response, reverse("usuarios:user_list"))
        created = get_user_model().objects.get(username="gerencia")
        self.assertTrue(created.groups.filter(name="Gerente").exists())

    def test_admin_can_create_editor(self):
        self.client.force_login(self.admin)
        response = self.client.post(
            reverse("usuarios:user_create"),
            {
                "username": "editor.inventario",
                "first_name": "Usuario",
                "last_name": "Editor",
                "email": "editor@empresa.com",
                "role": "Editores",
                "is_active": "on",
                "password1": "clave-editorial-2026",
                "password2": "clave-editorial-2026",
            },
        )
        self.assertRedirects(response, reverse("usuarios:user_list"))
        created = get_user_model().objects.get(username="editor.inventario")
        self.assertTrue(created.groups.filter(name="Editores").exists())

    def test_admin_cannot_delete_own_account(self):
        self.client.force_login(self.admin)
        response = self.client.post(reverse("usuarios:user_delete", args=[self.admin.pk]))
        self.assertRedirects(response, reverse("usuarios:user_list"))
        self.assertTrue(get_user_model().objects.filter(pk=self.admin.pk).exists())
