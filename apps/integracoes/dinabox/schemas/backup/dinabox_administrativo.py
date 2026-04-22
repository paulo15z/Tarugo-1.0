"""
SCHEMA ADMINISTRATIVO - Dinabox para PCP, Financeiro, Compras, Estoque

Responsável por: Gerenciar BOM, custos, alocação de material, ordens de compra
Roteamento: apps/pcp/, apps/estoque/, apps/finanzeiro/
"""

from datetime import datetime
from typing import List, Optional, Dict, Any
from pydantic import Field, field_validator, model_validator
from .base import DinaboxBaseModel


class MaterialInfo(DinaboxBaseModel):
    """Informação de material para BOM e orçamento."""
    id: Optional[str] = Field(None, alias="material_id")
    name: Optional[str] = Field(None, alias="material_name")
    manufacturer: Optional[str] = Field(None, alias="material_manufacturer")
    collection: Optional[str] = Field(None, alias="material_collection")
    m2: Optional[float] = Field(None, alias="material_m2", description="Área m²")
    width: Optional[float] = Field(None, alias="material_width")
    height: Optional[float] = Field(None, alias="material_height")
    reference: Optional[str] = Field(None, alias="material_ref")

    @field_validator("width", "height", "m2", mode="before")
    @classmethod
    def parse_float(cls, v: Any) -> Optional[float]:
        if isinstance(v, str) and v.strip():
            try:
                return float(v.replace(",", "."))
            except ValueError:
                return None
        return v


class PartAdministrativo(DinaboxBaseModel):
    """Peça focada em BOM e custos."""
    
    id: str
    ref: str
    code_a: Optional[str] = None
    code_b: Optional[str] = None
    code_a2: Optional[str] = None
    code_b2: Optional[str] = None
    name: str
    count: int = 1
    
    # Dimensões para cálculo de material
    width: float
    height: float
    thickness: float
    weight: float = 0.0
    
    # Material
    material: MaterialInfo
    
    # Preços
    factory_price: float = 0.0
    buy_price: float = 0.0
    sale_price: float = 0.0
    
    @classmethod
    def model_validate(cls, obj, **kwargs):
        """Mapeia campos flat do JSON Dinabox para estrutura de classes."""
        if isinstance(obj, dict):
            # Mapear material (campos prefixados com material_)
            material_data = {k: v for k, v in obj.items() if k.startswith("material_")}
            if material_data:
                obj["material"] = material_data
        return super().model_validate(obj, **kwargs)


class InputItemAdministrativo(DinaboxBaseModel):
    """Insumo/Hardware para BOM e orçamento."""
    
    id: str
    unique_id: str
    category_id: Optional[str] = None
    category_name: str
    name: str
    description: Optional[str] = ""
    
    qt: float
    unit: Optional[str] = None
    
    manufacturer: Optional[str] = None
    supplier_id: Optional[str] = None
    reference: Optional[str] = None
    purchase_order_id: Optional[str] = None
    
    factory_price: float = 0.0
    buy_price: float = 0.0
    sale_price: float = 0.0


class ModuleAdministrativo(DinaboxBaseModel):
    """Módulo focado em BOM e gestão de material."""
    
    id: str
    mid: str
    ref: str
    name: str
    type: str
    qt: int = 1
    
    # Conteúdo para BOM
    parts: List[PartAdministrativo] = Field(default_factory=list)
    inputs: List[InputItemAdministrativo] = Field(default_factory=list)

    @field_validator("parts", mode="before")
    @classmethod
    def normalize_parts(cls, parts: Any) -> Any:
        """Monta o material aninhado antes da validacao."""
        if not isinstance(parts, list):
            return parts

        normalized = []
        for part in parts:
            if not isinstance(part, dict):
                normalized.append(part)
                continue

            data = dict(part)
            material_data = {k: v for k, v in data.items() if k.startswith("material_")}
            if material_data:
                data["material"] = material_data
            normalized.append(data)

        return normalized
    
    @property
    def total_cost(self) -> float:
        """Custo total do módulo (material + insumos)"""
        parts_cost = sum(p.factory_price * p.count for p in self.parts)
        inputs_cost = sum(i.factory_price * i.qt for i in self.inputs)
        return parts_cost + inputs_cost


class DinaboxProjectAdministrativo(DinaboxBaseModel):
    """Projeto Dinabox focado em BOM, finanças e planejamento."""
    
    # Project metadata
    project_id: str
    project_status: str
    project_version: int
    project_description: str
    project_customer_id: str
    project_customer_name: str
    project_created: str
    project_last_modified: str
    
    # Author
    project_author_id: Optional[int] = None
    project_author_name: Optional[str] = None
    
    # BOM
    woodwork: List[ModuleAdministrativo] = Field(default_factory=list)
    
    # Metadata Tarugo
    imported_at: datetime = Field(default_factory=datetime.now)

    @model_validator(mode="before")
    @classmethod
    def normalize_root(cls, obj: Any) -> Any:
        """Preserva o autor do projeto ao validar a raiz."""
        if not isinstance(obj, dict):
            return obj

        data = dict(obj)
        if "project_author_id" not in data and "project_author" in data:
            data["project_author_id"] = data.get("project_author")
        return data
    
    @property
    def total_materials_cost(self) -> float:
        """Custo total de todos os materiais"""
        return sum(m.total_cost for m in self.woodwork)
    
    @property
    def total_modules(self) -> int:
        return len(self.woodwork)
    
    @property
    def total_parts(self) -> int:
        return sum(len(m.parts) for m in self.woodwork)
    
    @property
    def total_inputs(self) -> int:
        return sum(len(m.inputs) for m in self.woodwork)
    
    def get_bom_summary(self) -> Dict[str, Any]:
        """Retorna resumo de BOM para relatórios"""
        materials = {}
        hardware = {}
        
        for module in self.woodwork:
            for part in module.parts:
                key = f"{part.material.id}_{part.width}x{part.height}x{part.thickness}"
                if key not in materials:
                    materials[key] = {
                        "material": part.material.name,
                        "dimensions": f"{part.width}x{part.height}x{part.thickness}mm",
                        "quantity": 0,
                        "cost": 0.0
                    }
                materials[key]["quantity"] += part.count
                materials[key]["cost"] += part.factory_price * part.count
            
            for item in module.inputs:
                key = f"{item.id}_{item.category_name}"
                if key not in hardware:
                    hardware[key] = {
                        "item": item.name,
                        "category": item.category_name,
                        "quantity": 0,
                        "unit": item.unit,
                        "cost": 0.0
                    }
                hardware[key]["quantity"] += item.qt
                hardware[key]["cost"] += item.factory_price * item.qt
        
        return {
            "materials": materials,
            "hardware": hardware,
            "total_cost": self.total_materials_cost
        }
