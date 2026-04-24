"""
Gerador de XLS para o novo pipeline PCP.
Recebe List[PecaOperacional] e gera arquivo compatível com a operação atual.
"""
from io import BytesIO
import pandas as pd
from typing import List, Union
from apps.pcp.schemas.peca import PecaOperacional

def gerar_xls_roteiro(pecas: Union[List[PecaOperacional], pd.DataFrame]) -> bytes:
    """
    Converte lista de PecaOperacional ou DataFrame → Excel no formato esperado pelo cutplanning.
    Mantém compatibilidade com colunas antigas e usa vírgula como separador decimal.
    """
    if isinstance(pecas, pd.DataFrame):
        df = pecas.copy()
    else:
        rows = []
        for p in pecas:
            row = {
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
        rows.append(row)
        df = pd.DataFrame(rows)
    
    # Ordenação recomendada para a fábrica
    colunas_ordem = [
        "LOTE", "ID DA PEÇA", "REFERÊNCIA DA PEÇA", "DESCRIÇÃO DA PEÇA", "LOCAL",
        "MATERIAL DA PEÇA", "CÓDIGO DO MATERIAL", "ESPESSURA",
        "LARGURA DA PEÇA", "ALTURA DA PEÇA", "QUANTIDADE",
        "BORDA_FACE_FRENTE", "BORDA_FACE_TRASEIRA", "BORDA_FACE_LE", "BORDA_FACE_LD",
        "FURO", "FURO A", "FURO B", "UREF", "PLANO", "ROTEIRO", "CONTEXTO"
    ]
    
    df = df.reindex(columns=[c for c in colunas_ordem if c in df.columns])

    output = BytesIO()
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        df.to_excel(writer, index=False, sheet_name="PCP")
    
    output.seek(0)
    return output.getvalue()
