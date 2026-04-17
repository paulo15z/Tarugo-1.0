import math
import re
from collections import Counter
from io import BytesIO
from typing import Any

import pandas as pd

try:
    import xlwt
except ModuleNotFoundError:  # pragma: no cover - depende do ambiente
    xlwt = None

BORDA_COLS = ['BORDA_FACE_FRENTE', 'BORDA_FACE_TRASEIRA', 'BORDA_FACE_LE', 'BORDA_FACE_LD']

ALTURA_CHAPA_BRUTA = 2750.0
REFILO_TOTAL_MM = 10.0
ESPESSURA_SERRA_MM = 4.0
ALTURA_TIRA_MAX = ALTURA_CHAPA_BRUTA - REFILO_TOTAL_MM


def _pick_column(df: pd.DataFrame, *candidates: str) -> str | None:
    for col in candidates:
        if col in df.columns:
            return col
    return None


def _series(df: pd.DataFrame, *candidates: str, default: str = '') -> pd.Series:
    col = _pick_column(df, *candidates)
    if col:
        return df[col]
    return pd.Series([default] * len(df), index=df.index)


def _row_get(row: pd.Series, *candidates: str, default: Any = '') -> Any:
    for col in candidates:
        if col in row.index:
            return row.get(col, default)
    return default


def _formatar_ripa_para_erro(row, altura_ripa: float, altura_chapa: float) -> str:
    """Monta uma mensagem clara para identificar a ripa que falhou."""
    id_peca = str(_row_get(row, 'ID DA PEÇA', 'ID DA PEÃ‡A', 'ID DA PEÃƒâ€¡A', 'ID')).strip() or 'sem ID'
    descricao = str(_row_get(row, 'DESCRIÇÃO DA PEÇA', 'DESCRIÃ‡ÃƒO DA PEÃ‡A', 'DESCRI??O DA PE?A')).strip() or 'sem descricao'
    local = str(_row_get(row, 'LOCAL')).strip() or 'sem local'
    return (
        f"Ripa invalida para consolidacao: ID {id_peca} | {descricao} | {local} | "
        f"altura {altura_ripa:.1f}mm > tira {altura_chapa:.1f}mm (com refilo). "
        "A validacao considera refilo de 10mm (5mm por lado) e serra de 4mm entre pecas."
    )


