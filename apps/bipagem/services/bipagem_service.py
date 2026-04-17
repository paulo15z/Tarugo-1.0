from typing import Any

from apps.bipagem.schemas.operacao_schema import BipagemScanInput, EstornoBipagemInput
from apps.pcp.services.pcp_interface import (
    registrar_bipagem_peca,
    estornar_bipagem_peca,
)


def registrar_bipagem(data: dict[str, Any]) -> dict[str, Any]:
    try:
        payload = BipagemScanInput(**data)
    except Exception as exc:
        return {
            'sucesso': False,
            'mensagem': 'Dados de entrada invalidos',
            'erro': str(exc),
        }

    return registrar_bipagem_peca(
        pid=payload.pid,
        codigo_peca=payload.codigo_peca,
        quantidade=payload.quantidade,
        usuario=payload.usuario,
        localizacao=payload.localizacao,
    )


def estornar_bipagem(data: dict[str, Any]) -> dict[str, Any]:
    try:
        payload = EstornoBipagemInput(**data)
    except Exception as exc:
        return {
            'sucesso': False,
            'mensagem': 'Dados de entrada invalidos',
            'erro': str(exc),
        }

    return estornar_bipagem_peca(
        pid=payload.pid,
        codigo_peca=payload.codigo_peca,
        usuario=payload.usuario,
        motivo=payload.motivo,
    )
