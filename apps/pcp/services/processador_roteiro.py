from typing import List
import uuid
from datetime import datetime
from django.core.files.base import ContentFile
from django.conf import settings
from apps.integracoes.dinabox.api_service import DinaboxApiService
from apps.pcp.repositories.dinabox_repository import DinaboxRepository
from apps.pcp.repositories.lote_pcp_repository import LotePCPRepository
from apps.pcp.domain.consolidador_ripas import ConsolidadorRipas
from apps.pcp.domain.roteiros import RoteiroCalculator
from apps.pcp.domain.planos import PlanoCorteCalculator
from apps.pcp.schemas.processamento import ProcessarRoteiroOutput, ResumoPecas
from apps.pcp.schemas.peca import PecaOperacional
from apps.pcp.utils.excel import gerar_xls_roteiro

class ProcessadorRoteiroService:
    """Orquestrador final do pipeline PCP v2."""

    def __init__(self):
        self.dinabox_service = DinaboxApiService()
        self.consolidador = ConsolidadorRipas()
        self.roteiro_calc = RoteiroCalculator()
        self.plano_calc = PlanoCorteCalculator()
        self.lote_repo = LotePCPRepository()

    def processar_projeto_dinabox(
        self, 
        project_id: str, 
        numero_lote: int,
        usuario=None
    ) -> ProcessarRoteiroOutput:
        processamento_id = str(uuid.uuid4())[:8]
        try:
            # 1. Buscar da API Dinabox
            project_detail = self.dinabox_service.get_project_detail(project_id)
            raw_dict = project_detail.model_dump() if hasattr(project_detail, "model_dump") else dict(project_detail)

            # 2. Parse para domínio
            pecas: List[PecaOperacional] = DinaboxRepository.parsear_para_pecas_operacionais(raw_dict)
            total_entrada = len(pecas)

            # 3. Consolidação de ripas + auditoria
            pecas, auditorias_consolidacao = self.consolidador.consolidar(pecas)

            # 4. Roteiros e Planos
            for peca in pecas:
                # Roteiro
                roteiro_obj = self.roteiro_calc.calcular(peca)
                peca.roteiro = roteiro_obj.como_string
                
                # Plano
                decisao = self.plano_calc.determinar(peca)
                peca.plano_corte = decisao.plano.value
                
                # Lote-Plano (Requisito de fábrica)
                peca.lote_saida = f"{numero_lote}-{peca.plano_corte}"

            # 5. Gerar XLS
            nome_saida = f"{processamento_id}_projeto_{project_id}.xlsx"
            xls_bytes = gerar_xls_roteiro(pecas)

            # 6. Persistir (Histórico + Bipagem)
            processamento = self.lote_repo.salvar_processamento_com_auditoria(
                processamento_id=processamento_id,
                project_id=project_id,
                cliente_nome=raw_dict.get("project_customer_name", "Desconhecido"),
                numero_lote=numero_lote,
                pecas=pecas,
                usuario=usuario,
                auditorias_raw=auditorias_consolidacao,
            )

            # Salvar arquivo
            arquivo_content = ContentFile(xls_bytes, name=nome_saida)
            processamento.arquivo_saida.save(nome_saida, arquivo_content, save=True)

            # 7. Resumo final
            total_saida = len(pecas)
            ripas_geradas = sum(1 for p in pecas if "RIPA CORTE" in p.descricao.upper())
            
            # Cálculo de peças consolidadas
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
                projeto_id=project_id,
                cliente_nome=raw_dict.get("project_customer_name", ""),
                data_processamento=datetime.now(),
                resumo=resumo,
                pecas_finais=[p.model_dump() for p in pecas],
                arquivo_xls=nome_saida,
                auditoria=auditorias_consolidacao,
            )
        except Exception as e:
            raise RuntimeError(f"Falha no processamento do projeto {project_id}: {str(e)}") from e
