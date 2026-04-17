from pydantic import BaseModel
from typing import Optional


class Peca(BaseModel):
    descricao: str
    material: Optional[str]
    largura: Optional[float]
    altura: Optional[float]
    espessura: Optional[float]
    quantidade: int
