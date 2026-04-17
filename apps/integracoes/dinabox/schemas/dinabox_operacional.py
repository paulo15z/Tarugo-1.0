from datetime import datetime
from typing import List, Optional, Any
from pydantic import BaseModel, Field, field_validator, model_validator

class DinaboxBaseModel(BaseModel):
    pass

class HoleDetail(DinaboxBaseModel):
    """Detalhe de furo ou rasgo para usinagem."""
    type: str = Field(..., alias="t", description="F=Furo, R=Rasgo")
    
    x: Optional[float] = Field(None, description="X para furos")
    x1: Optional[float] = Field(None, description="X inicial para rasgos")
    x2: Optional[float] = Field(None, description="X final para rasgos")
    y1: Optional[float] = Field(None, description="Y inicial para rasgos")
    y2: Optional[float] = Field(None, description="Y final para rasgos")
    y: Optional[float] = Field(None, description="Y coordinate")
    z: Optional[float] = Field(None, description="Z profundidade")
    diameter: Optional[float] = Field(None, alias="d", description="Diâmetro/largura")
    
    r1: Optional[str] = Field(None, description="Referência 1")
    r2: Optional[str] = Field(None, description="Referência 2")

    @field_validator("x", "x1", "x2", "y", "y1", "y2", "z", "diameter", mode="before")
    @classmethod
    def parse_float_coords(cls, v: Any) -> Optional[float]:
        if v is None:
            return None
        if isinstance(v, (int, float)):
            return float(v)
        if isinstance(v, str) and v.strip():
            try:
                return float(v.replace(",", "."))
            except ValueError:
                return None
        return None

class PartHoles(DinaboxBaseModel):
    """Furos por face (A, B, C, D, E, F)."""
    face_a: Optional[List[HoleDetail]] = Field(None, alias="A")
    face_b: Optional[List[HoleDetail]] = Field(None, alias="B")
    face_c: Optional[List[HoleDetail]] = Field(None, alias="C")
    face_d: Optional[List[HoleDetail]] = Field(None, alias="D")
    face_e: Optional[List[HoleDetail]] = Field(None, alias="E")
    face_f: Optional[List[HoleDetail]] = Field(None, alias="F")
    invert: bool = False
    
    @property
    def total_holes(self) -> int:
        count = 0
        for face in [self.face_a, self.face_b, self.face_c, self.face_d, self.face_e, self.face_f]:
            if face:
                count += len(face)
        return count

class EdgeDetail(DinaboxBaseModel):
    """Detalhe de rebordo para um lado."""
    name: Optional[str] = None
    material_id: Optional[str] = None
    perimeter: Optional[float] = None
    thickness_abs: Optional[str] = Field(None, alias="abs")
    factory_price: Optional[float] = 0.0
    
    @field_validator("perimeter", mode="before")
    @classmethod
    def parse_perimeter(cls, v: Any) -> Optional[float]:
        if v is None:
            return None
        if isinstance(v, (int, float)):
            return float(v)
        if isinstance(v, str) and v.strip():
            try:
                return float(v.replace(",", "."))
            except ValueError:
                return None
        return None

class MaterialInfo(DinaboxBaseModel):
    """Material para processamento em fábrica."""
    id: Optional[str] = Field(None, alias="material_id")
    name: Optional[str] = Field(None, alias="material_name")
    manufacturer: Optional[str] = Field(None, alias="material_manufacturer")
    collection: Optional[str] = Field(None, alias="material_collection")
    m2: Optional[float] = Field(None, alias="material_m2")
    vein: bool = Field(False, alias="material_vein")
    width: Optional[float] = Field(None, alias="material_width")
    height: Optional[float] = Field(None, alias="material_height")
    face: Optional[str] = Field(None, alias="material_face")
    thumbnail: Optional[str] = Field(None, alias="material_thumbnail")

    @field_validator("width", "height", "m2", mode="before")
    @classmethod
    def parse_float(cls, v: Any) -> Optional[float]:
        if isinstance(v, str) and v.strip():
            try:
                return float(v.replace(",", "."))
            except ValueError:
                return None
        return v

