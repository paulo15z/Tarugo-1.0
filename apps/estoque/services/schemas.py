"""Compatibilidade legada.
Use `apps.estoque.schemas.movimentacao`.
"""

from apps.estoque.schemas.movimentacao import AjusteLoteSchema, MovimentacaoCreateSchema, ReservaCreateSchema

MovimentacaoSchema = MovimentacaoCreateSchema

__all__ = [
    "MovimentacaoSchema",
    "MovimentacaoCreateSchema",
    "AjusteLoteSchema",
    "ReservaCreateSchema",
]
