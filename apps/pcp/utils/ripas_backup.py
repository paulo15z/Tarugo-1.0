import pandas as pd
import math
from typing import Tuple


BORDA_COLS = ['BORDA_FACE_FRENTE', 'BORDA_FACE_TRASEIRA', 'BORDA_FACE_LE', 'BORDA_FACE_LD']


def consolidar_ripas(df: pd.DataFrame) -> pd.DataFrame:
    """
    Consolida ripas em tiras de chapa inteira, 
    EXCETO se a peça for identificada como uma PORTA.
    """
    
    # Criamos uma máscara para identificar o que NÃO deve ser mexido (Portas)
    mask_eh_porta = df['DESCRIÇÃO DA PEÇA'].str.upper().str.contains('PORTA', na=False)

    # A regra das ripas agora tem o filtro: (Tem RIPA ou tag) E (Não é PORTA)
    mask_ripa = (
        (
            df['DESCRIÇÃO DA PEÇA'].str.upper().str.contains('RIPA', na=False) |
            df.get('OBSERVAÇÃO', pd.Series(dtype=str)).str.lower().str.contains('_ripa_', na=False) |
            df.get('OBS', pd.Series(dtype=str)).str.lower().str.contains('_ripa_', na=False)
        ) & (~mask_eh_porta)
    )

    df_ripas = df[mask_ripa].copy()
    df_resto = df[~mask_ripa].copy()

    if df_ripas.empty:
        return df

    # CONFIGURAÇÕES
    ALTURA_CHAPA = 2750.0
    ESPESSURA_SERRA = 4.0
    MARGEM_REFILO = 5.0     #testando 5 de refilo

    def to_float(val):
        try: return float(str(val).replace(',', '.'))
        except: return 0.0

    df_ripas['ALTURA_NUM'] = df_ripas['ALTURA DA PEÇA'].apply(to_float)
    df_ripas['LARGURA_NUM'] = df_ripas['LARGURA DA PEÇA'].apply(to_float)
    df_ripas['QTD_NUM'] = df_ripas['QUANTIDADE'].apply(to_float)

    novas_ripas = []

    # varias fitas
    fita_cols = [col for col in df.columns if 'FITA' in col.upper()]

    grupos = df_ripas.groupby([
        'MATERIAL DA PEÇA',
        'ESPESSURA',
        'ALTURA_NUM',
        'LARGURA_NUM',
        'LOCAL',
        *fita_cols
    ])

    for name, group in grupos:
        altura_ripa = name[2]
        largura_ripa = name[3]

        total_pecas = int(group['QTD_NUM'].sum())

        if altura_ripa <= 0:
            continue

        altura_util = ALTURA_CHAPA - MARGEM_REFILO
        altura_por_peca = altura_ripa + ESPESSURA_SERRA
        max_por_tira = int(altura_util // altura_por_peca)

        if max_por_tira <= 0:
            raise ValueError(f"Ripa com altura {altura_ripa} maior que a chapa") # espero q nunca caia nisso, temos validações no proprio 3D

        qtd_tiras = math.ceil(total_pecas / max_por_tira)

        for i in range(qtd_tiras):
            nova = group.iloc[0].copy()
            nova['DESCRIÇÃO DA PEÇA'] = "RIPA CORTE"
            nova['ALTURA DA PEÇA'] = str(int(ALTURA_CHAPA)).replace('.', ',')
            nova['LARGURA DA PEÇA'] = str(int(largura_ripa)).replace('.', ',')
            nova['QUANTIDADE'] = "1"
            nova['OBSERVAÇÃO'] = (
                f"TIRA {i+1}/{qtd_tiras} → "
                f"{total_pecas} PCS {int(altura_ripa)}mm"
            )
            novas_ripas.append(nova)

    resultado = pd.concat([df_resto, pd.DataFrame(novas_ripas)], ignore_index=True)
    return resultado