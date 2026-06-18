"""
Consolidador das ripas - logica python sem tocar em planilha
"""

from typing import List, Tuple, Dict
from decimal import Decimal
import math
from dataclasses import dataclass
from apps.pcp.schemas.peca import PecaOperacional
from apps.pcp.domain.roteiros import RoteiroCalculator
from apps.pcp.domain.planos import PlanoCorteCalculator


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

    Mudanças desta versão:
    - Ripas de QUALQUER local (Caixa, Porta, Tamponamento, etc) entram no
      mesmo pool de consolidação por material+espessura+altura+largura.
      Antes, ripas de porta ficavam fora do agrupamento (~73% das ripas
      de um projeto real chegavam a ficar sem consolidar).
    - Cada tira gerada guarda, na observação, os módulos/peças de origem
      que ela contém (vínculo com a porta/módulo), em vez de só o módulo
      da primeira peça do grupo.
    - Nenhum campo de texto usa "|" (o cutplanning quebra a coluna nesse
      caractere). Separador trocado por " - " / ", ".
    - Todo caso de "não consolidei" agora gera entrada de auditoria,
      inclusive o caso em que 0 peças cabem numa tira (antes era silencioso).
    - Roteiro e plano da tira consolidada são calculados de verdade via
      RoteiroCalculator/PlanoCorteCalculator, em vez de hardcoded — evita
      a tira ficar com um roteiro "provisório" desalinhado da regra real.
    - Adicionada auditoria de conservação: soma das ripas de entrada vs
      soma representada na saída, pra pegar esse tipo de bug automaticamente
      no futuro.
    """

    def __init__(self, config: ConfiguracaoRipas | None = None):
        self.config = config or ConfiguracaoRipas()

    def consolidar(self, pecas: List[PecaOperacional]) -> Tuple[List[PecaOperacional], list[dict]]:
        """
        o tal do retorno completo (ripas + peças)
        """
        ripas = [p for p in pecas if p.eh_ripa()]
        nao_ripas = [p for p in pecas if not p.eh_ripa()]

        if not ripas:
            return pecas, []

        ripas_consolidadas, auditorias = self._processar_ripas(ripas)
        auditorias.append(self._verificar_conservacao(ripas, ripas_consolidadas))

        return nao_ripas + ripas_consolidadas, auditorias

    def _processar_ripas(self, ripas: List[PecaOperacional]) -> Tuple[List[PecaOperacional], List[dict]]:
        from collections import defaultdict

        grupos: Dict[Tuple, List[PecaOperacional]] = defaultdict(list)
        auditorias: List[dict] = []

        for ripa in ripas:
            # Importante: a chave NÃO inclui LOCAL/módulo de propósito.
            # Ripas de Caixa e de Porta com mesma dimensão/material
            # compartilham a mesma chapa - é isso que dá o aproveitamento.
            chave = (
                ripa.material_id or ripa.material_nome,
                ripa.dimensoes.espessura,
                ripa.dimensoes.altura,
                ripa.dimensoes.largura,
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
                pecas_finais.extend(grupo)
                auditorias.append({
                    "tipo": "consolidacao_ripa",
                    "id_peca": base.id_dinabox,
                    "mensagem": "Ripa sem altura definida - mantida sem consolidar",
                    "acao": "mantida_original",
                })
                continue

            altura_util = self.config.altura_chapa_bruta_mm - self.config.margem_refilo_mm
            altura_por_peca = altura_ripa + self.config.espessura_serra_mm

            if altura_por_peca > altura_util:
                pecas_finais.extend(grupo)
                auditorias.append({
                    "tipo": "consolidacao_ripa",
                    "id_peca": base.id_dinabox,
                    "mensagem": f"Ripa muito alta ({altura_ripa}mm > chapa útil de {altura_util}mm)",
                    "acao": "mantida_original",
                })
                continue

            max_pecas_por_tira = math.floor(altura_util / altura_por_peca)
            if max_pecas_por_tira <= 0:
                # Antes esse caso era silencioso (sem auditoria) - corrigido.
                pecas_finais.extend(grupo)
                auditorias.append({
                    "tipo": "consolidacao_ripa",
                    "id_peca": base.id_dinabox,
                    "mensagem": f"Nenhuma ripa de {altura_ripa}mm cabe na chapa útil de {altura_util}mm",
                    "acao": "mantida_original",
                })
                continue

            qtd_tiras = math.ceil(total_pecas / max_pecas_por_tira)

            tiras_geradas = self._distribuir_em_tiras(
                grupo, qtd_tiras, max_pecas_por_tira, altura_ripa, largura_ripa
            )
            pecas_finais.extend(tiras_geradas)

            modulos_no_grupo = sorted({p.ref_modulo for p in grupo if p.ref_modulo})
            auditorias.append({
                "tipo": "consolidacao_ripa",
                "id_peca": base.id_dinabox,
                "mensagem": f"{total_pecas} ripas ({', '.join(modulos_no_grupo)}) -> {qtd_tiras} tiras",
                "acao": "consolidada",
                "tiras_geradas": qtd_tiras,
                "modulos_envolvidos": modulos_no_grupo,
            })

        return pecas_finais, auditorias

    def _distribuir_em_tiras(
        self,
        grupo: List[PecaOperacional],
        qtd_tiras: int,
        max_pecas_por_tira: int,
        altura_ripa: Decimal,
        largura_ripa: Decimal,
    ) -> List[PecaOperacional]:
        """
        Distribui as peças originais entre as tiras na ordem em que elas
        aparecem no grupo, registrando em cada tira exatamente quais
        módulos/peças de origem (ex: portas) ela carrega.
        """
        base = grupo[0]
        fila = list(grupo)
        idx_peca = 0
        usado_da_peca_atual = 0

        tiras: List[PecaOperacional] = []

        for i in range(qtd_tiras):
            vagas = max_pecas_por_tira
            contribuintes: List[Tuple[str, str, int]] = []  # (id_dinabox, ref_modulo, qtd_usada)

            while vagas > 0 and idx_peca < len(fila):
                peca_atual = fila[idx_peca]
                disponivel = peca_atual.quantidade - usado_da_peca_atual
                usar = min(disponivel, vagas)

                contribuintes.append((peca_atual.id_dinabox, peca_atual.ref_modulo, usar))
                usado_da_peca_atual += usar
                vagas -= usar

                if usado_da_peca_atual >= peca_atual.quantidade:
                    idx_peca += 1
                    usado_da_peca_atual = 0

            total_pcs_tira = sum(c[2] for c in contribuintes)
            modulos_distintos = sorted({c[1] for c in contribuintes if c[1]})
            obs_modulos = ", ".join(modulos_distintos) if modulos_distintos else "N/D"

            # nada de "|" aqui - separador é " - " e ", "
            observacao = (
                f"TIRA {i + 1}/{qtd_tiras} - {total_pcs_tira} pcs de {int(altura_ripa)}mm "
                f"- ORIGEM: {obs_modulos}"
            )

            nova_peca = PecaOperacional(
                id_dinabox=f"{base.id_dinabox}-T{i + 1}",
                ref_completa=f"{base.ref_modulo} - RIPA-CORTE-T{i + 1}",
                ref_modulo=base.ref_modulo,
                ref_peca=f"RIPA-CORTE-T{i + 1}",
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
                observacoes_original=observacao,
                tags_markdown={"_ripa_"},
                plano_corte=None,
                roteiro=None,
            )

            # Calculados de verdade (não hardcoded) - assim a tira segue a
            # MESMA regra fixa de roteiro de ripa (COR -> BOR -> MAR -> ...)
            # e não fica desalinhada caso a regra mude no futuro.
            nova_peca.roteiro = str(RoteiroCalculator.calcular(nova_peca))
            nova_peca.plano_corte = PlanoCorteCalculator.determinar(nova_peca).plano.value

            tiras.append(nova_peca)

        return tiras

    def _verificar_conservacao(
        self, ripas_originais: List[PecaOperacional], resultado: List[PecaOperacional]
    ) -> dict:
        """
        Confere se a quantidade total de ripas de entrada bate com a
        quantidade representada na saída (tiras consolidadas + peças
        mantidas como estavam). É essa verificação que pega, de forma
        automática, qualquer ripa que esteja ficando de fora silenciosamente
        - como aconteceu com as ripas de Porta antes deste conserto.
        """
        total_entrada = sum(p.quantidade for p in ripas_originais)

        total_saida = 0
        for p in resultado:
            if p.descricao == "RIPA CORTE":
                texto = p.observacoes_original or ""
                try:
                    total_saida += int(texto.split(" - ")[1].split(" pcs")[0])
                except (IndexError, ValueError):
                    pass
            else:
                total_saida += p.quantidade

        bateu = total_entrada == total_saida
        return {
            "tipo": "verificacao_conservacao",
            "mensagem": f"Entrada: {total_entrada} ripas - Saída representada: {total_saida} ripas",
            "acao": "ok" if bateu else "DIVERGENCIA_DETECTADA",
        }