from pydantic import BaseModel, Field


class BipagemScanInput(BaseModel):
    pid: str = Field(..., min_length=8, max_length=8)
    codigo_peca: str = Field(..., min_length=1)
    quantidade: int = Field(default=1, ge=1)
    usuario: str = Field(default="OPERADOR")
    localizacao: str = Field(default="")


class EstornoBipagemInput(BaseModel):
    pid: str = Field(..., min_length=8, max_length=8)
    codigo_peca: str = Field(..., min_length=1)
    usuario: str = Field(..., min_length=1)
    motivo: str = Field(..., min_length=3)
