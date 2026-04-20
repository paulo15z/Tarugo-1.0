"""
Repository responsável por persistir lotes e peças processadas.
Separa claramente a camada de persistência do domínio.
"""
from typing import List, Dict
from django.db import transaction
from apps.pcp.models.processamento import ProcessamentoPCP, AuditoriaRoteamento
from apps.pcp.models.lote import LotePCP, AmbientePCP, ModuloPCP, PecaPCP
from apps.pcp.schemas.peca import PecaOperacional

class LotePCPRepository:
    """Persistência de lotes e auditoria."""

    @staticmethod
    @transaction.atomic
    def salvar_processamento_com_auditoria(
        processamento_id: str,
        project_id: str,
        cliente_nome: str,
        numero_lote: int,
        pecas: List[PecaOperacional],
        usuario=None,
        auditorias_raw: List[dict] | None = None
    ) -> ProcessamentoPCP:
        """
        Cria ProcessamentoPCP + salva auditorias + persiste hierarquia LotePCP.
        """
        # 1. Criar ProcessamentoPCP (Histórico)
        processamento = ProcessamentoPCP.objects.create(
            id=processamento_id,
            nome_arquivo=f"Projeto {project_id} (Pipeline v2)",
            lote=numero_lote,
            total_pecas=len(pecas),
            usuario=usuario,
        )

        # 2. Salvar auditorias de roteamento
        if auditorias_raw:
            for aud in auditorias_raw:
                AuditoriaRoteamento.objects.create(
                    processamento=processamento,
                    id_peca=aud.get("id_peca", ""),
                    tipo_transformacao=aud.get("tipo", "validacao"),
                    valor_antes=str(aud.get("valor_antes", "")),
                    valor_depois=str(aud.get("valor_depois", "")),
                    regra_aplicada=aud.get("regra_aplicada", aud.get("mensagem", "Desconhecida")),
                    confianca=aud.get("confianca", "medium"),
                )

        # 3. Persistir Hierarquia LotePCP (para Bipagem)
        lote_pcp = LotePCP.objects.create(
            pid=processamento_id,
            arquivo_original=f"Projeto {project_id}",
            cliente_nome=cliente_nome,
            cliente_id_projeto=project_id,
            status='pendente'
        )

        ambientes_cache: Dict[str, AmbientePCP] = {}
        modulos_cache: Dict[str, ModuloPCP] = {}

        for p in pecas:
            # Garantir Ambiente
            amb_nome = p.modulo_nome or "GERAL"
            if amb_nome not in ambientes_cache:
                amb, _ = AmbientePCP.objects.get_or_create(lote=lote_pcp, nome=amb_nome)
                ambientes_cache[amb_nome] = amb
            ambiente = ambientes_cache[amb_nome]

            # Garantir Modulo
            mod_nome = p.modulo_nome or "SEM MODULO"
            mod_ref = p.modulo_ref or "0"
            mod_key = f"{amb_nome}_{mod_ref}"
            if mod_key not in modulos_cache:
                mod, _ = ModuloPCP.objects.get_or_create(
                    ambiente=ambiente, 
                    nome=mod_nome,
                    codigo_modulo=mod_ref
                )
                modulos_cache[mod_key] = mod
            modulo = modulos_cache[mod_key]

            # Criar Peça
            PecaPCP.objects.create(
                modulo=modulo,
                referencia_bruta=p.ref_completa,
                codigo_modulo=p.modulo_ref,
                codigo_peca=p.id_dinabox,
                descricao=p.descricao,
                local=p.contexto,
                material=p.material_nome,
                codigo_material=p.material_id,
                comprimento=p.dimensoes.altura,
                largura=p.dimensoes.largura,
                espessura=p.dimensoes.espessura,
                quantidade_planejada=p.quantidade,
                roteiro=p.roteiro,
                plano=p.plano_corte,
                observacoes=p.observacoes_original,
                id_peca_dinabox=p.id_dinabox,
                atributos_tecnicos={
                    "tags": list(p.tags_markdown),
                    "eh_duplada": p.eh_duplada,
                    "dinabox_entity": p.dinabox_entity
                }
            )

        return processamento
