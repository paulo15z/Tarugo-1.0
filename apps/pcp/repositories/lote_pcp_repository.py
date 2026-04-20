"""
Repository responsável por persistir lotes e peças processadas.
Separa claramente a camada de persistência do domínio.
"""

from typing import List, Optional
from apps.pcp.models.processamento import ProcessamentoPCP, AuditoriaRoteamento
from apps.pcp.schemas.peca import PecaOperacional


class LotePCPRepository:
    """Persistência de lotes e auditoria."""

    @staticmethod
    def salvar_processamento_com_auditoria(
        processamento_id: str,
        project_id: str,
        cliente_nome: str,
        numero_lote: int,
        pecas: List[PecaOperacional],
        usuario=None,
        auditorias_raw: List[dict] | None = None
    ) -> ProcessamentoPCP:
        """Cria ProcessamentoPCP + salva auditorias."""

        processamento = ProcessamentoPCP.objects.create(
            id=processamento_id,
            nome_arquivo=f"Projeto {project_id} (Pipeline v2)",
            lote=numero_lote,
            total_pecas=len(pecas),
            usuario=usuario,
        )

        # Salvar auditorias (se existirem)
        if auditorias_raw:
            for aud in auditorias_raw:
                AuditoriaRoteamento.objects.create(
                    processamento=processamento,
                    id_peca=aud.get("id_peca", ""),
                    tipo_transformacao=aud.get("tipo", "validacao"),
                    valor_antes=aud.get("valor_antes", ""),
                    valor_depois=aud.get("valor_depois", ""),
                    regra_aplicada=aud.get("regra_aplicada", "Desconhecida"),
                    confianca=aud.get("confianca", "medium"),
                )

        return processamento