"""Consultas operacionais da bipagem consumindo a interface publica do PCP."""
from __future__ import annotations

from apps.pcp.services.pcp_interface import (
    get_preview_lote_operacional,
    list_lotes_operacionais,
    list_pecas_lote_operacional,
)


def get_lotes_dashboard(cliente: str = '', ambiente: str = '') -> list[dict]:
    return list_lotes_operacionais(cliente=cliente, ambiente=ambiente)


def get_lote_preview(pid: str) -> dict | None:
    return get_preview_lote_operacional(pid)


def get_pecas_do_lote(
    pid: str,
    termo: str = '',
    ambiente: str = '',
    plano: str = '',
    status: str = '',
) -> list[dict]:
    return list_pecas_lote_operacional(
        pid=pid,
        termo=termo,
        ambiente=ambiente,
        plano=plano,
        status=status,
    )
