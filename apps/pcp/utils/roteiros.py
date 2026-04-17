import pandas as pd
import re

BORDA_COLS = ['BORDA_FACE_FRENTE', 'BORDA_FACE_TRASEIRA', 'BORDA_FACE_LE', 'BORDA_FACE_LD']


def determinar_plano_de_corte(row: pd.Series, roteiro: str) -> str:
    """Determina o plano de corte priorizando tags estruturadas do Dinabox."""
    desc = str(row.get('DESCRI??O DA PE?A', '')).strip().lower()
    obs = (str(row.get('OBSERVA??O', '')) + ' ' + str(row.get('OBS', ''))).strip().lower()
    local = str(row.get('LOCAL', '')).strip().lower()
    material = str(row.get('MATERIAL DA PE?A', '')).strip().lower()

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
    if 'porta' in desc or 'porta' in local or 'frontal' in desc or 'frontal' in local or 'frente' in desc or 'frente' in local:
        return '06'
    return '11'


def calcular_roteiro(row: pd.Series) -> str:
    """Calcula o roteiro completo da peça"""
    desc = str(row.get('DESCRIÇÃO DA PEÇA', '')).strip().lower()
    local = str(row.get('LOCAL', '')).strip().lower()
    duplagem = str(row.get('DUPLAGEM', '')).strip().lower()
    furo = str(row.get('FURO', '')).strip().lower()
    obs = (str(row.get('OBSERVAÇÃO', '')) + ' ' + str(row.get('OBS', ''))).strip().lower()

    tem_borda = any(str(row.get(c, '')).strip() not in ('', 'nan') for c in BORDA_COLS)
    tem_furo = furo not in ('', 'nan', 'none')
    tem_duplagem = duplagem not in ('', 'nan', 'none')
    tem_puxador = 'puxador' in desc or 'tampa' in desc
    
    # Lógica refinada para Ripas
    eh_ripa = 'ripa' in desc or 'ripa' in local or '_ripa_' in obs
    
    # Portas e Frentes só se não for ripa
    eh_porta = ('porta' in local or 'porta' in desc) and not eh_ripa
    eh_gaveta = 'gaveta' in desc or 'gaveteiro' in desc or 'gaveta' in local
    eh_caixa = 'caixa' in local
    eh_frontal = ('frontal' in local or 'frontal' in desc) and not eh_ripa
    
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
    elif (tem_puxador or eh_porta or eh_frontal) and not eh_ripa:
        rota.append('MPE')
        rota.append('MAR')

    # Ripas vão para Marcenaria (MAR)
    if eh_painel or eh_tamponamento or tem_tamponamento_tag or eh_ripa:
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
