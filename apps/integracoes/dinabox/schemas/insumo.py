from pydantic import BaseModel
from typing import Optional


class Quantidade(BaseModel):
    valor: float
    unidade: str  # un | m2 | metro


class Insumo(BaseModel):
    categoria: Optional[str]

    descricao: str

    tipo: str  

    quantidade: Quantidade

    # 👇 só quando fizer sentido
    largura: Optional[int] = None
    altura: Optional[int] = None
    espessura: Optional[int] = None

    # 👇 campo livre pra não perder info do Dinabox
    metadata: Optional[dict] = None