class PartOperacional(DinaboxBaseModel):
    """Peça focada em operações de fabricação e rastreabilidade."""
    id: str
    ref: str
    code_a: Optional[str] = None
    code_b: Optional[str] = None
    code_a2: Optional[str] = None
    code_b2: Optional[str] = None
    name: str
    type: str
    entity: str
    count: int = 1
    note: Optional[str] = ""
    width: float
    height: float
    thickness: float
    weight: float = 0.0
    material: Optional[MaterialInfo] = None
    edge_left: EdgeDetail = Field(default_factory=EdgeDetail)
    edge_right: EdgeDetail = Field(default_factory=EdgeDetail)
    edge_top: EdgeDetail = Field(default_factory=EdgeDetail)
    edge_bottom: EdgeDetail = Field(default_factory=EdgeDetail)
    holes: Optional[PartHoles] = None
    
    @property
    def total_holes(self) -> int:
        return self.holes.total_holes if self.holes else 0
    
    @classmethod
    def model_validate(cls, obj: Any, **kwargs) -> "PartOperacional":
        if isinstance(obj, dict):
            material_data = {k: v for k, v in obj.items() if k.startswith("material_")}
            if material_data:
                obj["material"] = material_data
            for side in ["left", "right", "top", "bottom"]:
                edge_key = f"edge_{side}"
                edge_value = obj.get(edge_key)
                if edge_value is None or isinstance(edge_value, str):
                    edge_data = {
                        "name": edge_value if isinstance(edge_value, str) else None,
                        "material_id": obj.get(f"{edge_key}_id"),
                        "perimeter": obj.get(f"{edge_key}_perimeter"),
                        "thickness_abs": obj.get(f"{edge_key}_abs"),
                        "factory_price": obj.get(f"{edge_key}_factory"),
                    }
                    obj[edge_key] = edge_data
        return super().model_validate(obj, **kwargs)

class InputItemOperacional(DinaboxBaseModel):
    """Hardware/insumo para rastreabilidade operacional."""
    id: str
    unique_id: str
    category_id: Optional[str] = None
    category_name: str
    name: str
    description: Optional[str] = ""
    qt: float
    unit: Optional[str] = None

class ModuleOperacional(DinaboxBaseModel):
    """Módulo focado em fabricação e montagem."""
    id: str
    mid: str
    ref: str
    name: str
    type: str
    qt: int = 1
    note: Optional[str] = ""
    width: float
    height: float
    thickness: float
    thumbnail: Optional[str] = None
    pre_assembly: Optional[bool] = False
    parts: List[PartOperacional] = Field(default_factory=list)
    inputs: List[InputItemOperacional] = Field(default_factory=list)

    @field_validator("parts", mode="before")
    @classmethod
    def normalize_parts(cls, parts: Any) -> Any:
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
            for side in ["left", "right", "top", "bottom"]:
                edge_key = f"edge_{side}"
                edge_value = data.get(edge_key)
                if edge_value is None or isinstance(edge_value, str):
                    data[edge_key] = {
                        "name": edge_value if isinstance(edge_value, str) else None,
                        "material_id": data.get(f"{edge_key}_id"),
                        "perimeter": data.get(f"{edge_key}_perimeter"),
                        "abs": data.get(f"{edge_key}_abs"),
                        "factory_price": data.get(f"{edge_key}_factory"),
                    }
            normalized.append(data)
        return normalized

class ProjectHoleSummary(DinaboxBaseModel):
    """Resumo de hardware/furos para referência operacional."""
    id: str
    ref: Optional[str] = None
    name: str
    qt: int
    dimensions: Optional[str] = None
    weight: Optional[float] = None

class DinaboxProjectOperacional(DinaboxBaseModel):
    """Projeto Dinabox focado em operações de fábrica."""
    project_id: str
    project_status: str
    project_version: int
    project_description: str
    project_customer_id: str
    project_customer_name: str
    project_created: str
    project_last_modified: str
    project_author_id: Optional[int] = None
    project_author_name: Optional[str] = None
    woodwork: List[ModuleOperacional] = Field(default_factory=list)
    holes: List[ProjectHoleSummary] = Field(default_factory=[])
    imported_at: datetime = Field(default_factory=datetime.now)

    @model_validator(mode="before")
    @classmethod
    def normalize_root(cls, obj: Any) -> Any:
        if not isinstance(obj, dict):
            return obj
        data = dict(obj)
        if "project_author_id" not in data and "project_author" in data:
            data["project_author_id"] = data.get("project_author")
        return data
