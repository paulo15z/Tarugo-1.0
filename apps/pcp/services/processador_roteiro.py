from __future__ import annotations

from datetime import datetime
from typing import List
import uuid

from django.core.files.base import ContentFile


from apps.pcp.domain.consolidador_ripas import ConsolidadorRipas
from apps.pcp.domain.planos import PlanoCorteCalculator
from apps.pcp.domain.roteiros import RoteiroCalculator
from apps.pcp.repositories.lote_pcp_repository import LotePCPRepository
from apps.pcp.repositories.tabela_exportacao_repository import TabelaExportacaoRepository
from apps.pcp.schemas.peca import PecaOperacional
from apps.pcp.schemas.processamento import ProcessarRoteiroOutput, ResumoPecas
from apps.pcp.utils.excel import gerar_xls_roteiro


class ProcessadorRoteiroService:
    """
    Orquestra o pipeline PCP.

    Fontes suportadas:
    - tabela padrao de exportacao (CSV/XLS/XLSX)
    - conector externo Dinabox

    Depois da entrada normalizada, todas as fontes passam pelo mesmo fluxo:
    consolidacao, roteirizacao, plano de corte, XLS final e auditoria.
    """

    def __init__(self):
        self.consolidador = ConsolidadorRipas()
        self.roteiro_calc = RoteiroCalculator()
        self.plano_calc = PlanoCorteCalculator()
        self.lote_repo = LotePCPRepository()

    def _processar_pecas(
        self,
        *,
        pecas: List[PecaOperacional],
        origem_id: str,
        cliente_nome: str,
        numero_lote: int,
        usuario=None,
        nome_saida_prefixo: str,
        origem_label: str,
    ) -> ProcessarRoteiroOutput:
        processamento_id = str(uuid.uuid4())[:8]
        total_entrada = len(pecas)

        pecas, auditorias_consolidacao = self.consolidador.consolidar(pecas)

        for peca in pecas:
            roteiro_obj = self.roteiro_calc.calcular(peca)
            peca.roteiro = roteiro_obj.como_string

            decisao = self.plano_calc.determinar(peca)
            peca.plano_corte = decisao.plano.value
            peca.lote_saida = f"{numero_lote}-{peca.plano_corte}"

        nome_saida = f"{processamento_id}_{nome_saida_prefixo}.xls"
        xls_bytes = gerar_xls_roteiro(pecas)

        processamento = self.lote_repo.salvar_processamento_com_auditoria(
            processamento_id=processamento_id,
            project_id=origem_id,
            cliente_nome=cliente_nome or "Desconhecido",
            numero_lote=numero_lote,
            pecas=pecas,
            usuario=usuario,
            auditorias_raw=auditorias_consolidacao,
            origem_label=origem_label,
        )

        arquivo_content = ContentFile(xls_bytes, name=nome_saida)
        processamento.arquivo_saida.save(nome_saida, arquivo_content, save=True)

        total_saida = len(pecas)
        ripas_geradas = sum(1 for p in pecas if "RIPA CORTE" in p.descricao.upper())
        pecas_consolidadas = max(total_entrada - total_saida + ripas_geradas, 0)

        resumo = ResumoPecas(
            total_entrada=total_entrada,
            total_saida=total_saida,
            ripas_geradas=ripas_geradas,
            pecas_consolidadas=pecas_consolidadas,
            variacao=total_saida - total_entrada,
        )

        return ProcessarRoteiroOutput(
            processamento_id=processamento_id,
            projeto_id=origem_id,
            cliente_nome=cliente_nome or "",
            data_processamento=datetime.now(),
            resumo=resumo,
            pecas_finais=[p.model_dump() for p in pecas],
            arquivo_xls=nome_saida,
            auditoria=auditorias_consolidacao,
        )

    def processar_tabela_exportacao(self, arquivo, numero_lote: int, usuario=None) -> ProcessarRoteiroOutput:
        try:
            pecas = TabelaExportacaoRepository.parsear_arquivo(arquivo)
            nome = str(getattr(arquivo, "name", "") or "tabela_exportacao")
            origem_id = nome.rsplit(".", 1)[0][:64] or "tabela_exportacao"
            return self._processar_pecas(
                pecas=pecas,
                origem_id=origem_id,
                cliente_nome="Tabela de exportacao",
                numero_lote=numero_lote,
                usuario=usuario,
                nome_saida_prefixo=f"tabela_{origem_id}",
                origem_label="Tabela",
            )
        except Exception as exc:
            raise RuntimeError(f"Falha no processamento da tabela de exportacao: {exc}") from exc

    def processar_projeto_dinabox(self, project_id: str, numero_lote: int, usuario=None) -> ProcessarRoteiroOutput:
        raise RuntimeError("Integração Dinabox está desativada.")
