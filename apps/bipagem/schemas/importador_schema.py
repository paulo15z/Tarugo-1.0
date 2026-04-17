from pydantic import BaseModel, Field


class LinhaCSV(BaseModel):
    pedido: str
    ordem: str
    modulo: str
    id_peca: str = Field(..., min_length=1)
    descricao: str


class ImportacaoInput(BaseModel):
    linhas: list[LinhaCSV]


class ImportacaoOutput(BaseModel):
    sucesso: bool
    total_pecas: int = 0
    pedidos_criados: int = 0
    erro: str | None = None
