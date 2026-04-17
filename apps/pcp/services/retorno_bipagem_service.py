from __future__ import annotations

import csv
import io
from typing import Any

from django.db.models import Sum

from apps.bipagem.models import EventoBipagem
from apps.pcp.models.lote import LotePCP, PecaPCP
from apps.pcp.models.processamento import ProcessamentoPCP


class RetornoBipagemService:
    @staticmethod
    def obter_retorno_lote(pid: str, preview_limit: int = 40, log_limit: int = 120) -> dict[str, Any] | None:
        processamento = ProcessamentoPCP.objects.filter(id=pid).first()
        if not processamento:
            return None

        lote = LotePCP.objects.filter(pid=pid).first()
        pecas_qs = (
            PecaPCP.objects
            .filter(modulo__ambiente__lote__pid=pid)
            .select_related("modulo__ambiente")
            .order_by("modulo__ambiente__nome", "modulo__nome", "codigo_peca")
        )
        pecas = list(pecas_qs)

        eventos_qs = (
            EventoBipagem.objects
            .filter(peca__modulo__ambiente__lote__pid=pid)
            .select_related("peca__modulo__ambiente")
            .order_by("-momento")
        )

        total_planejada = sum(p.quantidade_planejada for p in pecas)
        total_produzida = sum(min(p.quantidade_produzida, p.quantidade_planejada) for p in pecas)
        total_faltante = sum(max(p.quantidade_planejada - p.quantidade_produzida, 0) for p in pecas)
        pecas_finalizadas = sum(1 for p in pecas if p.quantidade_produzida >= p.quantidade_planejada and p.quantidade_planejada > 0)
        pecas_em_producao = sum(1 for p in pecas if 0 < p.quantidade_produzida < p.quantidade_planejada)
        pecas_pendentes = sum(1 for p in pecas if p.quantidade_produzida <= 0)
        percentual = round((total_produzida / total_planejada * 100), 1) if total_planejada else 0.0

        agregados_eventos = eventos_qs.values("tipo").annotate(total=Sum("quantidade"))
        total_bipagens = 0
        total_estornos = 0
        total_eventos = eventos_qs.count()
        for item in agregados_eventos:
            if item["tipo"] == "BIPAGEM":
                total_bipagens = int(item["total"] or 0)
            elif item["tipo"] == "ESTORNO":
                total_estornos = int(item["total"] or 0)

        preview = [RetornoBipagemService._to_preview_peca(peca) for peca in pecas[:preview_limit]]
        log = [RetornoBipagemService._to_log_evento(evento) for evento in list(eventos_qs[:log_limit])]

        return {
            "lote": {
                "pid": processamento.id,
                "lote": processamento.lote,
                "nome_arquivo": processamento.nome_arquivo,
                "cliente_nome": lote.cliente_nome if lote else "",
                "ordem_producao": lote.ordem_producao if lote else "",
                "liberado_para_bipagem": processamento.liberado_para_bipagem,
                "data_liberacao": processamento.data_liberacao.isoformat() if processamento.data_liberacao else None,
            },
            "indicadores": {
                "total_pecas": len(pecas),
                "total_planejada": total_planejada,
                "total_produzida": total_produzida,
                "total_faltante": total_faltante,
                "percentual_concluido": percentual,
                "pecas_finalizadas": pecas_finalizadas,
                "pecas_em_producao": pecas_em_producao,
                "pecas_pendentes": pecas_pendentes,
                "total_eventos": total_eventos,
                "total_bipagens": total_bipagens,
                "total_estornos": total_estornos,
                "saldo_eventos": total_bipagens - total_estornos,
                "status_retorno": RetornoBipagemService._status_retorno(total_planejada, total_faltante, total_produzida),
            },
            "preview": preview,
            "preview_total_itens": len(pecas),
            "log": log,
            "log_total_eventos": total_eventos,
        }

    @staticmethod
    def gerar_relatorio_csv(pid: str) -> str | None:
        processamento = ProcessamentoPCP.objects.filter(id=pid).first()
        if not processamento:
            return None

        pecas = list(
            PecaPCP.objects
            .filter(modulo__ambiente__lote__pid=pid)
            .select_related("modulo__ambiente")
            .order_by("modulo__ambiente__nome", "modulo__nome", "codigo_peca")
        )

        output = io.StringIO()
        writer = csv.writer(output, delimiter=";")
        writer.writerow(
            [
                "pid",
                "lote",
                "codigo_peca",
                "descricao",
                "ambiente",
                "modulo",
                "plano",
                "quantidade_planejada",
                "quantidade_produzida",
                "faltam",
                "status",
                "ultimo_evento_tipo",
                "ultimo_evento_momento",
                "ultimo_evento_usuario",
                "ultimo_evento_localizacao",
                "ultimo_evento_motivo",
            ]
        )

        for peca in pecas:
            ultimo_evento = (
                EventoBipagem.objects
                .filter(peca=peca)
                .order_by("-momento")
                .first()
            )
            writer.writerow(
                [
                    processamento.id,
                    processamento.lote or "",
                    peca.codigo_peca,
                    peca.descricao,
                    peca.modulo.ambiente.nome if peca.modulo and peca.modulo.ambiente else "",
                    peca.modulo.nome if peca.modulo else "",
                    peca.plano or "",
                    peca.quantidade_planejada,
                    peca.quantidade_produzida,
                    max(peca.quantidade_planejada - peca.quantidade_produzida, 0),
                    peca.status,
                    ultimo_evento.tipo if ultimo_evento else "",
                    ultimo_evento.momento.isoformat() if ultimo_evento else "",
                    ultimo_evento.usuario if ultimo_evento else "",
                    ultimo_evento.localizacao if ultimo_evento else "",
                    ultimo_evento.motivo if ultimo_evento else "",
                ]
            )

        return output.getvalue()

    @staticmethod
    def _status_retorno(total_planejada: int, total_faltante: int, total_produzida: int) -> str:
        if total_planejada == 0:
            return "sem_pecas"
        if total_faltante == 0:
            return "concluido"
        if total_produzida == 0:
            return "pendente"
        return "em_producao"

    @staticmethod
    def _to_preview_peca(peca: PecaPCP) -> dict[str, Any]:
        return {
            "codigo_peca": peca.codigo_peca,
            "descricao": peca.descricao,
            "ambiente": peca.modulo.ambiente.nome if peca.modulo and peca.modulo.ambiente else "",
            "modulo": peca.modulo.nome if peca.modulo else "",
            "plano": peca.plano or "",
            "local": peca.local or "",
            "quantidade_planejada": peca.quantidade_planejada,
            "quantidade_produzida": peca.quantidade_produzida,
            "faltam": max(peca.quantidade_planejada - peca.quantidade_produzida, 0),
            "status": peca.status,
        }

    @staticmethod
    def _to_log_evento(evento: EventoBipagem) -> dict[str, Any]:
        peca = evento.peca
        return {
            "id": str(evento.id),
            "momento": evento.momento.isoformat(),
            "tipo": evento.tipo,
            "quantidade": evento.quantidade,
            "usuario": evento.usuario,
            "localizacao": evento.localizacao,
            "motivo": evento.motivo,
            "codigo_peca": peca.codigo_peca if peca else "",
            "descricao_peca": peca.descricao if peca else "",
            "ambiente": peca.modulo.ambiente.nome if peca and peca.modulo and peca.modulo.ambiente else "",
            "modulo": peca.modulo.nome if peca and peca.modulo else "",
            "plano": peca.plano if peca else "",
        }
