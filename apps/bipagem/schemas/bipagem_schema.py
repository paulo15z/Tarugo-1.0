from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime

class BipagemInput(BaseModel):
    codigo_peca: str = Field(..., min_length=1)
    usuario: str = Field(default="DESCONHECIDO")
    localizacao: str = Field(default="")
    lote_producao_id: Optional[int] = None

class PecaOutput(BaseModel):
    id_peca: str
    descricao: str
    status: str
    local: str
    material: Optional[str] = None
    quantidade: int
    roteiro: Optional[str] = None
    plano_corte: Optional[str] = None
    setor_destino: Optional[str] = None
    numero_lote_pcp: Optional[str] = None # Novo campo
    data_bipagem: Optional[datetime] = None
    pedido_numero: Optional[str] = None
    modulo_nome: Optional[str] = None

class BipagemOutput(BaseModel):
    sucesso: bool
    mensagem: str
    erro: Optional[str] = None
    repetido: bool = False
    peca: Optional[PecaOutput] = None

class ResumoModulo(BaseModel):
    referencia: str
    nome: str
    total: int
    bipadas: int
    percentual: float

class DetalheModulo(BaseModel):
    modulo: ResumoModulo
    pecas: List[PecaOutput]
