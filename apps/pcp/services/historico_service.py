from __future__ import annotations

from django.db import transaction
from django.db.models import ProtectedError
from django.db.utils import IntegrityError

from apps.pcp.models import AuditoriaProcessamentoPCP, LotePCP, ProcessamentoPCP


class HistoricoPCPService:
    @staticmethod
    @transaction.atomic
    def remover_processamento(pid: str, motivo: str, usuario=None) -> dict:
        motivo = (motivo or '').strip()
        if len(motivo) < 3:
            return {'sucesso': False, 'mensagem': 'Informe um motivo com pelo menos 3 caracteres.'}

        try:
            processamento = ProcessamentoPCP.objects.get(id=pid)
        except ProcessamentoPCP.DoesNotExist:
            return {'sucesso': False, 'mensagem': 'Processamento nao encontrado.'}

        lote_pcp = LotePCP.objects.filter(pid=pid).prefetch_related('ambientes__modulos__pecas').first()
        snapshot = {
            'pid': processamento.id,
            'lote': processamento.lote,
            'nome_arquivo': processamento.nome_arquivo,
            'total_pecas': processamento.total_pecas,
            'liberado_para_bipagem': processamento.liberado_para_bipagem,
            'liberado_para_viagem': processamento.liberado_para_viagem,
            'cliente_nome': lote_pcp.cliente_nome if lote_pcp else None,
            'ordem_producao': lote_pcp.ordem_producao if lote_pcp else None,
        }

        AuditoriaProcessamentoPCP.objects.create(
            processamento_id=processamento.id,
            lote=processamento.lote,
            nome_arquivo=processamento.nome_arquivo,
            acao='EXCLUSAO',
            motivo=motivo,
            usuario=usuario if getattr(usuario, 'is_authenticated', False) else None,
            snapshot=snapshot,
        )

        if processamento.arquivo_saida:
            processamento.arquivo_saida.delete(save=False)

        try:
            if lote_pcp:
                lote_pcp.delete()
            processamento.delete()
        except ProtectedError:
            return {
                'sucesso': False,
                'mensagem': (
                    'Nao foi possivel remover este lote porque existem registros '
                    'protegidos vinculados a ele.'
                ),
            }
        except IntegrityError:
            return {
                'sucesso': False,
                'mensagem': (
                    'Nao foi possivel remover este lote por conflito de integridade '
                    'de dados. Verifique vinculos no PCP/Bipagem.'
                ),
            }

        return {
            'sucesso': True,
            'mensagem': f'Processamento {pid} removido com auditoria.',
        }
