# apps/estoque/selectors/__init__.py
from .produto_selector import (
    get_produtos_com_saldo_baixo,
    get_total_produtos_ativos,
    get_saldo_atual,
    get_produtos_baixo_estoque,
)

from .movimentacao_selectors import (
    get_movimentacoes_recentes,
    listar_movimentacoes,
)
from .disponibilidade_selector import (
    get_saldo_fisico,
    get_saldo_reservado,
    get_saldo_disponivel,
    get_disponibilidade_por_produto,
    get_disponibilidade_resumida,
    listar_reservas_por_lote,
    get_comprometimento_por_lote,
    get_sinais_operacionais,
    get_necessidades_reposicao,
    get_risco_ruptura_por_lote,
)

__all__ = [
    'get_produtos_com_saldo_baixo',
    'get_total_produtos_ativos',
    'get_saldo_atual',
    'get_produtos_baixo_estoque',
    'get_movimentacoes_recentes',
    'listar_movimentacoes',
    'get_saldo_fisico',
    'get_saldo_reservado',
    'get_saldo_disponivel',
    'get_disponibilidade_por_produto',
    'get_disponibilidade_resumida',
    'listar_reservas_por_lote',
    'get_comprometimento_por_lote',
    'get_sinais_operacionais',
    'get_necessidades_reposicao',
    'get_risco_ruptura_por_lote',
]
