from django.utils import timezone
from apps.pcp.models.lote import PecaPCP

class LotePCPService:
    """Serviço para gerenciar operações em lotes e peças (Bipagem)."""

    @staticmethod
    def bipar_peca(peca_id: int, quantidade: int) -> PecaPCP:
        """
        Registra a bipagem de uma peça.
        """
        try:
            peca = PecaPCP.objects.get(id=peca_id)
            peca.quantidade_bipada += quantidade
            
            # Se atingiu ou passou a meta, marca como concluída
            if peca.quantidade_bipada >= peca.quantidade_planejada:
                peca.status = 'concluido'
                peca.data_bipagem = timezone.now()
            else:
                peca.status = 'processando'
                
            peca.save()
            return peca
        except PecaPCP.DoesNotExist:
            raise ValueError(f"Peça com ID {peca_id} não encontrada.")
