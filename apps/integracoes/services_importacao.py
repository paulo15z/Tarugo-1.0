from __future__ import annotations

import asyncio
from typing import Any

from asgiref.sync import sync_to_async
from django.db import transaction
from django.utils import timezone

from apps.integracoes.dinabox.schemas import (
    DinaboxProjectOperacional,
    DinaboxProjetoConcluidoEventoSchema,
    DinaboxProjetoPedidoSchema,
)
from apps.integracoes.models import DinaboxImportacaoProjeto, StatusImportacaoProjeto


class DinaboxImportacaoProjetoService:
    """Fila e worker leve para importar detalhes de projetos Dinabox para Pedidos."""

    @staticmethod
    def _montar_dados_engenharia(raw_data: dict[str, Any]) -> dict[str, Any]:
        schema = DinaboxProjetoPedidoSchema.model_validate(raw_data)
        dados = {
            "metadata": {
                "source": "dinabox",
                "project_id": schema.project_id,
                "project_status": schema.project_status,
                "project_version": schema.project_version,
                "project_description": schema.project_description,
                "project_customer_id": schema.project_customer_id,
                "project_customer_name": schema.project_customer_name,
                "project_created": schema.project_created,
                "project_last_modified": schema.project_last_modified,
                "project_author_name": schema.project_author_name,
            },
            "woodwork": schema.woodwork,
            "holes_summary": schema.holes,
            "raw_payload": raw_data,
        }
        try:
            operacional = DinaboxProjectOperacional.model_validate(raw_data)
            dados["operacional_resumo"] = operacional.get_manufacturing_summary()
            dados["woodwork"] = [item.model_dump() for item in operacional.woodwork]
            dados["holes_summary"] = [item.model_dump() for item in operacional.holes_summary]
        except Exception:
            pass
        return dados

    @staticmethod
    @transaction.atomic
    def enfileirar_importacao_por_evento(payload: dict[str, Any]) -> DinaboxImportacaoProjeto:
        schema = DinaboxProjetoConcluidoEventoSchema.model_validate(payload or {})
        return DinaboxImportacaoProjetoService.enfileirar_importacao(
            project_id=schema.project_id,
            project_customer_id=schema.project_customer_id,
            project_description=schema.project_description,
            origem=schema.origem or "projetos_concluido",
            prioridade=schema.prioridade,
        )

    @staticmethod
    @transaction.atomic
    def enfileirar_importacao(
        project_id: str,
        project_customer_id: str = "",
        project_description: str = "",
        origem: str = "projetos_concluido",
        prioridade: int = 100,
    ) -> DinaboxImportacaoProjeto:
        project_id = str(project_id or "").strip()
        if not project_id:
            raise ValueError("project_id e obrigatorio para enfileirar importacao.")

        item, created = DinaboxImportacaoProjeto.objects.get_or_create(
            project_id=project_id,
            status=StatusImportacaoProjeto.PENDENTE,
            defaults={
                "project_customer_id": str(project_customer_id or "").strip(),
                "project_description": str(project_description or "").strip(),
                "origem": origem,
                "prioridade": prioridade,
            },
        )
        if not created:
            item.project_customer_id = str(project_customer_id or item.project_customer_id or "").strip()
            item.project_description = str(project_description or item.project_description or "").strip()
            item.origem = origem or item.origem
            item.prioridade = prioridade
            item.ultimo_erro = ""
            item.save(
                update_fields=[
                    "project_customer_id",
                    "project_description",
                    "origem",
                    "prioridade",
                    "ultimo_erro",
                    "atualizado_em",
                ]
            )
        return item

    @staticmethod
    @transaction.atomic
    def _marcar_processando(item_id: int) -> DinaboxImportacaoProjeto:
        item = DinaboxImportacaoProjeto.objects.select_for_update().get(pk=item_id)
        item.status = StatusImportacaoProjeto.PROCESSANDO
        item.tentativas += 1
        item.iniciado_em = timezone.now()
        item.ultimo_erro = ""
        item.save(update_fields=["status", "tentativas", "iniciado_em", "ultimo_erro", "atualizado_em"])
        return item

    @staticmethod
    @transaction.atomic
    def _marcar_concluido(item_id: int, payload_bruto: dict[str, Any], resultado_resumo: dict[str, Any]) -> None:
        item = DinaboxImportacaoProjeto.objects.get(pk=item_id)
        item.status = StatusImportacaoProjeto.CONCLUIDO
        item.payload_bruto = payload_bruto
        item.resultado_resumo = resultado_resumo
        item.concluido_em = timezone.now()
        item.ultimo_erro = ""
        item.save(
            update_fields=[
                "status",
                "payload_bruto",
                "resultado_resumo",
                "concluido_em",
                "ultimo_erro",
                "atualizado_em",
            ]
        )

    @staticmethod
    @transaction.atomic
    def _marcar_erro(item_id: int, erro: str) -> None:
        item = DinaboxImportacaoProjeto.objects.get(pk=item_id)
        item.status = StatusImportacaoProjeto.ERRO
        item.ultimo_erro = str(erro or "").strip()[:4000]
        item.save(update_fields=["status", "ultimo_erro", "atualizado_em"])

    @staticmethod
    @transaction.atomic
    def integrar_payload_ao_pedido(raw_data: dict[str, Any]) -> dict[str, Any]:
        from apps.pedidos.selectors import AmbienteSelector
        from apps.pedidos.services import PedidoService

        schema = DinaboxProjetoPedidoSchema.model_validate(raw_data)
        ambiente = AmbienteSelector.get_ambiente_por_cliente_e_nome(
            customer_id=schema.project_customer_id,
            nome_ambiente=schema.project_description,
        )
        if ambiente is None:
            raise ValueError(
                f"Nenhum AmbientePedido encontrado para customer_id={schema.project_customer_id} "
                f"e descricao={schema.project_description}."
            )

        ambiente = PedidoService.processar_engenharia_ambiente(
            ambiente=ambiente,
            dados_engenharia=DinaboxImportacaoProjetoService._montar_dados_engenharia(raw_data),
        )
        return {
            "pedido_numero": ambiente.pedido.numero_pedido,
            "ambiente_id": ambiente.pk,
            "ambiente_nome": ambiente.nome_ambiente,
            "ambiente_status": ambiente.status,
            "project_id": schema.project_id,
            "project_customer_id": schema.project_customer_id,
            "project_description": schema.project_description,
        }

    @staticmethod
    def processar_item(item_id: int) -> dict[str, Any]:
        from apps.integracoes.dinabox.api_service import DinaboxApiService

        item = DinaboxImportacaoProjetoService._marcar_processando(item_id)
        try:
            service = DinaboxApiService()
            detail = service.get_project_detail(item.project_id)
            raw_data = detail.model_dump() if hasattr(detail, "model_dump") else dict(detail)
            resultado = DinaboxImportacaoProjetoService.integrar_payload_ao_pedido(raw_data)
            DinaboxImportacaoProjetoService._marcar_concluido(item_id, raw_data, resultado)
            return resultado
        except Exception as exc:
            DinaboxImportacaoProjetoService._marcar_erro(item_id, str(exc))
            raise

    @staticmethod
    def _buscar_payload_remoto(project_id: str) -> dict[str, Any]:
        from apps.integracoes.dinabox.api_service import DinaboxApiService

        service = DinaboxApiService()
        detail = service.get_project_detail(project_id)
        return detail.model_dump() if hasattr(detail, "model_dump") else dict(detail)

    @staticmethod
    @transaction.atomic
    def _finalizar_item_com_payload(item_id: int, raw_data: dict[str, Any]) -> dict[str, Any]:
        try:
            resultado = DinaboxImportacaoProjetoService.integrar_payload_ao_pedido(raw_data)
            DinaboxImportacaoProjetoService._marcar_concluido(item_id, raw_data, resultado)
            return resultado
        except Exception as exc:
            DinaboxImportacaoProjetoService._marcar_erro(item_id, str(exc))
            raise

    @staticmethod
    def listar_itens_pendentes(limit: int = 10) -> list[DinaboxImportacaoProjeto]:
        return list(
            DinaboxImportacaoProjeto.objects.filter(
                status__in=[StatusImportacaoProjeto.PENDENTE, StatusImportacaoProjeto.ERRO]
            ).order_by("prioridade", "criado_em")[:limit]
        )

    @staticmethod
    async def processar_fila_async(limit: int = 10, concorrencia: int = 2) -> list[dict[str, Any] | Exception]:
        itens = await sync_to_async(DinaboxImportacaoProjetoService.listar_itens_pendentes)(limit)
        semaforo = asyncio.Semaphore(max(1, concorrencia))

        async def _run(item: DinaboxImportacaoProjeto):
            async with semaforo:
                try:
                    marcado = await sync_to_async(
                        DinaboxImportacaoProjetoService._marcar_processando,
                        thread_sensitive=True,
                    )(item.pk)
                    raw_data = await asyncio.to_thread(
                        DinaboxImportacaoProjetoService._buscar_payload_remoto,
                        marcado.project_id,
                    )
                    return await sync_to_async(
                        DinaboxImportacaoProjetoService._finalizar_item_com_payload,
                        thread_sensitive=True,
                    )(item.pk, raw_data)
                except Exception as exc:
                    await sync_to_async(
                        DinaboxImportacaoProjetoService._marcar_erro,
                        thread_sensitive=True,
                    )(item.pk, str(exc))
                    return exc

        return await asyncio.gather(*[_run(item) for item in itens], return_exceptions=True)
