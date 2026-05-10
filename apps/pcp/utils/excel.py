from __future__ import annotations

from io import BytesIO
from typing import List, Union

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
    "FURO",
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
                "FURO": "SIM" if p.tem_furacoes() else "",
                "FURO A": p.furacoes.get("A") or "",
                "FURO B": p.furacoes.get("B") or "",
                "UREF": p.uref or "",
                "PLANO": p.plano_corte or "11",
                "ROTEIRO": p.roteiro or "COR",
                "CONTEXTO": p.contexto or "",
            }
        )
    return pd.DataFrame(rows)


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
