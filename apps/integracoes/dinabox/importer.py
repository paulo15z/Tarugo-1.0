from datetime import datetime

from .parsers.corte import parse_corte
from .parsers.compras import parse_compras

from .schemas.projeto import ProjetoCompleto, Projeto, Cliente
from .schemas.base import Metadata


def importar_projeto(
    csv_corte: str | None = None,
    html_compras: str | None = None
) -> ProjetoCompleto:

    data = {
        "projeto": {},
        "cliente": {},
        "pecas": [],
        "insumos": []
    }

    # -------------------------
    # CORTE
    # -------------------------
    if csv_corte:
        corte_data = parse_corte(csv_corte)
        data["pecas"] = corte_data.get("pecas", [])

    # -------------------------
    # COMPRAS
    # -------------------------
    if html_compras:
        compras_data = parse_compras(html_compras)

        data["insumos"] = compras_data.get("insumos", [])

        data["projeto"].update(compras_data.get("projeto", {}))
        data["cliente"].update(compras_data.get("cliente", {}))

    # -------------------------
    # METADATA
    # -------------------------
    metadata = Metadata(
        data_importacao=datetime.now()
    )

    # -------------------------
    # BUILD FINAL
    # -------------------------
    projeto = Projeto(**data["projeto"])
    cliente = Cliente(**data["cliente"])

    return ProjetoCompleto(
        projeto=projeto,
        cliente=cliente,
        pecas=data["pecas"],
        insumos=data["insumos"],
        metadata=metadata
    )
