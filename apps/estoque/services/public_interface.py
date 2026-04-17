from apps.estoque.domain.tipos import FamiliaProduto
from apps.estoque.models import Produto
from apps.estoque.selectors.disponibilidade_selector import (
    get_comprometimento_por_lote,
    get_disponibilidade_por_produto,
    get_necessidades_reposicao,
    get_risco_ruptura_por_lote,
    get_sinais_operacionais,
)


class EstoquePublicService:
    """
    Interface publica do Estoque para consumo por outros apps (ex.: PCP).
    Evita acesso direto aos models fora do dominio de estoque.
    """

    @staticmethod
    def consultar_disponibilidade(
        produto_id: int | None = None,
        sku: str | None = None,
        familia: str | None = None,
        espessura: int | None = None,
    ) -> list[dict]:
        produtos = Produto.objects.select_related("categoria").filter(ativo=True)
        if produto_id:
            produtos = produtos.filter(id=produto_id)
        if sku:
            produtos = produtos.filter(sku=sku)
        if familia:
            produtos = produtos.filter(categoria__familia=familia)

        resultado = []
        for produto in produtos:
            if produto.categoria.familia == FamiliaProduto.MDF and espessura is None:
                for esp in produto.saldos_mdf.values_list("espessura", flat=True):
                    resultado.append(get_disponibilidade_por_produto(produto, espessura=esp))
            else:
                resultado.append(get_disponibilidade_por_produto(produto, espessura=espessura))
        return resultado

    @staticmethod
    def get_alertas_baixo_estoque() -> list[dict]:
        alertas = []
        produtos = Produto.objects.select_related("categoria").filter(ativo=True)
        for produto in produtos:
            if produto.categoria.familia == FamiliaProduto.MDF:
                for esp in produto.saldos_mdf.values_list("espessura", flat=True):
                    disponibilidade = get_disponibilidade_por_produto(produto, espessura=esp)
                    tem_demanda_ativa = disponibilidade["saldo_reservado"] > 0
                    if tem_demanda_ativa and disponibilidade["saldo_disponivel"] <= produto.estoque_minimo:
                        alertas.append(disponibilidade)
            else:
                disponibilidade = get_disponibilidade_por_produto(produto)
                if disponibilidade["saldo_disponivel"] <= produto.estoque_minimo:
                    alertas.append(disponibilidade)
        return alertas

    @staticmethod
    def consultar_comprometimento_lote(lote_pcp_id: str, status: str = "ativa") -> list[dict]:
        return get_comprometimento_por_lote(lote_pcp_id=lote_pcp_id, status=status)

    @staticmethod
    def consultar_risco_ruptura_lote(lote_pcp_id: str, dias: int = 30) -> dict:
        return get_risco_ruptura_por_lote(lote_pcp_id=lote_pcp_id, dias=dias)

    @staticmethod
    def listar_sinais_operacionais(dias: int = 30) -> list[dict]:
        return get_sinais_operacionais(dias=dias)

    @staticmethod
    def listar_necessidades_reposicao(dias: int = 30) -> list[dict]:
        return get_necessidades_reposicao(dias=dias)
