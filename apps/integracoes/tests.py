from __future__ import annotations

import json
from unittest.mock import patch

from asgiref.sync import async_to_sync
from django.contrib.auth.models import Group, User
from django.test import TestCase, override_settings
from django.urls import reverse

from apps.comercial.models import AmbienteOrcamento, ClienteComercial, StatusClienteComercial
from apps.integracoes.models import (
    DinaboxClienteIndex,
    DinaboxImportacaoProjeto,
    StatusImportacaoProjeto,
)
from apps.integracoes.services_importacao import DinaboxImportacaoProjetoService
from apps.pedidos.domain.status import AmbienteStatus, PedidoStatus
from apps.pedidos.services import PedidoService


class DinaboxImportacaoProjetoServiceTests(TestCase):
    def setUp(self):
        self.cliente = ClienteComercial.objects.create(
            customer_id="2539544",
            numero_pedido="573",
            status=StatusClienteComercial.CONTRATO_FECHADO,
        )
        DinaboxClienteIndex.objects.create(
            customer_id="2539544",
            customer_name="1067 - THIAGO E GABY",
            customer_type="pf",
            customer_status="on",
        )
        AmbienteOrcamento.objects.create(cliente=self.cliente, nome_ambiente="COZINHA", ordem=0)
        AmbienteOrcamento.objects.create(cliente=self.cliente, nome_ambiente="SALA", ordem=1)
        self.pedido = PedidoService.criar_pedido_do_comercial(self.cliente, "573")

        self.payload = {
            "project_id": "0310366465",
            "project_status": "production",
            "project_version": 16396,
            "project_created": "09/03/2026 12:12:19",
            "project_last_modified": "09/04/2026 17:15:24",
            "project_author_name": "Lucas",
            "project_description": "COZINHA",
            "project_customer_id": "2539544",
            "project_customer_name": "1067 - THIAGO E GABY",
            "holes": [{"id": "minifix", "name": "Minifix e Tambor", "qt": 242}],
            "woodwork": [
                {
                    "id": "1762957027",
                    "mid": "M5922165",
                    "ref": "M5922165",
                    "type": "thickened",
                    "qt": 1,
                    "name": "Prateleira",
                    "width": 250,
                    "height": 1769,
                    "thickness": 30,
                    "parts": [],
                }
            ],
        }

    def test_enfileira_importacao(self):
        item = DinaboxImportacaoProjetoService.enfileirar_importacao(
            project_id="0310366465",
            project_customer_id="2539544",
            project_description="COZINHA",
        )
        self.assertEqual(item.status, StatusImportacaoProjeto.PENDENTE)
        self.assertEqual(item.project_description, "COZINHA")

    def test_integra_payload_ao_pedido(self):
        resultado = DinaboxImportacaoProjetoService.integrar_payload_ao_pedido(self.payload)

        cozinha = self.pedido.ambientes.get(nome_ambiente="COZINHA")
        sala = self.pedido.ambientes.get(nome_ambiente="SALA")
        self.pedido.refresh_from_db()
        cozinha.refresh_from_db()
        sala.refresh_from_db()

        self.assertEqual(resultado["pedido_numero"], "573")
        self.assertEqual(cozinha.status, AmbienteStatus.AGUARDANDO_PCP)
        self.assertEqual(sala.status, AmbienteStatus.PENDENTE_PROJETOS)
        self.assertEqual(self.pedido.status, PedidoStatus.ENVIADO_PARA_PROJETOS)
        self.assertEqual(cozinha.dados_engenharia["metadata"]["project_id"], "0310366465")
        self.assertIn("raw_payload", cozinha.dados_engenharia)

    def test_processa_item_com_fetch_mockado(self):
        item = DinaboxImportacaoProjetoService.enfileirar_importacao(
            project_id="0310366465",
            project_customer_id="2539544",
            project_description="COZINHA",
        )

        payload = self.payload

        class _Payload:
            def model_dump(self_inner):
                return payload

        with patch("apps.integracoes.dinabox.api_service.DinaboxApiService.get_project_detail") as mocked:
            mocked.return_value = _Payload()
            resultado = DinaboxImportacaoProjetoService.processar_item(item.pk)

        item.refresh_from_db()
        self.assertEqual(item.status, StatusImportacaoProjeto.CONCLUIDO)
        self.assertEqual(resultado["ambiente_nome"], "COZINHA")

    def test_processa_fila_async(self):
        DinaboxImportacaoProjetoService.enfileirar_importacao(
            project_id="0310366465",
            project_customer_id="2539544",
            project_description="COZINHA",
        )

        payload = self.payload

        class _Payload:
            def model_dump(self_inner):
                return payload

        with patch("apps.integracoes.dinabox.api_service.DinaboxApiService.get_project_detail", return_value=_Payload()):
            resultados = async_to_sync(DinaboxImportacaoProjetoService.processar_fila_async)(
                limit=5,
                concorrencia=1,
            )

        self.assertEqual(len(resultados), 1)
        self.assertFalse(isinstance(resultados[0], Exception))
        self.assertEqual(resultados[0]["project_description"], "COZINHA")

    def test_enfileira_importacao_por_evento(self):
        item = DinaboxImportacaoProjetoService.enfileirar_importacao_por_evento(
            {
                "project_id": "0310366465",
                "project_customer_id": "2539544",
                "project_description": "COZINHA",
                "origem": "projetos_webhook",
                "prioridade": 20,
            }
        )

        self.assertEqual(item.project_id, "0310366465")
        self.assertEqual(item.project_customer_id, "2539544")
        self.assertEqual(item.project_description, "COZINHA")
        self.assertEqual(item.origem, "projetos_webhook")
        self.assertEqual(item.prioridade, 20)


