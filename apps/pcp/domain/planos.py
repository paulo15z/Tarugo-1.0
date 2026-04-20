"""
Regras puras de determinação de plano de corte.
"""
from enum import Enum
from typing import List, Tuple, Literal
from pydantic import BaseModel
from apps.pcp.schemas.peca import PecaOperacional

class PlanoCorte(str, Enum):
    PINTURA = "01"
    LAMINA = "02"
    RIPA_CORTE = "03"
    MCX = "04"
    DUP = "05"
    MPE = "06"
    PAINEL = "07"
    PRE_MONTAGEM = "10"
    OUTROS = "11"

class DecisaoPlano(BaseModel):
    plano: PlanoCorte
    condicao_aplicada: str
    confianca: Literal["high", "medium", "low"]

class PlanoCorteCalculator:
    """Determina plano de corte com prioridade clara."""

    DECISOES_ORDENADAS: List[Tuple] = [
        # Ripas (maior prioridade)
        (lambda p: p.eh_ripa() or "_ripa_" in p.tags_markdown, PlanoCorte.RIPA_CORTE, "high", "é_ripa"),
        
        # Pintura
        (lambda p: "_pin_" in p.tags_markdown, PlanoCorte.PINTURA, "high", "tem_tag_pintura"),
        
        # Lâmina
        (lambda p: "_lamina_" in p.tags_markdown or (p.material_nome and "lamina" in p.material_nome.lower()), PlanoCorte.LAMINA, "high", "é_lamina"),
        
        # Painel / Passagem
        (lambda p: "_painel_" in p.tags_markdown or "_passagem_" in p.tags_markdown, PlanoCorte.PAINEL, "high", "é_painel_ou_passagem"),

        # Duplagem
        (lambda p: p.eh_duplada_de_verdade(), PlanoCorte.DUP, "high", "é_duplada"),
        
        # Pré-montagem
        (lambda p: "_pre_" in p.tags_markdown or "_prem_" in p.tags_markdown, PlanoCorte.PRE_MONTAGEM, "high", "tem_tag_pre"),
        
        # Portas / Frontais
        (lambda p: p.eh_porta_dinabox(), PlanoCorte.MPE, "medium", "é_porta"),
        
        # Caixaria
        (lambda p: any(kw in p.descricao.lower() for kw in ["caixa", "gaveta"]), PlanoCorte.MCX, "medium", "é_caixaria"),
        
        # Default
        (lambda p: True, PlanoCorte.OUTROS, "low", "default"),
    ]

    @staticmethod
    def determinar(peca: PecaOperacional) -> DecisaoPlano:
        # Requisito: Planos de corte devem ser calculados APÓS o roteiro.
        # O plano 04 (MCX) usa o sinal do roteiro para se definir.
        roteiro = peca.roteiro or ""

        # 1. Verificações de alta prioridade (Tags e Tipos Específicos)
        if peca.eh_ripa() or "_ripa_" in peca.tags_markdown:
            return DecisaoPlano(plano=PlanoCorte.RIPA_CORTE, condicao_aplicada="é_ripa", confianca="high")
        
        if "_pin_" in peca.tags_markdown or "PIN" in roteiro:
            return DecisaoPlano(plano=PlanoCorte.PINTURA, condicao_aplicada="tem_tag_pintura", confianca="high")
            
        if "_lamina_" in peca.tags_markdown or (peca.material_nome and "lamina" in peca.material_nome.lower()):
            return DecisaoPlano(plano=PlanoCorte.LAMINA, condicao_aplicada="é_lamina", confianca="high")
            
        if "_painel_" in peca.tags_markdown or "_passagem_" in peca.tags_markdown:
            return DecisaoPlano(plano=PlanoCorte.PAINEL, condicao_aplicada="é_painel_ou_passagem", confianca="high")

        if peca.eh_duplada_de_verdade() or "DUP" in roteiro:
            return DecisaoPlano(plano=PlanoCorte.DUP, condicao_aplicada="é_duplada", confianca="high")
            
        if "_pre_" in peca.tags_markdown or "_prem_" in peca.tags_markdown:
            return DecisaoPlano(plano=PlanoCorte.PRE_MONTAGEM, condicao_aplicada="tem_tag_pre", confianca="high")

        # 2. Verificações baseadas no Roteiro (Sinal do Roteiro)
        if "MCX" in roteiro:
            return DecisaoPlano(plano=PlanoCorte.MCX, condicao_aplicada="sinal_roteiro_mcx", confianca="high")
            
        if "MPE" in roteiro:
            return DecisaoPlano(plano=PlanoCorte.MPE, condicao_aplicada="sinal_roteiro_mpe", confianca="high")

        # 3. Fallbacks (Heurísticas de média/baixa confiança)
        if peca.eh_porta_dinabox():
            return DecisaoPlano(plano=PlanoCorte.MPE, condicao_aplicada="é_porta", confianca="medium")
            
        if any(kw in peca.descricao.lower() for kw in ["caixa", "gaveta"]):
            return DecisaoPlano(plano=PlanoCorte.MCX, condicao_aplicada="é_caixaria", confianca="medium")
        
        return DecisaoPlano(plano=PlanoCorte.OUTROS, condicao_aplicada="fallback", confianca="low")

    @staticmethod
    def determinar_batch(pecas: List[PecaOperacional]) -> List[DecisaoPlano]:
        return [PlanoCorteCalculator.determinar(p) for p in pecas]
