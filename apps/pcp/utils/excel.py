from __future__ import annotations

from io import BytesIO
from typing import List, Union
import re

import pandas as pd
import xlwt

from apps.pcp.schemas.peca import PecaOperacional


COLUNAS_ROTEIRO = [
    "NOME DO CLIENTE",
    "ID DO PROJETO",
    "NOME DO PROJETO",
    "DESCRIÇÃO DO MÓDULO",
    "LOTE",
    "ID DA PEÇA",
    "REFERÊNCIA DA PEÇA",
    "DESCRIÇÃO DA PEÇA",
    "LOCAL",
    "MATERIAL DA PEÇA",
    "CÓDIGO DO MATERIAL",
    "ESPESSURA",
    "LARGURA DA PEÇA",
    "ALTURA DA PEÇA",
    "QUANTIDADE",
    "BORDA_FACE_FRENTE",
    "BORDA_FACE_TRASEIRA",
    "BORDA_FACE_LE",
    "BORDA_FACE_LD",
    "OBSERVACAO",
    "FURO A",
    "FURO B",
    "UREF",
    "PLANO",
    "ROTEIRO",
    "CONTEXTO",
]


def _pecas_para_dataframe(pecas: List[PecaOperacional]) -> pd.DataFrame:
    rows = []
    for p in pecas:
        rows.append(
            {
                "NOME DO CLIENTE": p.nome_do_cliente or "",
                "ID DO PROJETO": p.id_do_projeto or "",
                "NOME DO PROJETO": p.nome_do_projeto or "",
                "DESCRIÇÃO DO MÓDULO": p.descricao_modulo or "",
                "LOTE": p.lote_saida or "",
                "ID DA PEÇA": p.id_dinabox,
                "REFERÊNCIA DA PEÇA": p.ref_completa,
                "DESCRIÇÃO DA PEÇA": p.descricao,
                "LOCAL": p.modulo_nome or "",
                "MATERIAL DA PEÇA": p.material_nome or "",
                "CÓDIGO DO MATERIAL": p.material_id or "",
                "ESPESSURA": str(p.dimensoes.espessura or "").replace(".", ","),
                "LARGURA DA PEÇA": str(p.dimensoes.largura or "").replace(".", ","),
                "ALTURA DA PEÇA": str(p.dimensoes.altura or "").replace(".", ","),
                "QUANTIDADE": p.quantidade,
                "BORDA_FACE_FRENTE": p.bordas.get("top").nome if p.bordas and p.bordas.get("top") else "",
                "BORDA_FACE_TRASEIRA": p.bordas.get("bottom").nome if p.bordas and p.bordas.get("bottom") else "",
                "BORDA_FACE_LE": p.bordas.get("left").nome if p.bordas and p.bordas.get("left") else "",
                "BORDA_FACE_LD": p.bordas.get("right").nome if p.bordas and p.bordas.get("right") else "",
                "OBSERVACAO": p.observacoes_original or "",
                "FURO A": p.furacoes.get("A") or "",
                "FURO B": p.furacoes.get("B") or "",
                "UREF": p.uref or "",
                "PLANO": p.plano_corte or "11",
                "ROTEIRO": p.roteiro or "COR",
                "CONTEXTO": p.contexto or "",
            }
        )
    return pd.DataFrame(rows)


# Note: the experimental OPERACAO_USINAGEM implementation is currently on hold.
# We keep the helper code here for future use, but the generated XLS still uses CONTEXTO.
#
# def _operacao_usinagem(peca: PecaOperacional) -> str:
#     OPERATION_TAG_MAP = {
#         "_cava_usinada_": "CAVA45",
#         "_puxador_usinado_": "PUXADOR-01",
#         "_provencal_": "PROVENCAL_PORTA",
#         "_provencal_ripa_": "PROVENCAL_MOLDURA",
#     }
#
#     reserved_tags = set(OPERATION_TAG_MAP.keys()) | {
#         "_ripa_",
#         "_dup_",
#         "_veio_",
#         "_pin_",
#         "_tap_",
#         "_led_",
#     }
#
#     if peca.tags_markdown:
#         for tag in peca.tags_markdown:
#             normalized_tag = str(tag).strip().lower()
#             if normalized_tag in OPERATION_TAG_MAP:
#                 return OPERATION_TAG_MAP[normalized_tag]
#
#     obs = (peca.observacoes_original or "").lower()
#     for marker, code in OPERATION_TAG_MAP.items():
#         if marker in obs:
#             return code
#
#     # Detect explicit manual operation codes from tags or obs, e.g. _PUXADOR-01_, _CAVA45_
#     explicit_codes: list[str] = []
#     if peca.tags_markdown:
#         for tag in peca.tags_markdown:
#             normalized_tag = str(tag).strip("_").upper()
#             if normalized_tag and f"_{normalized_tag.lower()}_" not in reserved_tags and re.fullmatch(r"[A-Z0-9-]+", normalized_tag):
#                 explicit_codes.append(normalized_tag)
#
#     for match in re.findall(r"_([A-Z0-9-]+)_", obs.upper()):
#         if f"_{match.lower()}_" not in reserved_tags:
#             explicit_codes.append(match)
#
#     return explicit_codes[0] if explicit_codes else ""


def _write_xls(df: pd.DataFrame) -> bytes:
    workbook = xlwt.Workbook(encoding="utf-8")
    sheet = workbook.add_sheet("PCP")

    header_style = xlwt.easyxf("font: bold on; align: horiz center; pattern: pattern solid, fore_colour gray25;")

    for col_index, column in enumerate(df.columns):
        sheet.write(0, col_index, column, header_style)
        sheet.col(col_index).width = min(max(len(str(column)) + 4, 12), 40) * 256

    for row_index, (_, row) in enumerate(df.iterrows(), start=1):
        for col_index, column in enumerate(df.columns):
            value = row[column]
            if pd.isna(value):
                value = ""
            sheet.write(row_index, col_index, value)

    output = BytesIO()
    workbook.save(output)
    output.seek(0)
    return output.getvalue()


def gerar_xls_roteiro(pecas: Union[List[PecaOperacional], pd.DataFrame]) -> bytes:
    """
    Gera XLS BIFF8 no formato esperado pela operação.

    O preview do frontend usa as mesmas peças, mas este arquivo precisa manter
    todas as linhas e usar extensão/formato .xls para compatibilidade fabril.
    """
    if isinstance(pecas, pd.DataFrame):
        df = pecas.copy()
    else:
        df = _pecas_para_dataframe(pecas)

    df = df.reindex(columns=[column for column in COLUNAS_ROTEIRO if column in df.columns])
    return _write_xls(df)