class DinaboxEnfileirarProjetoConcluidoViewTests(TestCase):
    def setUp(self):
        self.url = reverse("integracoes:dinabox-enfileirar-projeto-concluido")
        group, _ = Group.objects.get_or_create(name="PROJETOS")
        self.user = User.objects.create_user(username="projetos-user", password="123")
        self.user.groups.add(group)

    def test_endpoint_enfileira_com_usuario_projetos(self):
        payload = {
            "project_id": "0310366465",
            "project_customer_id": "2539544",
            "project_description": "COZINHA",
        }
        self.client.force_login(self.user)
        response = self.client.post(self.url, data=json.dumps(payload), content_type="application/json")

        self.assertEqual(response.status_code, 202)
        body = response.json()
        self.assertTrue(body["sucesso"])
        self.assertEqual(body["importacao"]["project_id"], "0310366465")
        self.assertEqual(DinaboxImportacaoProjeto.objects.count(), 1)

    def test_endpoint_bloqueia_sem_usuario_e_sem_token(self):
        response = self.client.post(
            self.url,
            data=json.dumps({"project_id": "0310366465"}),
            content_type="application/json",
        )

        self.assertEqual(response.status_code, 403)
        self.assertEqual(DinaboxImportacaoProjeto.objects.count(), 0)

    @override_settings(DINABOX_PROJETOS_TRIGGER_TOKEN="segredo-projetos")
    def test_endpoint_enfileira_com_token(self):
        response = self.client.post(
            self.url,
            data=json.dumps({"project_id": "0310366465", "project_description": "COZINHA"}),
            content_type="application/json",
            HTTP_X_TARUGO_TRIGGER_TOKEN="segredo-projetos",
        )

        self.assertEqual(response.status_code, 202)
        self.assertEqual(DinaboxImportacaoProjeto.objects.count(), 1)


class DinaboxImportacoesListViewTests(TestCase):
    def setUp(self):
        self.url = reverse("integracoes:dinabox-importacoes-list")
        group, _ = Group.objects.get_or_create(name="TI")
        self.user = User.objects.create_user(username="ti-user", password="123")
        self.user.groups.add(group)
        DinaboxImportacaoProjeto.objects.create(
            project_id="0310366465",
            project_customer_id="2539544",
            project_description="COZINHA",
            status=StatusImportacaoProjeto.PENDENTE,
            origem="projetos_concluido",
        )
        DinaboxImportacaoProjeto.objects.create(
            project_id="0310366466",
            project_customer_id="2539544",
            project_description="SALA",
            status=StatusImportacaoProjeto.CONCLUIDO,
            origem="worker_manual",
        )

    def test_lista_importacoes_para_usuario_autorizado(self):
        self.client.force_login(self.user)
        response = self.client.get(self.url)

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Fila de Importacoes Dinabox")
        self.assertContains(response, "0310366465")
        self.assertContains(response, "0310366466")

    def test_filtra_por_status(self):
        self.client.force_login(self.user)
        response = self.client.get(self.url, {"status": StatusImportacaoProjeto.PENDENTE})

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "0310366465")
        self.assertNotContains(response, "0310366466")
