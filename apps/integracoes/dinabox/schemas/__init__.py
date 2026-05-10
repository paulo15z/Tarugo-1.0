# apps/integracoes/dinabox/schemas/__init__.py
from .dinabox_operacional import DinaboxProjectOperacional, ModuleOperacional, PartOperacional
from .dinabox_logistico import DinaboxProjectLogistico, ModuleLogistico
from .dinabox_administrativo import DinaboxProjectAdministrativo, ModuleAdministrativo
from .api import (
    DinaboxProjectListResponse,
    DinaboxProjectDetail,
    DinaboxGroupListResponse,
    DinaboxGroupDetail,
    DinaboxCustomerDetail,
    DinaboxCustomerListResponse,
    DinaboxMaterialListResponse,
    DinaboxLabelListResponse,
)

__all__ = [
    "DinaboxProjectOperacional",
    "ModuleOperacional",
    "PartOperacional",
    "DinaboxProjectLogistico",
    "ModuleLogistico",
    "DinaboxProjectAdministrativo",
    "ModuleAdministrativo",
    "DinaboxProjectListResponse",
    "DinaboxProjectDetail",
    "DinaboxGroupListResponse",
    "DinaboxGroupDetail",
    "DinaboxCustomerDetail",
    "DinaboxCustomerListResponse",
    "DinaboxMaterialListResponse",
    "DinaboxLabelListResponse",
]
