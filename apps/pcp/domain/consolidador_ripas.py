"""
Consolidador das ripas - logica python sem tocar em planilha
"""

from typing import List, Tuple
from decimal import Decimal
import math
from dataclasses import dataclass
from apps.pcp.schemas.peca import PecaOperacional

@dataclass
class ConfiguracaoRipas:
    """
    configurações tecnicas para corte
    """
    altura_chapa_bruta_mm: Decimal = Decimal("2750")
    margem_refilo_mm: Decimal = Decimal("10")
    espessura_serra_mm: Decimal = Decimal("4")


class ConsolidadorRipas: 
    """
    simplesmente python sem planilha
    """

    def __init__(self, config: ConfiguracaoRipas | None = None):
        self.config = config or ConfiguracaoRipas()

    def consolidar(self, pecas: List[PecaOperacional]) -> Tuple[List[PecaOperacional], list[dict]]:
        """
        o tal do retorno completo (ripas + peças)"""

        ripas = [p for p in pecas if p.eh_ripa()]
        nao_ripas = [p for p in pecas if not p.eh_ripa()]

        if not ripas:
            return pecas, []
        
        ripas_consolidadas, auditorias = self._processar_ripas(ripas)
        return nao_ripas + ripas_consolidadas, auditorias


    def _processar_ripas(self, ripas: List[PecaOperacional]) -> Tuple[List[PecaOperacional], List[dict]]:
        from collections import defaultdict

        grupos: dict[Tuple, List[PecaOperacional]] = defaultdict(list)
        auditorias = []

        for ripa in ripas:
            chave = (
                ripa.material_id or ripa.material_nome,
                ripa.dimensoes.espessura,
                ripa.dimensoes.altura,
                ripa.dimensoes.largura
            )
            grupos[chave].append(ripa)

        pecas_finais: List[PecaOperacional] = []

        for chave, grupo in grupos.items():
            if not grupo:
                continue

            base = grupo[0]
            total_pecas = sum(p.quantidade for p in grupo)

            altura_ripa = base.dimensoes.altura or Decimal("0")
            largura_ripa = base.dimensoes.largura or Decimal("0")

            if altura_ripa <= 0:
                pecas_finais.extend(grupo)  # não dá pra consolidar
                continue

            # calculo de tiras
            altura_util = self.config.altura_chapa_bruta_mm - self.config.margem_refilo_mm
            altura_por_peca = altura_ripa + self.config.espessura_serra_mm

            if altura_por_peca > altura_util:
                pecas_finais.extend(grupo)
                auditorias.append({
                    "tipo": "consolidacao_ripa",
                    "id_peca": base.id_dinabox,
                    "mensagem": f"Ripa muito alta ({altura_ripa}mm > chapa útil)",
                    "acao": "mantida_original"
                })
                continue

            max_pecas_por_tira = math.floor(altura_util / altura_por_peca)
            if max_pecas_por_tira <= 0:
                pecas_finais.extend(grupo)
                continue
                
            qtd_tiras = math.ceil(total_pecas / max_pecas_por_tira)

            for i in range(qtd_tiras):
                nova_peca = PecaOperacional(
                    id_dinabox=f"{base.id_dinabox}-T{i+1}",
                    ref_completa=f"{base.ref_modulo} - RIPA-CORTE-T{i+1}",
                    ref_modulo=base.ref_modulo,
                    ref_peca=f"RIPA-CORTE-T{i+1}",
                    descricao="RIPA CORTE",
                    modulo_ref=base.modulo_ref,
                    modulo_nome=base.modulo_nome,
                    contexto=base.contexto,
                    quantidade=1,
                    dimensoes=base.dimensoes.model_copy(update={
                        "altura": self.config.altura_chapa_bruta_mm,
                        "largura": largura_ripa,
                    }),
                    material_id=base.material_id,
                    material_nome=base.material_nome,
                    material_com_veio=base.material_com_veio,
                    bordas=base.bordas,
                    furacoes={},
                    eh_duplada=False,
                    observacoes_original=f"TIRA {i+1}/{qtd_tiras} | {total_pecas} pcs de {int(altura_ripa)}mm",
                    tags_markdown={"_ripa_"},
                    plano_corte="03",   # RIPA_CORTE
                    roteiro="COR → BOR → XBOR",  # provisório (será recalculado depois)
                )
                pecas_finais.append(nova_peca)  

            auditorias.append({
                "tipo": "consolidacao_ripa",
                "id_peca": base.id_dinabox,
                "mensagem": f"{total_pecas} ripas → {qtd_tiras} tiras",
                "acao": "consolidada",
                "tiras_geradas": qtd_tiras
            })

        return pecas_finais, auditorias
