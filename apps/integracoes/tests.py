from types import SimpleNamespace
from unittest.mock import MagicMock, patch

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from apps.integracoes.dinabox.client import DinaboxAPIClient


class DinaboxClientTestCase(TestCase):
    @patch("apps.integracoes.dinabox.client.requests.Session.post")
    def test_obter_token_lendo_campo_token(self, mock_post):
        fake_response = MagicMock()
        fake_response.status_code = 200
        fake_response.json.return_value = {
            "token": "abc123tokenxyz",
            "expires_in": 3600,
            "token_type": "Bearer",
        }
        mock_post.return_value = fake_response

        client = DinaboxAPIClient(
            base_url="https://www.dinabox.app",
            username="user",
            password="pass",
            verify_ssl=True,
            timeout=5,
        )
        result = client.obter_token()

        self.assertEqual(result.token, "abc123tokenxyz")
        self.assertEqual(result.expires_in, 3600)
        self.assertEqual(result.token_type, "Bearer")


class DinaboxViewsTestCase(TestCase):
    def setUp(self):
        user_model = get_user_model()
        self.user = user_model.objects.create_user(
            username="operador_integracao",
            password="senha12345",
            is_staff=True,
        )
        self.client.force_login(self.user)

    @patch("apps.integracoes.views._obter_servico_dinabox")
    def test_conectar_exibe_status_conta_tecnica(self, mock_service_factory):
        fake_service = SimpleNamespace(
            client=SimpleNamespace(
                obter_token=MagicMock(return_value=SimpleNamespace(token="abc123tokenxyz", expires_in=120, token_type="Bearer"))
            ),
            get_service_account_profile=MagicMock(
                return_value=(
                    {"user_login": "DinaboxAPI", "user_display_name": "Tarugo API", "user_email": "api@tarugo.local"},
                    {
                        "token_preview": "abc123...nxyz",
                        "user_login": "DinaboxAPI",
                        "user_display_name": "Tarugo API",
                        "user_email": "api@tarugo.local",
                    },
                )
            ),
        )
        mock_service_factory.return_value = fake_service

        response = self.client.get(reverse("integracoes:dinabox-conectar"))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Integracao Dinabox")
        self.assertContains(response, "Conta tecnica")

    @patch("apps.integracoes.views._obter_servico_dinabox")
    def test_projetos_lista_sem_sessao_usuario(self, mock_service_factory):
        fake_service = SimpleNamespace(
            list_projects=MagicMock(return_value=SimpleNamespace(projects=[], total=0, quantity=10, page=1))
        )
        mock_service_factory.return_value = fake_service

        response = self.client.get(reverse("integracoes:dinabox-projetos-list"))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Projetos Dinabox")
