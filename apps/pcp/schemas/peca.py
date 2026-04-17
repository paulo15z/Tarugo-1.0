from decimal import Decimal
from typing import Optional, List, Any

from pydantic import BaseModel, Field, field_validator, ConfigDict, model_validator


class AtributosTecnicos(BaseModel):
    """Atributos técnicos extraídos do Dinabox"""
    acabamento: Optional[str] = None
    furacao: Optional[str] = None
    duplagem: Optional[str] = None
    borda: Optional[str] = None
    pintura: Optional[str] = None
    tapecar: Optional[str] = None
    eletrica: Optional[str] = None
    curvo: Optional[str] = None

    model_config = ConfigDict(extra="ignore")


class Dimensoes(BaseModel):
    """Dimensões com parsing robusto (vírgula/ponto/nan)"""
    comprimento: Optional[Decimal] = Field(None, ge=0)
    largura: Optional[Decimal] = Field(None, ge=0)
    espessura: Optional[Decimal] = Field(None, ge=0)
    metro_quadrado: Optional[Decimal] = Field(None, ge=0)

    @field_validator(
        "comprimento", "largura", "espessura", "metro_quadrado", mode="before"
    )
    @classmethod
    def parse_decimal(cls, v: Any) -> Optional[Decimal]:
        if v is None or str(v).strip() in ("", "nan", "NaN", "0"):
            return None
        try:
            return Decimal(str(v).replace(",", "."))
        except:
            return None


class Peca(BaseModel):
    """Peça individual (uma linha do DataFrame)"""
    # Coluna REFERENCIA - parsing automático
    referencia: str = Field(..., min_length=1, description="Valor bruto da coluna REFERENCIA")

    codigo_modulo: Optional[str] = Field(None, description="ID do módulo quando presente (ex: M2052026)")
    codigo_peca: Optional[str] = Field(None, min_length=1, description="ID da peça (sempre presente)")

    descricao: str = Field(..., min_length=1)
    local: Optional[str] = None
    material: Optional[str] = None
    codigo_material: Optional[str] = None

    dimensoes: Dimensoes = Field(default_factory=Dimensoes)
    quantidade: int = Field(..., gt=0)

    atributos: AtributosTecnicos = Field(default_factory=AtributosTecnicos)

    # campos calculados pelo processamento
    roteiro: Optional[str] = None
    plano: Optional[str] = None

    observacoes: Optional[str] = None
    lote: Optional[str] = None
    id_peca_dinabox: Optional[str] = None  # ID DA PEÇA original

    # permite todos os campos extras do Dinabox
    model_config = ConfigDict(extra="allow")

    @model_validator(mode="before")
    @classmethod
    def parse_referencia(cls, data: Any) -> Any:
        """Parseia automaticamente a coluna REFERENCIA antes das validações obrigatórias."""
        if not isinstance(data, dict):
            return data

        ref = str(data.get("referencia", "")).strip()
        if not ref:
            return data

        if " - " in ref:
            partes = ref.split(" - ", 1)
            data["codigo_modulo"] = data.get("codigo_modulo") or partes[0].strip()
            data["codigo_peca"] = data.get("codigo_peca") or partes[1].strip()
        else:
            data["codigo_peca"] = data.get("codigo_peca") or ref

        return data


class Modulo(BaseModel):
    """Módulo do projeto"""
    nome: str = Field(..., min_length=1)                    # DESCRIÇÃO MÓDULO
    codigo_modulo: Optional[str] = None                     # ID do módulo (ex: M2052026)

    pecas: List[Peca] = Field(default_factory=list)


class Ambiente(BaseModel):
    """Ambiente do projeto (ex: SOCIAL, COZINHA)"""
    nome: str = Field(..., min_length=1)                    # NOME DO PROJETO
    modulos: List[Modulo] = Field(default_factory=list)


class Cliente(BaseModel):
    """Cliente do projeto"""
    nome: str = Field(..., min_length=1)                    # NOME DO CLIENTE
    id_projeto: Optional[str] = None                        # ID DO PROJETO
    ambientes: List[Ambiente] = Field(default_factory=list)


class LotePCPInput(BaseModel):
    """Input principal após processar o arquivo Dinabox"""
    pid: str = Field(..., min_length=8, max_length=8)
    arquivo_original: str

    cliente: Cliente

    # ordem de produção (pode vir do arquivo ou ser gerada)
    ordem_producao: Optional[str] = None

    model_config = ConfigDict(extra="allow")