def consolidar_ripas(df: pd.DataFrame) -> pd.DataFrame:
    """Consolida ripas em tiras considerando refilo, serra e IDs unicos."""
    desc_col = _pick_column(df, 'DESCRIÇÃO DA PEÇA', 'DESCRIÃ‡ÃƒO DA PEÃ‡A', 'DESCRI??O DA PE?A')
    if not desc_col:
        raise ValueError("Coluna de descricao da peca nao encontrada para consolidacao de ripas.")

    obs_col = _pick_column(df, 'OBSERVAÇÃO', 'OBSERVAÃ‡ÃƒO', 'OBSERVA??O')
    altura_col = _pick_column(df, 'ALTURA DA PEÇA', 'ALTURA DA PEÃ‡A', 'ALTURA DA PEÃƒâ€¡A')
    largura_col = _pick_column(df, 'LARGURA DA PEÇA', 'LARGURA DA PEÃ‡A', 'LARGURA DA PEÃƒâ€¡A')
    material_col = _pick_column(df, 'MATERIAL DA PEÇA', 'MATERIAL DA PEÃ‡A', 'MATERIAL DA PE?A')

    if not altura_col or not largura_col or not material_col:
        raise ValueError("Colunas obrigatorias para consolidacao de ripas nao encontradas.")

    mask_porta = _series(df, 'LOCAL').astype(str).str.upper().str.contains('PORTA', na=False)
    mask_ripa = (
        _series(df, desc_col).astype(str).str.upper().str.contains('RIPA', na=False)
        | (_series(df, obs_col).astype(str).str.lower().str.contains('_ripa_', na=False) if obs_col else False)
        | _series(df, 'OBS').astype(str).str.lower().str.contains('_ripa_', na=False)
    )
    mask_ripa = mask_ripa & ~mask_porta

    df_ripas = df[mask_ripa].copy()
    df_resto = df[~mask_ripa].copy()

    if df_ripas.empty:
        return df

    def to_float(val):
        try:
            return float(str(val).replace(',', '.'))
        except Exception:
            return 0.0

    df_ripas['ALTURA_NUM'] = df_ripas[altura_col].apply(to_float)
    df_ripas['LARGURA_NUM'] = df_ripas[largura_col].apply(to_float)
    df_ripas['QTD_NUM'] = _series(df_ripas, 'QUANTIDADE').apply(to_float)

    novas_ripas = []
    fita_cols = [col for col in df.columns if 'FITA' in col.upper()]
    sufixo_tira_por_id_base: dict[str, int] = {}

    grupos = df_ripas.groupby([
        material_col,
        'ESPESSURA',
        'ALTURA_NUM',
        'LARGURA_NUM',
        'LOCAL',
        *fita_cols,
    ])

    for name, group in grupos:
        altura_ripa = name[2]
        largura_ripa = name[3]
        total_pecas = int(group['QTD_NUM'].sum())

        if altura_ripa <= 0:
            continue

        max_por_tira = int((ALTURA_TIRA_MAX + ESPESSURA_SERRA_MM) // (altura_ripa + ESPESSURA_SERRA_MM))

        if max_por_tira <= 0:
            raise ValueError(_formatar_ripa_para_erro(group.iloc[0], altura_ripa, ALTURA_TIRA_MAX))

        qtd_tiras = math.ceil(total_pecas / max_por_tira)
        pecas_restantes = total_pecas

        for i in range(qtd_tiras):
            nova = group.iloc[0].copy()
            pecas_nesta_tira = min(max_por_tira, pecas_restantes)
            pecas_restantes -= pecas_nesta_tira

            altura_tira_mm = (
                (pecas_nesta_tira * altura_ripa)
                + (max(pecas_nesta_tira - 1, 0) * ESPESSURA_SERRA_MM)
                + REFILO_TOTAL_MM
            )
            altura_tira_mm = min(altura_tira_mm, ALTURA_TIRA_MAX)

            id_col = _pick_column(
                pd.DataFrame(columns=nova.index),
                'ID DA PEÇA',
                'ID DA PEÃ‡A',
                'ID DA PEÃƒâ€¡A',
                'ID',
            )
            if id_col:
                id_base = str(nova[id_col]).strip() or 'SEMID'
                proximo = sufixo_tira_por_id_base.get(id_base, 0) + 1
                sufixo_tira_por_id_base[id_base] = proximo
                nova[id_col] = f"{id_base}-T{proximo}"

            nova[desc_col] = 'RIPA CORTE'
            nova[altura_col] = str(int(math.ceil(altura_tira_mm))).replace('.', ',')
            nova[largura_col] = str(int(largura_ripa)).replace('.', ',')
            nova['QUANTIDADE'] = '1'

            observacao_txt = (
                f"TIRA {i + 1}/{qtd_tiras} -> "
                f"{pecas_nesta_tira}/{total_pecas} PCS {int(altura_ripa)}mm - "
                f"{max_por_tira} pcs/tira"
            )
            if obs_col:
                nova[obs_col] = observacao_txt
            else:
                nova['OBS'] = observacao_txt

            novas_ripas.append(nova)

    resultado = pd.concat([df_resto, pd.DataFrame(novas_ripas)], ignore_index=True)
    resultado = resultado.drop(columns=['ALTURA_NUM', 'LARGURA_NUM', 'QTD_NUM'], errors='ignore')
    return resultado


def determinar_plano_de_corte(row, roteiro: str) -> str:
    """Mantem a logica de plano priorizando tags estruturadas do Dinabox."""
    desc = str(_row_get(row, 'DESCRIÇÃO DA PEÇA', 'DESCRIÃ‡ÃƒO DA PEÃ‡A', 'DESCRI??O DA PE?A')).strip().lower()
    obs = (
        str(_row_get(row, 'OBSERVAÇÃO', 'OBSERVAÃ‡ÃƒO', 'OBSERVA??O'))
        + ' '
        + str(_row_get(row, 'OBS'))
    ).strip().lower()
    local = str(_row_get(row, 'LOCAL')).strip().lower()
    material = str(_row_get(row, 'MATERIAL DA PEÇA', 'MATERIAL DA PEÃ‡A', 'MATERIAL DA PE?A')).strip().lower()

    tag_ripa = '_ripa_' in obs
    eh_porta_frontal = (
        'porta' in desc
        or 'porta' in local
        or 'frontal' in desc
        or 'frontal' in local
        or 'frente' in desc
        or 'frente' in local
    )
    eh_ripa_corte = 'ripa corte' in desc
    eh_ripa_literal = bool(re.search(r'\bripa\b', desc))
    tag_painel = '_painel_' in obs
    tag_passagem = '_passagem_' in obs
    tag_lamina = '_lamina_' in obs
    tag_pintura = '_pin_' in obs or 'PIN' in roteiro
    tag_pre_montagem = '_pre_' in obs or '_pr?_' in obs or 'PR?' in roteiro

    # Regra operacional: plano 03 para ripas reais.
    # Nao classificar "porta ripada"/frontal como ripa de corte.
    if tag_ripa or eh_ripa_corte or (eh_ripa_literal and not eh_porta_frontal):
        return '03'
    if tag_pintura:
        return '01'
    if tag_lamina or 'lamina' in material or 'l?mina' in material or 'folha' in material:
        return '02'
    if tag_painel or tag_passagem:
        return '07'
    if 'DUP' in roteiro:
        return '05'
    if tag_pre_montagem or 'pre montagem' in obs or 'prem' in obs:
        return '10'
    if 'MCX' in roteiro:
        return '04'
    if 'MPE' in roteiro:
        return '06'
    if (
        'porta' in desc or 'porta' in local
        or 'frontal' in desc or 'frontal' in local
        or 'frente' in desc or 'frente' in local
    ):
        return '06'
    return '11'


def calcular_roteiro(row) -> str:
    """Calcula roteiro com base nos campos operacionais do Dinabox."""
    desc = str(_row_get(row, 'DESCRIÇÃO DA PEÇA', 'DESCRIÃ‡ÃƒO DA PEÃ‡A', 'DESCRI??O DA PE?A')).strip().lower()
    local = str(_row_get(row, 'LOCAL')).strip().lower()
    duplagem = str(_row_get(row, 'DUPLAGEM')).strip().lower()
    furo = str(_row_get(row, 'FURO')).strip().lower()
    obs = (
        str(_row_get(row, 'OBSERVAÇÃO', 'OBSERVAÃ‡ÃƒO', 'OBSERVA??O'))
        + ' '
        + str(_row_get(row, 'OBS'))
    ).strip().lower()

    tem_borda = any(str(_row_get(row, c)).strip() not in ('', 'nan') for c in BORDA_COLS)
    tem_furo = furo not in ('', 'nan', 'none')
    tem_duplagem = duplagem not in ('', 'nan', 'none')
    tem_puxador = 'puxador' in desc or 'tampa' in desc
    eh_ripa = 'ripa' in desc or 'ripa' in local or '_ripa_' in obs
    eh_porta = 'porta' in local or 'porta' in desc
    eh_gaveta = 'gaveta' in desc or 'gaveteiro' in desc or 'gaveta' in local
    eh_caixa = 'caixa' in local
    eh_frontal = 'frontal' in local or 'frontal' in desc
    eh_tamponamento = 'tamponamento' in local
    eh_painel = '_painel_' in obs

    tem_pintura = '_pin_' in obs
    tem_tamponamento_tag = '_tamp_' in obs or '_tamponamento_' in obs
    tem_tapecar = '_tap_' in obs
    tem_eletrica = '_led_' in obs
    tem_curvo = '_curvo_' in obs

    rota = ['COR']
    if tem_duplagem and not eh_ripa:
        rota.append('DUP')
    if tem_borda:
        rota.append('BOR')
        if eh_ripa:
            rota.append('MAR')
            rota.append('XBOR')
    if tem_furo:
        rota.append('USI')
        rota.append('FUR')
    if (eh_gaveta or eh_caixa) and not eh_painel and not tem_duplagem and not tem_tamponamento_tag:
        rota.append('MCX')
    elif tem_puxador or eh_porta or eh_frontal:
        rota.append('MPE')
        rota.append('MAR')
    if eh_painel or eh_tamponamento or tem_tamponamento_tag:
        rota.append('MAR')
    if tem_pintura:
        rota.append('PIN')
    if tem_tapecar:
        rota.append('TAP')
    if tem_eletrica:
        rota.append('MEL')
    if tem_curvo:
        rota.append('XMAR')

    rota.extend(['CQL', 'EXP'])

    rota_final = []
    for etapa in rota:
        if etapa not in rota_final:
            rota_final.append(etapa)

    return ' > '.join(rota_final)


def gerar_xls_roteiro(df: pd.DataFrame) -> BytesIO:
    """Gera arquivo XLS formatado com estilos."""
    if xlwt is None:
        raise ModuleNotFoundError("xlwt nao esta instalado no ambiente.")
    wb = xlwt.Workbook(encoding='utf-8')
    ws = wb.add_sheet('Roteiro de Pecas')

    st_header = xlwt.easyxf(
        'font: bold true, colour white, height 200; '
        'pattern: pattern solid, fore_colour dark_blue; '
        'alignment: horiz centre, vert centre, wrap true; '
        'borders: left thin, right thin, top thin, bottom thin;'
    )
    st_header_rot = xlwt.easyxf(
        'font: bold true, colour white, height 200; '
        'pattern: pattern solid, fore_colour dark_yellow; '
        'alignment: horiz centre, vert centre; '
        'borders: left thin, right thin, top thin, bottom thin;'
    )
    st_data = xlwt.easyxf(
        'font: height 180; alignment: horiz centre, vert centre; '
        'borders: left thin, right thin, top thin, bottom thin;'
    )
    st_data_alt = xlwt.easyxf(
        'font: height 180; pattern: pattern solid, fore_colour ice_blue; '
        'alignment: horiz centre, vert centre; '
        'borders: left thin, right thin, top thin, bottom thin;'
    )
    st_rot = xlwt.easyxf(
        'font: bold true, height 180; pattern: pattern solid, fore_colour light_yellow; '
        'alignment: horiz centre, vert centre; '
        'borders: left thin, right thin, top thin, bottom thin;'
    )

    cols = list(df.columns)
    ws.row(0).height = 600

    for ci, col in enumerate(cols):
        st = st_header_rot if col in ('ROTEIRO', 'PLANO') else st_header
        ws.write(0, ci, col, st)
        ws.col(ci).width = 6000 if col in ('ROTEIRO', 'PLANO') else 4000

    for ri, (_, row) in enumerate(df.iterrows(), 1):
        st_base = st_data_alt if ri % 2 == 0 else st_data
        for ci, col in enumerate(cols):
            val = str(row.get(col, '')).replace('nan', '').strip()
            style = st_rot if col in ('ROTEIRO', 'PLANO') else st_base
            ws.write(ri, ci, val, style)

    buf = BytesIO()
    wb.save(buf)
    buf.seek(0)
    return buf
