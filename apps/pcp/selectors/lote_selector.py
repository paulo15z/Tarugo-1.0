"""
Consultas do PCP para expor lotes pendentes de bipagem.
"""
from __future__ import annotations

from apps.pcp.models.lote import LotePCP, PecaPCP


def list_lotes_pendentes():
    """QuerySet usado pela API para listar lotes que ainda não foram liberados."""
    return (
        LotePCP.objects
        .filter(status='pendente')
        .order_by('-data_processamento')
        .prefetch_related('ambientes__modulos')
    )


def get_lote_by_pid(pid: str) -> LotePCP | None:
    """Retorna o lote identificado pelo PID ou None."""
    try:
        return (
            LotePCP.objects
            .prefetch_related('ambientes__modulos__pecas')
            .get(pid=pid)
        )
    except LotePCP.DoesNotExist:
        return None


def get_peca_by_id(peca_id: int) -> PecaPCP | None:
    """Busca uma peça do PCP por ID, com o lote carregado para validações."""
    try:
        return (
            PecaPCP.objects
            .select_related('modulo__ambiente__lote')
            .get(id=peca_id)
        )
    except PecaPCP.DoesNotExist:
        return None
