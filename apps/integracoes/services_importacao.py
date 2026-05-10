from __future__ import annotations

import asyncio
from typing import Any

from asgiref.sync import sync_to_async
from django.db import transaction
from django.utils import timezone
from pydantic import BaseModel, Field

from apps.integracoes.models import DinaboxImportacaoProjeto, StatusImportacaoProjeto

try:
    from apps.integracoes.dinabox.schemas import DinaboxProjectOperacional
except (ImportError, ModuleNotFoundError):
    DinaboxProjectOperacional = None


class ProjetoConcluidoEventoSchema(BaseModel):
    project_id: str = Field(..., min_length=1)
    project_customer_id: str = ""
    project_description: str = ""
    origem: str = "projetos_concluido"
    prioridade: int = 100


class ImportacaoProjetoService:
    """
    Fila leve de ingestao de projetos externos.

    A fila nao grava em um dominio de pedidos inexistente. Ela busca o payload
    no provedor, persiste o bruto e salva um resumo operacional quando o schema
    do conector atual conseguir validar os dados.
    """

    @staticmethod
    def _montar_resumo(raw_data: dict[str, Any], provider: str = "dinabox") -> dict[str, Any]:
        resumo: dict[str, Any] = {
            "provider": provider,
            "project_id": str(raw_data.get("project_id") or raw_data.get("id") or ""),
            "project_customer_id": str(raw_data.get("project_customer_id") or raw_data.get("customer_id") or ""),
            "project_customer_name": str(raw_data.get("project_customer_name") or raw_data.get("customer_name") or ""),
            "project_description": str(raw_data.get("project_description") or raw_data.get("description") or ""),
            "raw_keys": sorted(raw_data.keys()),
        }

        if DinaboxProjectOperacional is not None:
            try:
                operacional = DinaboxProjectOperacional.model_validate(raw_data)
                resumo["operacional"] = operacional.get_manufacturing_summary()
            except Exception as exc:
                resumo["schema_warning"] = str(exc)

        return resumo

    @staticmethod
    @transaction.atomic
    def enfileirar_importacao_por_evento(payload: dict[str, Any]) -> DinaboxImportacaoProjeto:
        schema = ProjetoConcluidoEventoSchema.model_validate(payload or {})
        return ImportacaoProjetoService.enfileirar_importacao(
            project_id=schema.project_id,
            project_customer_id=schema.project_customer_id,
            project_description=schema.project_description,
            origem=schema.origem,
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
    def _buscar_payload_remoto(project_id: str) -> dict[str, Any]:
        from apps.integracoes.dinabox.api_service import DinaboxApiService

        service = DinaboxApiService()
        detail = service.get_project_detail(project_id)
        return detail.model_dump() if hasattr(detail, "model_dump") else dict(detail)

    @staticmethod
    @transaction.atomic
    def _finalizar_item_com_payload(item_id: int, raw_data: dict[str, Any]) -> dict[str, Any]:
        resultado = ImportacaoProjetoService._montar_resumo(raw_data)
        ImportacaoProjetoService._marcar_concluido(item_id, raw_data, resultado)
        return resultado

    @staticmethod
    def processar_item(item_id: int) -> dict[str, Any]:
        item = ImportacaoProjetoService._marcar_processando(item_id)
        try:
            raw_data = ImportacaoProjetoService._buscar_payload_remoto(item.project_id)
            return ImportacaoProjetoService._finalizar_item_com_payload(item_id, raw_data)
        except Exception as exc:
            ImportacaoProjetoService._marcar_erro(item_id, str(exc))
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
        itens = await sync_to_async(ImportacaoProjetoService.listar_itens_pendentes)(limit)
        semaforo = asyncio.Semaphore(max(1, concorrencia))

        async def _run(item: DinaboxImportacaoProjeto):
            async with semaforo:
                try:
                    marcado = await sync_to_async(
                        ImportacaoProjetoService._marcar_processando,
                        thread_sensitive=True,
                    )(item.pk)
                    raw_data = await asyncio.to_thread(
                        ImportacaoProjetoService._buscar_payload_remoto,
                        marcado.project_id,
                    )
                    return await sync_to_async(
                        ImportacaoProjetoService._finalizar_item_com_payload,
                        thread_sensitive=True,
                    )(item.pk, raw_data)
                except Exception as exc:
                    await sync_to_async(
                        ImportacaoProjetoService._marcar_erro,
                        thread_sensitive=True,
                    )(item.pk, str(exc))
                    return exc

        return await asyncio.gather(*[_run(item) for item in itens], return_exceptions=True)


DinaboxImportacaoProjetoService = ImportacaoProjetoService
