# apps/pcp/services/schemas.py
from pydantic import BaseModel, Field


class PCPProcessRequest(BaseModel):
    """Schema de entrada para processamento do PCP"""
    lote: int = Field(..., gt=0, description="Número do lote (ex: 305)")
    filename: str
    file_bytes: bytes
    usuario_id: int | None = None