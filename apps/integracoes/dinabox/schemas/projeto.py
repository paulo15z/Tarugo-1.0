from pydantic import BaseModel
from typing import List, Optional
from .insumo import Insumo
from .peca import Peca
from .base import Metadata
from .material import Chapa

class Cliente(BaseModel):
    nome: Optional[str]


class Projeto(BaseModel):
    id: Optional[str]
    nome: Optional[str]


class ProjetoCompleto(BaseModel):
    projeto: Projeto
    cliente: Cliente

    pecas: List[Peca]
    insumos: List[Insumo]

    chapas: List[Chapa]

    metadata: Metadata
