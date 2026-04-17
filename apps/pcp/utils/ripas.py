import pandas as pd
import math

BORDA_COLS = ['BORDA_FACE_FRENTE', 'BORDA_FACE_TRASEIRA', 'BORDA_FACE_LE', 'BORDA_FACE_LD']

ALTURA_CHAPA = 2730.0
ESPESSURA_SERRA = 4.0
MARGEM_REFILO = 5.0

DESCRICOES_EXCLUIDAS = ['arremate', 'rodapé', 'rodape', 'rodateto', 'cordão', 'cordao']


def _to_float(val):
    try:
        return float(str(val).replace(',', '.'))
    except:
        return 0.0


def _eh_descricao_excluida(desc: str) -> bool:
    desc_lower = str(desc).lower()
    return any(ex in desc_lower for ex in DESCRICOES_EXCLUIDAS)


def _eh_ripa_fonte(row) -> bool:
    """
    Considera ripa-fonte apenas quando a peça já vem praticamente como tira.
    
    Regra:
    - >= 85% da altura da chapa → fonte
    - OU >= 75% da chapa E muito estreita → fonte
    """
    altura = row['ALTURA_NUM']
    largura = row['LARGURA_NUM']

    if altura >= ALTURA_CHAPA * 0.85:
        return True

    if altura >= ALTURA_CHAPA * 0.75 and largura <= 60:
        return True

    return False


def consolidar_ripas(df: pd.DataFrame) -> pd.DataFrame:

    # =========================
    # IDENTIFICAÇÃO
    # =========================

    mask_porta = df['DESCRIÇÃO DA PEÇA'].str.upper().str.contains('PORTA', na=False)

    mask_tem_ripa = (
        df['DESCRIÇÃO DA PEÇA'].str.upper().str.contains('RIPA', na=False) |
        df.get('OBSERVAÇÃO', pd.Series(dtype=str)).str.lower().str.contains('_ripa_', na=False) |
        df.get('OBS', pd.Series(dtype=str)).str.lower().str.contains('_ripa_', na=False)
    )

    mask_excluida = mask_porta | df['DESCRIÇÃO DA PEÇA'].apply(_eh_descricao_excluida)
    mask_ripa = mask_tem_ripa & ~mask_excluida

    df_ripas = df[mask_ripa].copy()
    df_resto = df[~mask_ripa].copy()

    if df_ripas.empty:
        return df

    # =========================
    # CONVERSÕES
    # =========================

    df_ripas['ALTURA_NUM'] = df_ripas['ALTURA DA PEÇA'].apply(_to_float)
    df_ripas['LARGURA_NUM'] = df_ripas['LARGURA DA PEÇA'].apply(_to_float)
    df_ripas['QTD_NUM'] = df_ripas['QUANTIDADE'].apply(_to_float)

    # =========================
    # SEPARAÇÃO DE FLUXOS
    # =========================

    df_ripas['EH_FONTE'] = df_ripas.apply(_eh_ripa_fonte, axis=1)

    df_pequenas = df_ripas[~df_ripas['EH_FONTE']].copy()
    df_fontes = df_ripas[df_ripas['EH_FONTE']].copy()

    novas_linhas = []

    fita_cols = [col for col in df.columns if 'FITA' in col.upper()]

    chave_grupo = [
        'MATERIAL DA PEÇA',
        'ESPESSURA',
        'ALTURA_NUM',
        'LARGURA_NUM',
        'LOCAL',
        *fita_cols
    ]

    # =========================
    # FLUXO A - RIPAS PEQUENAS
    # =========================

    if not df_pequenas.empty:
        for name, group in df_pequenas.groupby(chave_grupo):

            altura_ripa = name[2]
            largura_ripa = name[3]
            total_pecas = int(group['QTD_NUM'].sum())

            if altura_ripa <= 0:
                continue

            altura_util = ALTURA_CHAPA - MARGEM_REFILO

            # serra só entre peças
            max_por_tira = int((altura_util + ESPESSURA_SERRA) // (altura_ripa + ESPESSURA_SERRA))

            if max_por_tira <= 0:
                raise ValueError(
                    f"Ripa {altura_ripa}mm maior que chapa {ALTURA_CHAPA}mm"
                )

            qtd_tiras = math.ceil(total_pecas / max_por_tira)

            for i in range(qtd_tiras):
                nova = group.iloc[0].copy()

                # tornar o ID DA PEÇA único para cada tira ---
                if 'ID DA PEÇA' in nova:
                    id_base = str(nova['ID DA PEÇA'])
                    nova['ID DA PEÇA'] = f"{id_base}-T{i+1}"
                elif 'ID' in nova:
                    id_base = str(nova['ID'])
                    nova['ID'] = f"{id_base}-T{i+1}"
                # ----------------------------------------------------------

                nova['DESCRIÇÃO DA PEÇA'] = 'RIPA CORTE'
                nova['ALTURA DA PEÇA'] = str(int(ALTURA_CHAPA))
                nova['LARGURA DA PEÇA'] = str(int(largura_ripa))
                nova['QUANTIDADE'] = '1'

                nova['OBSERVAÇÃO'] = (
                    f"TIRA {i+1}/{qtd_tiras} | "
                    f"{total_pecas} PCS {int(altura_ripa)}mm | "
                    f"{max_por_tira} pcs/tira"
                )

                novas_linhas.append(nova)

    # =========================
    # FLUXO B - RIPAS FONTE
    # =========================

    if not df_fontes.empty:
        for name, group in df_fontes.groupby(chave_grupo):

            largura_ripa = name[3]
            altura_ripa = name[2]
            total_pecas = int(group['QTD_NUM'].sum())

            nova = group.iloc[0].copy()
            nova['QUANTIDADE'] = str(total_pecas)

            # --- CORREÇÃO: Diferenciar o ID da Ripa Fonte ---
            if 'ID DA PEÇA' in nova:
                id_base = str(nova['ID DA PEÇA'])
                nova['ID DA PEÇA'] = f"{id_base}-F"
            elif 'ID' in nova:
                id_base = str(nova['ID'])
                nova['ID'] = f"{id_base}-F"
            # ------------------------------------------------

            nova['OBSERVAÇÃO'] = (
                f"RIPA FONTE | {total_pecas} PCS {int(largura_ripa)}x{int(altura_ripa)}mm"
            )

            novas_linhas.append(nova)

    # =========================
    # RESULTADO FINAL
    # =========================

    if not novas_linhas:
        return df_resto

    df_novas = pd.DataFrame(novas_linhas)

    # --- colunas auxiliares criadas para o cálculo ---
    colunas_para_remover = ['ALTURA_NUM', 'LARGURA_NUM', 'QTD_NUM', 'EH_FONTE']
    df_novas.drop(columns=colunas_para_remover, errors='ignore', inplace=True)
    # -------------------------------------------------------------------

    resultado = pd.concat([df_resto, df_novas], ignore_index=True)

    return resultado