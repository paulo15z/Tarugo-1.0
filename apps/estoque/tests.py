from django.contrib.auth import get_user_model
from django.test import TestCase

from apps.estoque.models import CategoriaProduto, Produto, SaldoMDF
from apps.estoque.selectors.disponibilidade_selector import (
    get_comprometimento_por_lote,
    get_necessidades_reposicao,
    get_risco_ruptura_por_lote,
    get_saldo_disponivel,
    get_saldo_fisico,
)
from apps.estoque.services.public_interface import EstoquePublicService
from apps.estoque.services.reserva_service import ReservaService


class ReservaIndustrialTestCase(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(username="tester", password="123456")
        self.categoria = CategoriaProduto.objects.create(nome="Ferragens", familia="ferragens")
        self.produto = Produto.objects.create(
            nome="Parafuso 5x50",
            sku="PAR-5X50",
            categoria=self.categoria,
            quantidade=10,
            estoque_minimo=2,
            unidade_medida="un",
        )

    def test_reserva_reduz_disponibilidade_sem_reduzir_fisico(self):
        ReservaService.criar_reserva(
            {
                "produto_id": self.produto.id,
                "quantidade": 4,
                "referencia_externa": "PED-001",
                "origem_externa": "pcp",
                "lote_pcp_id": "LOTE-001",
            },
            usuario=self.user,
        )

        self.produto.refresh_from_db()
        self.assertEqual(get_saldo_fisico(self.produto), 10)
        self.assertEqual(get_saldo_disponivel(self.produto), 6)

    def test_cancelar_reserva_recompoe_disponibilidade(self):
        reserva = ReservaService.criar_reserva(
            {
                "produto_id": self.produto.id,
                "quantidade": 3,
                "referencia_externa": "PED-002",
                "origem_externa": "pcp",
                "lote_pcp_id": "LOTE-002",
            },
            usuario=self.user,
        )

        ReservaService.cancelar_reserva(reserva.id, usuario=self.user)
        self.assertEqual(get_saldo_disponivel(self.produto), 10)

    def test_consumir_reserva_baixa_fisico_e_conclui_reserva(self):
        reserva = ReservaService.criar_reserva(
            {
                "produto_id": self.produto.id,
                "quantidade": 2,
                "referencia_externa": "PED-003",
                "origem_externa": "pcp",
                "lote_pcp_id": "LOTE-003",
            },
            usuario=self.user,
        )

        ReservaService.consumir_reserva(reserva.id, usuario=self.user)

        self.produto.refresh_from_db()
        reserva.refresh_from_db()
        self.assertEqual(reserva.status, "consumida")
        self.assertEqual(self.produto.quantidade, 8)
        self.assertEqual(get_saldo_disponivel(self.produto), 8)


class AlertaMDFPorDemandaTestCase(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(username="tester2", password="123456")
        self.categoria_mdf = CategoriaProduto.objects.create(nome="MDF", familia="mdf")
        self.produto_mdf = Produto.objects.create(
            nome="MDF Branco TX",
            sku="MDF-BRANCO-TX",
            categoria=self.categoria_mdf,
            quantidade=0,
            estoque_minimo=5,
            unidade_medida="un",
        )
        SaldoMDF.objects.create(produto=self.produto_mdf, espessura=18, quantidade=3)

    def test_mdf_sem_demanda_nao_gera_alerta(self):
        alertas = EstoquePublicService.get_alertas_baixo_estoque()
        self.assertEqual(len(alertas), 0)

    def test_mdf_com_demanda_gera_alerta(self):
        ReservaService.criar_reserva(
            {
                "produto_id": self.produto_mdf.id,
                "quantidade": 2,
                "espessura": 18,
                "referencia_externa": "LOTE-001",
                "origem_externa": "pcp",
                "lote_pcp_id": "LOTE-001",
            },
            usuario=self.user,
        )
        alertas = EstoquePublicService.get_alertas_baixo_estoque()
        self.assertEqual(len(alertas), 1)
        self.assertEqual(alertas[0]["produto_id"], self.produto_mdf.id)
        self.assertEqual(alertas[0]["espessura"], 18)


class ComprometimentoLoteTestCase(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(username="tester3", password="123456")
        self.categoria = CategoriaProduto.objects.create(nome="Ferragens", familia="ferragens")
        self.produto = Produto.objects.create(
            nome="Corredica 450",
            sku="COR-450",
            categoria=self.categoria,
            quantidade=20,
            estoque_minimo=3,
            unidade_medida="un",
        )

    def test_comprometimento_por_lote_agrega_quantidade(self):
        ReservaService.criar_reserva(
            {
                "produto_id": self.produto.id,
                "quantidade": 2,
                "origem_externa": "pcp",
                "lote_pcp_id": "LOTE-900",
            },
            usuario=self.user,
        )
        ReservaService.criar_reserva(
            {
                "produto_id": self.produto.id,
                "quantidade": 3,
                "origem_externa": "pcp",
                "lote_pcp_id": "LOTE-900",
            },
            usuario=self.user,
        )

        data = get_comprometimento_por_lote("LOTE-900")
        self.assertEqual(len(data), 1)
        self.assertEqual(data[0]["produto_id"], self.produto.id)
        self.assertEqual(data[0]["quantidade"], 5)

    def test_risco_ruptura_por_lote_identifica_quando_comprometimento_excede_disponivel(self):
        ReservaService.criar_reserva(
            {
                "produto_id": self.produto.id,
                "quantidade": 18,
                "origem_externa": "pcp",
                "lote_pcp_id": "LOTE-901",
            },
            usuario=self.user,
        )

        risco = get_risco_ruptura_por_lote("LOTE-901")
        self.assertTrue(risco["risco_ruptura"])
        self.assertTrue(len(risco["itens_criticos"]) >= 1)


class NecessidadeReposicaoTestCase(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(username="tester4", password="123456")
        self.categoria = CategoriaProduto.objects.create(nome="Ferragens", familia="ferragens")
        self.produto = Produto.objects.create(
            nome="Puxador Slim",
            sku="PUX-SLIM",
            categoria=self.categoria,
            quantidade=5,
            estoque_minimo=8,
            unidade_medida="un",
        )

    def test_lista_reposicao_sugere_quantidade_para_estoque_abaixo_do_minimo(self):
        necessidades = get_necessidades_reposicao(dias=30)
        item = next((n for n in necessidades if n["produto_id"] == self.produto.id), None)
        self.assertIsNotNone(item)
        self.assertGreaterEqual(item["quantidade_sugerida"], 3)
