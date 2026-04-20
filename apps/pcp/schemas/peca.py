from decimal import Decimal
from datetime import datetime
from typing import Optional, Set, Dict, Literal
from pydantic import BaseModel, Field, ConfigDict, field_validator


class Dimensoes(BaseModel): #dimensoes
    largura: Optional[Decimal] = Field(None, ge=0)
    altura: Optional[Decimal] = Field(None, ge=0)
    espessura: Optional[Decimal] = Field(None, ge=0)
    metro_quadrado: Optional[Decimal] = Field(None, ge=0)

    @field_validator("largura", "altura", "espessura", "metro_quadrado", mode="before")
    @classmethod
    def converter_decimal(cls, v):
        if v is None or str(v).strip() in ("", "nan", "NaN"): #tratamento basico de nulos
            return None
        try:
            return Decimal(str(v).replace(",", ".")) #troca de decimal
        except Exception:
            return None


class BordaInfo(BaseModel): 
    face: Literal["left", "right", "top", "bottom"]
    nome: Optional[str] = None
    perimetro_mm: Decimal = 0
    espessura_mm: int = 0


class PecaOperacional(BaseModel): # model tipado para o resto da operação
    # IDENTIFICAÇÃO
    id_dinabox: str
    ref_completa: str
    ref_modulo: Optional[str] = None
    ref_peca: Optional[str] = None
    descricao: str

    # LOCALIZAÇÃO
    modulo_ref: str
    modulo_nome: str
    contexto: Optional[str] = None

    # GEOMETRIA
    quantidade: int = Field(..., gt=0)
    dimensoes: Dimensoes
    material_id: Optional[str] = None
    material_nome: Optional[str] = None
    material_com_veio: bool = False

    # BORDA 
    bordas: Dict[str, BordaInfo] = Field(default_factory=dict)

    # PROCESSAMENTO
    furacoes: Dict[str, Optional[str]] = Field(default_factory=dict)
    eh_duplada: bool = False
    dinabox_entity: Optional[str] = None      # ex: "dinabox_porta", "cabinet", "panel"
    dinabox_type: Optional[str] = None


    # ANOTAÇÕES
    observacoes_original: Optional[str] = None
    tags_markdown: Set[str] = Field(default_factory=set)
    atributos_tecnicos: Dict[str, Any] = Field(default_factory=dict)

    # RESULTADO
    roteiro: Optional[str] = None
    plano_corte: Optional[str] = None
    lote_saida: Optional[str] = None

    # AUDITORIA
    data_criacao: datetime = Field(default_factory=datetime.now)
    id_auditoria: Optional[str] = None

    model_config = ConfigDict(from_attributes=True, extra="allow")

    def eh_ripa(self) -> bool:
        return "_ripa_" in self.tags_markdown or "ripa" in self.descricao.lower()

    def eh_porta_dinabox(self) -> bool:
        """Regra forte baseada no entity da API"""
        if self.dinabox_entity and "dinabox_porta" in self.dinabox_entity.lower():
            return True
        
        return "porta" in self.descricao.lower() and "_ripa_" not in self.tags_markdown

    def tem_furacoes(self) -> bool:
        return any(self.furacoes.values())

    def tem_bordas(self) -> bool:
        return any(b.nome for b in self.bordas.values())

    def eh_duplada_de_verdade(self) -> bool:
        return self.eh_duplada and "_dup_" in self.tags_markdown