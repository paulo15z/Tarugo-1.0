""" 
Regras puras de calculo de roteiro, modulares
basicamente python
"""
from enum import Enum
from typing import List
from pydantic import BaseModel
from apps.pcp.schemas.peca import PecaOperacional

#---------------------------------------------#

class Setor(str, Enum):
    # Industria
    COR = "COR"   # Seccionadora/Halter, início da indústria
    DUP = "DUP"   # Duplagem manual ou prensa
    FUR = "FUR"   # Furação / Usinagem (Unificado)
    BOR = "BOR"   # Bordo automática
    
    # Marcenaria
    XBOR = "XBOR" # Bordo manual
    MCX = "MCX"   # Montagem de caixa
    MPE = "MPE"   # Montagem de portas e frentes
    MAR = "MAR"   # Marcenaria geral / Acabamento
    XMAR = "XMAR" # Marcenaria especial / Curvos
    
    # Outros
    PIN = "PIN"   # Pintura
    TAP = "TAP"   # Tapeçaria
    MEL = "MEL"   # Elétrica / LED
    CQL = "CQL"   # Controle de Qualidade
    EXP = "EXP"   # Expedição

class Roteiro(BaseModel):
    setores: List[Setor]

    @property
    def como_string(self) -> str:
        return " -> ".join(s.value for s in self.setores) if self.setores else "NENHUM"
    
    def __str__(self):
        return self.como_string
    
class RoteiroCalculator:
    """Calculadora de roteiro industrial — versão final Tarugo 1.1."""

    @staticmethod
    def calcular(peca: PecaOperacional) -> Roteiro:
        setores = [Setor.COR]
        
        desc = peca.descricao.lower()
        local = (peca.modulo_nome or "").lower()
        obs = (peca.observacoes_original or "").lower()
        
        # 1. Duplagem (exceto ripas)
        if peca.eh_duplada and not peca.eh_ripa():
            setores.append(Setor.DUP)

        # 2. Furação / Usinagem
        if peca.tem_furacoes():
            setores.append(Setor.FUR)

        # 3. Bordas
        if peca.tem_bordas():
            setores.append(Setor.BOR)
            if peca.eh_ripa():
                setores.append(Setor.XBOR)

        # 4. Lógica de Marcenaria (MCX, MPE, MAR)
        
        # MCX: Montagem de Caixa
        palavras_caixaria = ["balcao", "balcão", "aereo", "aéreo", "torre", "gaveteiro", "caixa", "interno", "base", "lateral", "prateleira", "divisor", "fundo"]
        eh_caixaria = any(p in local for p in palavras_caixaria) or any(p in desc for p in palavras_caixaria)
        
        # MPE: Montagem de Portas e Externos
        eh_mpe = peca.eh_porta_dinabox() or 'frente' in desc
        
        # MAR: Marcenaria Geral
        eh_mar = "_painel_" in obs or "tamponamento" in desc or "regua" in desc or "régua" in desc or local.startswith('t -') or local.startswith('t-')

        if eh_caixaria and not eh_mpe and not eh_mar:
            setores.append(Setor.MCX)
        elif eh_mpe:
            setores.append(Setor.MPE)
            setores.append(Setor.MAR)
        elif eh_mar or (peca.eh_ripa() and not eh_caixaria):
            setores.append(Setor.MAR)

        # 5. Especiais
        if "curvo" in desc or "curva" in desc or "_curvo_" in obs:
            setores.append(Setor.XMAR)
            
        if "_pin_" in obs:
            setores.append(Setor.PIN)
            
        if "_tap_" in obs:
            setores.append(Setor.TAP)
            
        if "_led_" in obs:
            setores.append(Setor.MEL)

        # 6. Finalização
        setores.extend([Setor.CQL, Setor.EXP])

        # Remover duplicatas mantendo a ordem
        rota_final = []
        for s in setores:
            if s not in rota_final:
                rota_final.append(s)
                
        return Roteiro(setores=rota_final)

    @staticmethod
    def calcular_batch(pecas: List[PecaOperacional]) -> List[Roteiro]:
        return [RoteiroCalculator.calcular(p) for p in pecas]
