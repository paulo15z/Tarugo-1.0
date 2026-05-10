from decimal import Decimal
from typing import Optional
from pydantic import BaseModel, Field, field_validator


class CsvInputRow(BaseModel):
    """Modelo Pydantic para validar linhas do CSV de entrada."""

    nome_do_cliente: str = Field(..., description="Nome do cliente")
    id_do_projeto: str = Field(..., description="ID do projeto")
    nome_do_projeto: str = Field(..., description="Nome do projeto")
    referencia_da_peca: Optional[str] = Field(None, description="Referencia da peca")
    descricao_modulo: str = Field(..., description="Descricao do modulo")
    quantidade: int = Field(..., gt=0, description="Quantidade")
    largura_da_peca: Decimal = Field(..., ge=0, description="Largura da peca")
    altura_da_peca: Decimal = Field(..., ge=0, description="Altura da peca")
    metro_quadrado: Optional[Decimal] = Field(None, ge=0, description="Metro quadrado")
    espessura: Decimal = Field(..., ge=0, description="Espessura")
    codigo_do_material: str = Field(..., description="Codigo do material")
    material_da_peca: str = Field(..., description="Material da peca")
    veio: Optional[str] = Field(None, description="Veio")
    borda_face_frente: Optional[str] = Field(None, description="Borda face frente")
    borda_face_traseira: Optional[str] = Field(None, description="Borda face traseira")
    borda_face_le: Optional[str] = Field(None, description="Borda face LE")
    borda_face_ld: Optional[str] = Field(None, description="Borda face LD")
    lote: Optional[str] = Field(None, description="Lote")
    observacao: Optional[str] = Field(None, description="Observacao")
    descricao_da_peca: str = Field(..., description="Descricao da peca")
    id_da_peca: str = Field(..., description="ID da peca")
    local: str = Field(..., description="Local")
    duplagem: Optional[str] = Field(None, description="Duplagem")
    furo: Optional[str] = Field(None, description="Furo")
    obs: Optional[str] = Field(None, description="Obs")
    referencia: Optional[str] = Field(None, description="Referencia")
    furo_a: Optional[str] = Field(None, description="Furo A")
    furo_b: Optional[str] = Field(None, description="Furo B")

    @field_validator(
        "nome_do_cliente",
        "id_do_projeto",
        "nome_do_projeto",
        "referencia_da_peca",
        "descricao_modulo",
        "codigo_do_material",
        "material_da_peca",
        "veio",
        "borda_face_frente",
        "borda_face_traseira",
        "borda_face_le",
        "borda_face_ld",
        "lote",
        "observacao",
        "descricao_da_peca",
        "id_da_peca",
        "local",
        "duplagem",
        "furo",
        "obs",
        "referencia",
        "furo_a",
        "furo_b",
        mode="before",
    )
    @classmethod
    def normalizar_strings(cls, v):
        if v is None:
            return None
        if isinstance(v, float) and v.is_integer():
            return str(int(v))
        return str(v).strip()

    @field_validator("quantidade", mode="before")
    @classmethod
    def validar_quantidade(cls, v):
        if v is None:
            return 1
        try:
            return int(v)
        except:
            return 1

    @field_validator("largura_da_peca", "altura_da_peca", "espessura", "metro_quadrado", mode="before")
    @classmethod
    def converter_decimal(cls, v):
        if v is None or str(v).strip() in ("", "nan", "NaN"):
            return Decimal("0")
        try:
            return Decimal(str(v).replace(",", "."))
        except:
            return Decimal("0")

    @field_validator("id_da_peca", mode="after")
    @classmethod
    def limpar_id_peca(cls, v):
        """Remove '.0' do final do ID da peca se presente."""
        if isinstance(v, str) and v.endswith('.0'):
            return v[:-2]
        return v
