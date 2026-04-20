from decimal import Decimal
from typing import Optional, List, Dict
from pydantic import BaseModel, Field, ConfigDict, field_validator


class MaterialDinabox(BaseModel): #acabamento
    id: str
    name: str
    width: Decimal = Field(..., gt=0)
    height: Decimal = Field(..., gt=0)
    vein: bool = False

    model_config = ConfigDict(from_attributes=True)


class EdgeDinabox(BaseModel): #borda
    name: Optional[str] = None
    perimeter: Decimal = 0
    thickness: int = 0

    model_config = ConfigDict(from_attributes=True)


class PartDinabox(BaseModel): #peça
    id: str
    ref: str = Field(..., min_length=1)
    name: str = Field(..., min_length=1)
    type: str = "cabinet"
    count: int = Field(..., gt=0)

    width: Decimal = Field(..., gt=0)
    height: Decimal = Field(..., gt=0)
    thickness: Decimal = Field(..., gt=0)

    material: Optional[MaterialDinabox] = None
    note: Optional[str] = None
    code_a: Optional[str] = None
    code_b: Optional[str] = None
    code_a2: Optional[str] = None
    code_b2: Optional[str] = None

    edge_left: Optional[EdgeDinabox] = None #seta default e aponta a classe especifica
    edge_right: Optional[EdgeDinabox] = None
    edge_top: Optional[EdgeDinabox] = None
    edge_bottom: Optional[EdgeDinabox] = None

    model_config = ConfigDict(from_attributes=True, extra="allow")


class ModuleDinabox(BaseModel): #modulo
    id: str
    mid: str
    ref: str = Field(..., min_length=1)
    name: str = Field(..., min_length=1)
    type: str = "thickened"

    parts: List[PartDinabox] = Field(default_factory=list)
    material: Optional[MaterialDinabox] = None

    edge_left: Optional[EdgeDinabox] = None
    edge_right: Optional[EdgeDinabox] = None
    edge_top: Optional[EdgeDinabox] = None
    edge_bottom: Optional[EdgeDinabox] = None

    model_config = ConfigDict(from_attributes=True, extra="allow")


class ProjectoDinabox(BaseModel): #projeto/ambiente
    project_id: str = Field(..., min_length=8, max_length=10)
    project_customer_name: str
    project_customer_id: str
    project_description: str
    project_status: str
    project_created: str
    project_last_modified: str
    project_author_name: str

    woodwork: List[ModuleDinabox] = Field(default_factory=list) # lista de peças/modulos
    holes: Optional[List[Dict]] = None #furação

    model_config = ConfigDict(from_attributes=True, extra="allow")

    @field_validator("project_id")
    @classmethod
    def validar_project_id(cls, v: str) -> str:
        if not v.isdigit() or len(v) not in (8, 10):
            raise ValueError("Project ID deve ter 8 ou 10 dígitos")
        return v