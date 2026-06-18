"""
Regras puras de calculo de roteiro, modulares
basicamente python
"""
from enum import Enum
from typing import List
from pydantic import BaseModel
from apps.dinabox.schemas.peca import PecaOperacional

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
    """Calculadora de roteiro industrial — versão Tarugo 1.2.

    Mudança principal nesta versão: RIPA passou a ter um caminho FIXO e
    isolado (COR -> BOR -> MAR -> [especiais] -> CQL -> EXP), que não
    depende mais de LOCAL/eh_caixaria/eh_porta_dinabox. Antes, uma ripa
    com LOCAL="Porta" caía na regra de MPE/MCX igual peça normal e ganhava
    setores que não fazem sentido pra ripa (XBOR + MPE, por exemplo).
    """

    @staticmethod
    def calcular(peca: PecaOperacional) -> Roteiro:
        # Ripa é tratada de forma totalmente separada e tem prioridade
        # máxima — igual já acontece no PlanoCorteCalculator.
        if peca.eh_ripa():
            return RoteiroCalculator._calcular_ripa(peca)

        setores = [Setor.COR]

        desc = peca.descricao.lower()
        local = (peca.modulo_nome or "").lower()
        obs = (peca.observacoes_original or "").lower()

        # 1. Duplagem
        if peca.eh_duplada:
            setores.append(Setor.DUP)

        # 2. Furação / Usinagem
        if peca.tem_furacoes():
            setores.append(Setor.FUR)

        # 3. Bordas
        if peca.tem_bordas():
            setores.append(Setor.BOR)

        # 4. Lógica de Marcenaria (MCX, MPE, MAR)
        palavras_caixaria = ["balcao", "balcão", "aereo", "aéreo", "torre", "gaveteiro", "caixa", "base", "prateleira", "divisor", "fundo", "gaveta"]
        eh_caixaria = any(p in local for p in palavras_caixaria) or any(p in desc for p in palavras_caixaria)

        eh_gaveta_local = local.strip().upper() == "GAVETA"
        industria_tem_cor_bor_fur = Setor.COR in setores or Setor.BOR in setores or Setor.FUR in setores

        eh_mpe = peca.eh_porta_dinabox() or 'frente' in desc

        eh_mar = "_painel_" in obs or "tamponamento" in desc or "regua" in desc or "régua" in desc or "painel" in desc or local.startswith('t -') or local.startswith('t-')

        if eh_gaveta_local and industria_tem_cor_bor_fur:
            setores.append(Setor.MCX)
        elif eh_caixaria and not eh_mpe and not eh_mar:
            setores.append(Setor.MCX)
        elif eh_mpe:
            setores.append(Setor.MPE)
            setores.append(Setor.MAR)
        else:
            # cobre eh_mar e o default geral de marcenaria
            setores.append(Setor.MAR)

        # 5. Especiais
        RoteiroCalculator._aplicar_especiais(setores, desc, obs)

        # 6. Finalização
        setores.extend([Setor.CQL, Setor.EXP])

        return Roteiro(setores=RoteiroCalculator._sem_duplicatas(setores))

    @staticmethod
    def _calcular_ripa(peca: PecaOperacional) -> Roteiro:
        """
        Caminho fixo de ripa: COR -> BOR (bordo no comprimento, 2 lados
        maiores) -> MAR (marceneiro) -> CQL -> EXP.

        Não tem XBOR, não tem MCX/MPE, e não é afetado por LOCAL
        (Caixa, Porta, Tamponamento, etc). Isso vale tanto pra ripa solta
        quanto pra tira consolidada — ambas passam por aqui.
        """
        setores = [Setor.COR]

        if peca.tem_furacoes():
            setores.append(Setor.FUR)

        if peca.tem_bordas():
            setores.append(Setor.BOR)

        setores.append(Setor.MAR)

        desc = peca.descricao.lower()
        obs = (peca.observacoes_original or "").lower()
        RoteiroCalculator._aplicar_especiais(setores, desc, obs)

        setores.extend([Setor.CQL, Setor.EXP])

        return Roteiro(setores=RoteiroCalculator._sem_duplicatas(setores))

    @staticmethod
    def _aplicar_especiais(setores: List[Setor], desc: str, obs: str) -> None:
        if "curvo" in desc or "curva" in desc or "_curvo_" in obs:
            setores.append(Setor.XMAR)

        if "_pin_" in obs:
            setores.append(Setor.PIN)

        if "_tap_" in obs:
            setores.append(Setor.TAP)

        if "_led_" in obs:
            setores.append(Setor.MEL)

    @staticmethod
    def _sem_duplicatas(setores: List[Setor]) -> List[Setor]:
        rota_final = []
        for s in setores:
            if s not in rota_final:
                rota_final.append(s)
        return rota_final

    @staticmethod
    def calcular_batch(pecas: List[PecaOperacional]) -> List[Roteiro]:
        return [RoteiroCalculator.calcular(p) for p in pecas]

