# apps/estoque/models.py
# Re-exporta tudo para compatibilidade com imports legados
from .models.produto import Produto
from .models.movimentacao import Movimentacao
from .models.reserva import Reserva

__all__ = ['Produto', 'Movimentacao', 'Reserva']