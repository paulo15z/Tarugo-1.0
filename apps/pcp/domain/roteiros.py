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
    # industria
    COR = "COR" # seccionadora/halter, inicio da industria
    DUP = "DUP" #duplagem manual ou prensa (futuro amem)
    FUR = "FUR" # maquina nova 
    BOR = "BOR" # bordo na FUTURA VI automatica

    # marcenaria
    XBOR = "XBOR" # borod manual
    MCX = "MCX" # montagme de caixa
    MPE = "MPE" # montagem de portas e frentes
    MAR = "MAR" # marcenaria artesanal
    XMAR = "XMAR" # marcenaria especial 

class Roteiro(BaseModel):
    setores: List[Setor]

    @property
    def como_string(self) -> str:
        return " -> ".join(s.value for s in self.setores) if self.setores else "NENHUM"
    
    def __str__(self):
        return self.como_string
    
class RoteiroCalculator:
    """Calculadora de roteiro industrial — versão melhorada."""

    @staticmethod
    def calcular(peca: PecaOperacional) -> Roteiro:
        setores = [Setor.COR]

        # 1. Duplagem (exceto ripas)
        if peca.eh_duplada and not peca.eh_ripa():
            setores.append(Setor.DUP)

        # 2. Furação
        if peca.tem_furacoes():
            setores.append(Setor.FUR)

        # 3. Bordas + ripas especiais
        if peca.tem_bordas():
            setores.append(Setor.BOR)
            if peca.eh_ripa():
                setores.append(Setor.XBOR)

        # 4. MPE — (usa entity da API)
        if peca.eh_porta_dinabox():
            setores.append(Setor.MPE)

        # 5. Caixaria / gavetas
        if any(kw in peca.descricao.lower() for kw in ["caixa", "gaveta", "fundo"]):
            setores.append(Setor.MCX)

        return Roteiro(setores=setores)

    @staticmethod
    def calcular_batch(pecas: List[PecaOperacional]) -> List[Roteiro]:
        return [RoteiroCalculator.calcular(p) for p in pecas]