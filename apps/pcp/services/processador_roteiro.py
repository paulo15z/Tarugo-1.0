"""
Service principal do novo pipeline PCP.
Segue padrão Tarugo: Service chama Repository + Domain + Utils.
"""

from typing import List, Tuple
import uuid
from datetime import datetime

from django.conf import settings
from apps.integracoes.dinabox.api_service import DinaboxApiService
from apps.pcp.repositories.dinabox_repository import DinaboxRepository
from apps.pcp.domain.consolidador_ripas import ConsolidadorRipas
from apps.pcp.domain.roteiros import RoteiroCalculator
from apps.pcp.domain.planos import PlanoCorteCalculator
from apps.pcp.schemas.processamento import ProcessarRoteiroOutput, ResumoPecas
from apps.pcp.schemas.peca import PecaOperacional

class ProcessadorRoteiroService:
    """ 
    Dinabox API -> Parse -> consolidação -> roteiro -> plano -> output
    """

    def __init__(self):
        self.dinabox_service = DinaboxApiService()
        self.consolidador = ConsolidadorRipas()
        self.roteiro_calc = RoteiroCalculator()
        self.plano_calc = PlanoCorteCalculator()

    def processar_projeto_dinabox(
            self, project_id: str, numero_lote: int | None = None
    ) -> ProcessarRoteiroOutput:
        
        """
        agora vai
        """

        processamento_id = str(uuid.uuid4())[:8]

        try:
            # 1 - buscar dados brutos 
            project_data = self.dinabox_service.get_project_detail(project_id)
            raw_dict = project_data.model_dump() if hasattr(project_data, "model_dump") else dict(project_data)

            # 2 - parse -> dominio nosso
            pecas: List[PecaOperacional] = DinaboxRepository.parsear_para_pecas_operacionais(raw_dict)
            total_entrada = len(pecas)

            # 3 - ripas
            pecas, auditorias_consolidacao = self.consolidador.consolidar(pecas)

            # 4 - roteiros
            for peca in pecas:
                roteiro_obj = self.roteiro_calc.calcular(peca)
                peca.roteiro = roteiro_obj.como_string

            # 5 - plano de corte
            for peca in pecas:
                decisao = self.plano_calc.determinar(peca)
                peca.plano_corte = decisao.plano.value

            # 5 - resumo
            total_saida = len(pecas)
            ripas_geradas = sum(1 for p in pecas if p.eh_ripa() and "RIPA CORTE" in p.descricao)

            resumo = ResumoPecas(
                total_entrada=total_entrada,
                total_saida=total_saida,
                ripas_geradas=ripas_geradas,
                pecas_consolidadas=total_entrada - len([p for p in pecas if not p.eh_ripa()]),
                variacao=total_saida - total_entrada,
            )

            return ProcessarRoteiroOutput(
                processamento_id=processamento_id,
                projeto_id=project_id,
                cliente_nome=raw_dict.get("project_customer_name", "Cliente não informado"),
                data_processamento=datetime.now(),
                resumo=resumo,
                pecas_finais=[p.model_dump() for p in pecas],
                auditoria=auditorias_consolidacao,
            )

        except Exception as e:
            raise RuntimeError(f"Falha no processamento do projeto {project_id}: {str(e)}") from e