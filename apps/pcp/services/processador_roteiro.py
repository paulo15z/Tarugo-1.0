"""
Service principal do novo pipeline PCP — Fase 4 completa.
"""

from typing import List, Tuple
import uuid
from datetime import datetime
from django.core.files.base import ContentFile
from django.conf import settings

from apps.integracoes.dinabox.api_service import DinaboxApiService
from apps.pcp.repositories.dinabox_repository import DinaboxRepository
from apps.pcp.domain.consolidador_ripas import ConsolidadorRipas
from apps.pcp.domain.roteiros import RoteiroCalculator
from apps.pcp.domain.planos import PlanoCorteCalculator
from apps.pcp.schemas.processamento import ProcessarRoteiroOutput, ResumoPecas
from apps.pcp.schemas.peca import PecaOperacional
from apps.pcp.models.processamento import ProcessamentoPCP   # model existente
from apps.pcp.utils.excel import gerar_xls_roteiro


class ProcessadorRoteiroService:
    def __init__(self):
        self.dinabox_service = DinaboxApiService()
        self.consolidador = ConsolidadorRipas()
        self.roteiro_calc = RoteiroCalculator()
        self.plano_calc = PlanoCorteCalculator()

    def processar_projeto_dinabox(
        self, project_id: str, numero_lote: int | None = None
    ) -> ProcessarRoteiroOutput:
        processamento_id = str(uuid.uuid4())[:8]

        try:
            # 1. Buscar dados
            project_detail = self.dinabox_service.get_project_detail(project_id)
            raw_dict = project_detail.model_dump() if hasattr(project_detail, "model_dump") else dict(project_detail)

            # 2. Parse
            pecas: List[PecaOperacional] = DinaboxRepository.parsear_para_pecas_operacionais(raw_dict)
            total_entrada = len(pecas)

            # 3. Consolidação de ripas
            pecas, auditorias = self.consolidador.consolidar(pecas)

            # 4. Roteiros
            for peca in pecas:
                roteiro_obj = self.roteiro_calc.calcular(peca)
                peca.roteiro = roteiro_obj.como_string

            # 5. Planos
            for peca in pecas:
                decisao = self.plano_calc.determinar(peca)
                peca.plano_corte = decisao.plano.value

            # 6. Gerar XLS
            nome_saida = f"{processamento_id}_projeto_{project_id}.xlsx"
            xls_bytes = gerar_xls_roteiro(pecas, nome_saida)

            # 7. Salvar no banco (model existente)
            processamento = ProcessamentoPCP.objects.create(
                id=processamento_id,
                nome_arquivo=f"Projeto {project_id} (Novo Pipeline)",
                lote=numero_lote or 999,   # temporário — ajustar depois
                total_pecas=len(pecas),
                usuario=None,  # será preenchido na view
            )

            arquivo_content = ContentFile(xls_bytes, name=nome_saida)
            processamento.arquivo_saida.save(nome_saida, arquivo_content, save=True)

            # 8. Resumo
            total_saida = len(pecas)
            ripas_geradas = sum(1 for p in pecas if "RIPA CORTE" in p.descricao.upper())

            resumo = ResumoPecas(
                total_entrada=total_entrada,
                total_saida=total_saida,
                ripas_geradas=ripas_geradas,
                pecas_consolidadas=total_entrada - sum(1 for p in pecas if not p.eh_ripa()),
                variacao=total_saida - total_entrada,
            )

            return ProcessarRoteiroOutput(
                processamento_id=processamento_id,
                projeto_id=project_id,
                cliente_nome=raw_dict.get("project_customer_name", "Desconhecido"),
                data_processamento=datetime.now(),
                resumo=resumo,
                pecas_finais=[p.model_dump() for p in pecas],
                arquivo_xls=nome_saida,
                auditoria=auditorias,
            )

        except Exception as e:
            raise RuntimeError(f"Erro no processamento do projeto {project_id}: {str(e)}") from e