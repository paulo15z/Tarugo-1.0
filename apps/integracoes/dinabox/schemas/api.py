# apps/integracoes/dinabox/schemas/api.py
from typing import List, Optional, Dict, Any
from pydantic import Field
from .base import DinaboxBaseModel

class DinaboxProjectDetail(DinaboxBaseModel):
    id: str
    description: str
    status: str
    customer_id: str
    customer_name: str
    created_at: str
    updated_at: str

class DinaboxProjectListResponse(DinaboxBaseModel):
    projects: List[DinaboxProjectDetail]
    total: int
    page: int
    quantity: int

class DinaboxGroupDetail(DinaboxBaseModel):
    id: str
    name: str

class DinaboxGroupListResponse(DinaboxBaseModel):
    project_groups: List[DinaboxGroupDetail]
    total: int

class DinaboxCustomerDetail(DinaboxBaseModel):
    id: str
    name: str
    type: str
    status: str
    emails: Optional[List[str]] = None
    phones: Optional[List[str]] = None
    addresses: Optional[List[Dict[str, Any]]] = None

class DinaboxCustomerListResponse(DinaboxBaseModel):
    customers: List[DinaboxCustomerDetail]
    total: int
    page: int
    quantity: int

class DinaboxMaterialListResponse(DinaboxBaseModel):
    materials: List[Dict[str, Any]]
    total: int

class DinaboxLabelListResponse(DinaboxBaseModel):
    labels: List[Dict[str, Any]]
    total: int
