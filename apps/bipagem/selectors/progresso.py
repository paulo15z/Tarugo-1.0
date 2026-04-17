from django.db.models import Count, Q
from typing import List, Optional
from apps.bipagem.models import Pedido, Modulo, Peca
from apps.bipagem.domain.tipos import StatusPeca

def get_resumo_pedido(numero_pedido: str) -> Optional[dict]:
    """
    Retorna o resumo de progresso de um pedido.
    """
    try:
        pedido = Pedido.objects.get(numero_pedido=numero_pedido)
        
        # Agregando dados de progresso
        stats = Peca.objects.filter(
            modulo__ordem_producao__pedido=pedido
        ).aggregate(
            total=Count('id'),
            bipadas=Count('id', filter=Q(status=StatusPeca.BIPADA)),
            concluidas=Count('id', filter=Q(status=StatusPeca.CONCLUIDA))
        )
        
        total = stats['total'] or 0
        bipadas = stats['bipadas'] or 0
        percentual = (bipadas / total * 100) if total > 0 else 0
        
        return {
            'numero_pedido': pedido.numero_pedido,
            'cliente': pedido.cliente_nome,
            'total_pecas': total,
            'pecas_bipadas': bipadas,
            'pecas_bipadas_neg': -bipadas, # Para facilitar cálculos no template Django
            'percentual': round(percentual, 1)
        }
    except Pedido.DoesNotExist:
        return None

def get_modulos_pedido(numero_pedido: str) -> List[dict]:
    """
    Retorna a lista de módulos de um pedido com seu progresso.
    """
    modulos = Modulo.objects.filter(
        ordem_producao__pedido__numero_pedido=numero_pedido
    ).annotate(
        total=Count('pecas'),
        bipadas=Count('pecas', filter=Q(pecas__status=StatusPeca.BIPADA))
    ).order_by('nome_modulo')
    
    resultado = []
    for m in modulos:
        total = m.total or 0
        bipadas = m.bipadas or 0
        percentual = (bipadas / total * 100) if total > 0 else 0
        
        resultado.append({
            'referencia': m.referencia_modulo,
            'nome': m.nome_modulo,
            'total': total,
            'bipadas': bipadas,
            'percentual': round(percentual, 1)
        })
    return resultado

def get_pecas_modulo(referencia_modulo: str) -> List[Peca]:
    """
    Retorna todas as peças de um módulo específico.
    """
    return Peca.objects.filter(
        modulo__referencia_modulo=referencia_modulo
    ).select_related('modulo__ordem_producao__pedido').order_by('id_peca')
