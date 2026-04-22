"""
SCHEMA LOGÍSTICO - Dinabox para Expedição, Viagens e Entregas

Responsável por: Customer info, endereços, expedição, viagens, tracking
Roteamento: apps/logistica/, apps/bipagem/ (para viagens)
"""

from datetime import datetime
from typing import List, Optional
from pydantic import Field, model_validator
from .base import DinaboxBaseModel


class CustomerInfo(DinaboxBaseModel):
    """Informações do cliente para logística."""
    customer_id: str = Field(..., alias="project_customer_id")
    customer_name: str = Field(..., alias="project_customer_name")
    customer_address: Optional[str] = Field(None, alias="project_customer_address")
    
    # Opcionais (se presentes no JSON futuro)
    phone: Optional[str] = None
    email: Optional[str] = None
    city: Optional[str] = None
    state: Optional[str] = None
    zipcode: Optional[str] = None


class ModuleLogistico(DinaboxBaseModel):
    """Módulo focado em informações para expedição."""
    
    id: str
    mid: str
    ref: str
    name: str
    type: str
    qt: int = 1
    
    # Dimensões para cálculo de volume/peso
    width: float
    height: float
    thickness: float
    
    @property
    def volume_m3(self) -> float:
        """Volume em metros cúbicos (aproximado)"""
        return (self.width * self.height * self.thickness) / 1_000_000_000


class ProjectHoleSummary(DinaboxBaseModel):
    """Resumo de itens para referência de conteúdo da remessa."""
    id: str
    ref: Optional[str] = None
    name: str
    qt: int
    dimensions: Optional[str] = None
    weight: Optional[float] = None


class DinaboxProjectLogistico(DinaboxBaseModel):
    """Projeto Dinabox focado em logística e expedição."""
    
    # Project metadata
    project_id: str
    project_status: str
    project_version: int
    project_description: str
    project_author_id: Optional[int] = None
    project_author_name: Optional[str] = None
    
    # Customer info (crítico para logística)
    customer: CustomerInfo = Field(...)
    project_created: str
    project_last_modified: str
    
    # Content for shipment planning
    woodwork: List[ModuleLogistico] = Field(default_factory=list)
    holes_summary: List[ProjectHoleSummary] = Field(default_factory=[], alias="holes")
    
    # Metadata Tarugo
    imported_at: datetime = Field(default_factory=datetime.now)

    @model_validator(mode="before")
    @classmethod
    def normalize_root(cls, obj):
        """Monta o cliente e preserva o autor antes da validacao."""
        if not isinstance(obj, dict):
            return obj

        data = dict(obj)
        data["customer"] = {
            "project_customer_id": data.get("project_customer_id"),
            "project_customer_name": data.get("project_customer_name"),
            "project_customer_address": data.get("project_customer_address"),
        }

        if "project_author_id" not in data and "project_author" in data:
            data["project_author_id"] = data.get("project_author")

        return data
    
    @property
    def total_modules(self) -> int:
        return len(self.woodwork)
    
    @property
    def total_volume_m3(self) -> float:
        """Volume total em metros cúbicos"""
        return sum(m.volume_m3 for m in self.woodwork)
    
    @property
    def total_items(self) -> int:
        """Total de itens para conferência de expedição"""
        return sum(h.qt for h in self.holes_summary)
    
    def get_shipment_summary(self) -> dict:
        """Retorna resumo para criação de viagem/expedição"""
        return {
            "project_id": self.project_id,
            "project_description": self.project_description,
            "customer": {
                "id": self.customer.customer_id,
                "name": self.customer.customer_name,
                "address": self.customer.customer_address,
            },
            "content": {
                "total_modules": self.total_modules,
                "total_items": self.total_items,
                "estimated_volume_m3": self.total_volume_m3,
            },
            "items_detail": [
                {
                    "id": h.id,
                    "name": h.name,
                    "quantity": h.qt,
                    "dimensions": h.dimensions,
                    "weight_kg": h.weight,
                }
                for h in self.holes_summary
            ]
        }
