import os
import uuid

from django.conf import settings

from apps.integracoes.dinabox.service import DinaboxService
from apps.pcp.services.lote_service import LotePCPService
from apps.pcp.services.utils import (
    calcular_roteiro,
    consolidar_ripas,
    determinar_plano_de_corte,
    gerar_xls_roteiro,
)


def _pick_col(df, *candidates):
    for col in candidates:
        if col in df.columns:
            return col
    return None


def _gerar_coluna_lote(df, lote: int):
    """Preenche a coluna LOTE com o lote informado no front e o plano gerado."""
    df = df.copy()
    df["PLANO"] = df["PLANO"].astype(str).str.strip()
    df["LOTE"] = df["PLANO"].apply(lambda plano: f"{lote}-{plano}")
    return df


def _montar_resumo_processamento(total_entrada: int, df_saida) -> dict:
    """Resume o impacto do processamento para exibir no frontend."""
    total_saida = len(df_saida)
    qtd_ripas = 0

    desc_col = _pick_col(df_saida, "DESCRIÇÃO DA PEÇA", "DESCRIÃ‡ÃƒO DA PEÃ‡A", "DESCRI??O DA PE?A")
    if desc_col:
        qtd_ripas = int(
            df_saida[desc_col]
            .astype(str)
            .str.upper()
            .eq("RIPA CORTE")
            .sum()
        )

    pecas_consolidadas = max(total_entrada - total_saida + qtd_ripas, 0)

    return {
        "total_entrada": total_entrada,
        "total_saida": total_saida,
        "ripas_geradas": qtd_ripas,
        "pecas_consolidadas": pecas_consolidadas,
        "variacao": total_saida - total_entrada,
    }


def processar_arquivo_dinabox(uploaded_file, lote: int):
    """Processa arquivo Dinabox e gera roteiro XLS + lote PCP."""
    df = DinaboxService.parse_to_dataframe(uploaded_file.read(), uploaded_file.name)

    total_entrada = len(df)
    df = consolidar_ripas(df)
    df["ROTEIRO"] = df.apply(calcular_roteiro, axis=1)
    df["PLANO"] = df.apply(lambda row: determinar_plano_de_corte(row, row["ROTEIRO"]), axis=1)
    df = _gerar_coluna_lote(df, lote)

    for col in ["LARGURA_NUM", "QTD_NUM"]:
        if col in df.columns:
            df = df.drop(columns=col)

    obs_col = _pick_col(df, "OBSERVAÇÃO", "OBSERVAÃ‡ÃƒO", "OBSERVA??O")
    if obs_col:
        df[obs_col] = df[obs_col].str.replace(
            r" *_(pin|tamp|tap|led|curvo|painel|ripa|lamina|tamponamento)_ *",
            " ",
            case=False,
            regex=True,
        ).str.strip()

    if "OBS" in df.columns:
        df["OBS"] = df["OBS"].str.replace(
            r" *_(pin|tamp|tap|led|curvo|painel|ripa|lamina|tamponamento)_ *",
            " ",
            case=False,
            regex=True,
        ).str.strip()

    pid = str(uuid.uuid4())[:8]
    nome_saida = f"{pid}_{uploaded_file.name.rsplit('.', 1)[0]}.xls"
    xls_buf = gerar_xls_roteiro(df)
    xls_bytes = xls_buf.getvalue()

    os.makedirs(settings.PCP_OUTPUTS_DIR, exist_ok=True)
    caminho = os.path.join(settings.PCP_OUTPUTS_DIR, nome_saida)
    with open(caminho, "wb") as f:
        f.write(xls_bytes)

    LotePCPService.criar_lote_a_partir_de_dataframe(
        df=df,
        pid=pid,
        nome_arquivo=uploaded_file.name,
    )

    resumo_processamento = _montar_resumo_processamento(total_entrada, df)

    return df, xls_bytes, nome_saida, pid, resumo_processamento
