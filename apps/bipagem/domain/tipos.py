from enum import Enum

class StatusPeca(str, Enum):
    PENDENTE = 'PENDENTE'
    BIPADA = 'BIPADA'
    CONCLUIDA = 'CONCLUIDA'
    CANCELADA = 'CANCELADA'

MAPA_SETORES = {
    '01': {'nome': 'PINTURA', 'cor': '#c026d3'},
    '02': {'nome': 'LAMINAS/FOLHAS', 'cor': '#b45309'},
    '03': {'nome': 'RIPAS', 'cor': '#16a34a'},
    '04': {'nome': 'MONTAGEM DE CAIXA', 'cor': '#2563eb'},
    '05': {'nome': 'DUPLAGEM', 'cor': '#f97316'},
    '06': {'nome': 'PORTAS/FRENTES', 'cor': '#ec4899'},
    '07': {'nome': 'PAINEIS/PASSAGEM', 'cor': '#7c3aed'},
    '08': {'nome': 'PECAS 18MM OUTROS', 'cor': '#64748b'},
    '09': {'nome': 'PECAS 25MM OUTROS', 'cor': '#475569'},
    '10': {'nome': 'PRE-MONTAGEM', 'cor': '#06b6d4'},
    '11': {'nome': 'OUTROS', 'cor': '#0f766e'},
    '12': {'nome': 'IMPRIMIR', 'cor': '#94a3b8'},
}

MAPA_ETAPAS = {
    'COR': 'CORTE',
    'USI': 'USINAGEM',
    'FUR': 'FURACAO',
    'BOR': 'BORDA',
    'XBOR': 'BORDA MANUAL',
    'MPE': 'MONTAGEM DE PERFIS',
    'MCX': 'MONTAGEM DE CAIXA',
    'MAR': 'MARCENARIA',
    'MEL': 'MONTAGEM ELETRICA',
    'PIN': 'PINTURA',
    'PR?': 'PRE-MONTAGEM',
    'TAP': 'TAPECARIA',
    'XMAR': 'MARCENARIA ESPECIAL',
    'CQL': 'QUALIDADE',
    'EXP': 'EXPEDICAO',
}

def get_nome_setor(codigo_plano: str) -> str:
    return MAPA_SETORES.get(codigo_plano, {}).get('nome', f'SETOR {codigo_plano}' if codigo_plano else 'NAO DEFINIDO')

def get_cor_setor(codigo_plano: str) -> str:
    return MAPA_SETORES.get(codigo_plano, {}).get('cor', '#334155')

def get_nome_etapa(codigo_etapa: str | None) -> str | None:
    if not codigo_etapa:
        return None
    return MAPA_ETAPAS.get(codigo_etapa, codigo_etapa)
