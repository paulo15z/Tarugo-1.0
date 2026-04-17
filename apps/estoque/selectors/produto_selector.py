# apps/estoque/selectors/produto_selector.py
from django.db.models import QuerySet, F, Sum
from apps.estoque.models import Produto


class ProdutoSelector:
    """Classe principal de selectors (mantida para o padrão Tarugo)"""

    @staticmethod
    def get_all_produtos() -> QuerySet[Produto]:
        return Produto.objects.all().order_by("nome")

    @staticmethod
    def get_produto_para_movimentacao(produto_id: int) -> Produto:
        """Lock de concorrência - usado no service"""
        return Produto.objects.select_for_update().get(id=produto_id)

    @staticmethod
    def get_historico_movimentacoes(produto_id: int) -> QuerySet:
        return Produto.objects.get(id=produto_id).movimentacoes.all()


# ===================== FUNÇÕES TOP-LEVEL (exigidas pelo __init__.py) =====================
def get_produtos_com_saldo_baixo() -> QuerySet[Produto]:
    """Mantido para compatibilidade com selectors/__init__.py e API"""
    return Produto.objects.filter(quantidade__lte=F('estoque_minimo')).order_by('nome')


def get_total_produtos_ativos() -> int:
    """Mantido para compatibilidade"""
    return Produto.objects.count()


def get_saldo_atual() -> int:
    """Saldo total de todos os produtos"""
    return Produto.objects.aggregate(total=Sum('quantidade'))['total'] or 0


def get_produtos_baixo_estoque() -> QuerySet[Produto]:
    """Mantido para compatibilidade com BaixoEstoqueView"""
    return get_produtos_com_saldo_baixo()