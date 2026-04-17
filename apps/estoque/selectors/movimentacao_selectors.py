# apps/estoque/selectors/movimentacao_selectors.py
from django.db.models import QuerySet

from apps.estoque.models import Movimentacao


def get_movimentacoes_recentes(produto_id: int | None = None, limite: int = 15) -> QuerySet:
    """Retorna as movimentações mais recentes (padrão para dashboard)."""
    qs = Movimentacao.objects.select_related('produto', 'usuario')

    if produto_id:
        qs = qs.filter(produto_id=produto_id)

    return qs.order_by('-criado_em')[:limite]


def listar_movimentacoes(
    produto_id: int | None = None,
    tipo: str | None = None,
    usuario_id: int | None = None,
    data_inicio=None,
    data_fim=None,
) -> QuerySet:
    """
    Selector principal de movimentações com filtros completos.
    Retorna queryset — paginação fica na view ou template.
    """
    qs = Movimentacao.objects.select_related('produto', 'usuario')

    if produto_id:
        qs = qs.filter(produto_id=produto_id)
    if tipo:
        qs = qs.filter(tipo=tipo)
    if usuario_id:
        qs = qs.filter(usuario_id=usuario_id)
    if data_inicio:
        qs = qs.filter(criado_em__gte=data_inicio)
    if data_fim:
        qs = qs.filter(criado_em__lte=data_fim)

    return qs.order_by('-criado_em')