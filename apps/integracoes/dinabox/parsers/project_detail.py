"""
Extrai peças e módulos a partir do JSON de detalhe de projeto Dinabox.
Implementação mínima: reconhece listas comuns (woodwork, parts); expandir conforme payloads reais.
"""

from __future__ import annotations

from typing import Any


def _as_dict(detail: Any) -> dict:
    if detail is None:
        return {}
    if hasattr(detail, "model_dump"):
        return detail.model_dump()
    if isinstance(detail, dict):
        return detail
    return {}


def parse_project_detail(detail: Any) -> dict[str, Any]:
    raw = _as_dict(detail)
    pecas: list[dict[str, Any]] = []
    modulos: list[dict[str, Any]] = []

    wood = raw.get("woodwork") or raw.get("parts") or raw.get("pieces")
    if isinstance(wood, list):
        for item in wood:
            if not isinstance(item, dict):
                continue
            pecas.append(
                {
                    "descricao": str(item.get("description") or item.get("descricao") or ""),
                    "material": str(item.get("material") or item.get("material_name") or ""),
                    "quantidade": item.get("quantity") or item.get("quantidade") or 1,
                    "modulo": item.get("module") or item.get("modulo"),
                }
            )

    mods = raw.get("modules") or raw.get("modulos")
    if isinstance(mods, list):
        for m in mods:
            if isinstance(m, dict):
                modulos.append({"nome": str(m.get("name") or m.get("nome") or ""), "id": m.get("id")})

    cliente_nome = raw.get("project_customer_name") or raw.get("customer_name") or ""
    return {
        "pecas": pecas,
        "modulos": modulos,
        "metadata": {"source": "dinabox", "raw_keys": list(raw.keys())[:40]},
        "cliente": {"nome": str(cliente_nome) if cliente_nome else ""},
    }
