from pydantic import BaseModel, Field, field_validator, model_validator
from typing import Dict, Any, Optional
from decimal import Decimal

# pydantic mt daora

class AtributosMDF(BaseModel):
    acabamento: str = Field(..., min_length=1)
    espessura: int = Field(..., gt=0)
    fabricante: str = Field(..., min_length=1)
    dimensao_chapa: Optional[str] = None
    custo_m2: Optional[Decimal] = None


class AtributosDobradiça(BaseModel):
    modelo: str = Field(..., min_length=1)
    angulo: int = Field(..., gt=0)
    marca: str = Field(..., min_length=1)
    diametro_copo: Optional[int] = Field(None, gt=0)
    tipo: str = Field(..., min_length=1)  # reta, curva, overlay, etc.
    cor: Optional[str] = None


class AtributosCorrediça(BaseModel):
    modelo: str = Field(..., min_length=1)
    tamanho: int = Field(..., gt=0)
    marca: str = Field(..., min_length=1)
    tipo: str = Field(..., min_length=1)
    capacidade_carga: Optional[int] = None


class AtributosFitaBorda(BaseModel):
    acabamento: str = Field(..., min_length=1)
    largura_mm: int = Field(..., gt=0)
    marca: str = Field(..., min_length=1)
    tipo: str = Field(..., min_length=1)  # PVC, ABS, etc.


class ProdutoCreateSchema(BaseModel):
    """Schema principal de criação de produto com validação por categoria"""
    nome: str = Field(..., min_length=3)
    sku: str = Field(..., min_length=3)
    categoria_id: int = Field(..., gt=0)
    familia: Optional[str] = None # Informado pelo front ou inferido pela categoria
    unidade_medida: str
    estoque_minimo: int = Field(0, ge=0)
    preco_custo: Optional[Decimal] = None
    lote: Optional[str] = None
    localizacao: Optional[str] = None
    atributos_especificos: Dict[str, Any] = Field(default_factory=dict)

    @model_validator(mode='after')
    def validar_atributos_por_categoria(self):
        """Validação dinâmica baseada na categoria (será melhorada quando tivermos o service)"""
        # Por enquanto só valida que veio algo quando necessário
        if not self.atributos_especificos:
            # Podemos deixar vazio por enquanto no MVP
            pass
        return self


class ProdutoUpdateSchema(BaseModel):
    nome: Optional[str] = None
    estoque_minimo: Optional[int] = None
    preco_custo: Optional[Decimal] = None
    lote: Optional[str] = None
    localizacao: Optional[str] = None
    atributos_especificos: Optional[Dict[str, Any]] = None
    ativo: Optional[bool] = None