"""
Modelos Pydantic flexíveis para respostas da API Dinabox (listagens e detalhes).
"""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class DinaboxProjectListResponse(BaseModel):
    model_config = ConfigDict(extra="allow")

    projects: list[Any] = Field(default_factory=list)
    total: int = 0
    quantity: int = 10
    page: int = 1


class DinaboxProjectDetail(BaseModel):
    model_config = ConfigDict(extra="allow")


class DinaboxGroupListResponse(BaseModel):
    model_config = ConfigDict(extra="allow")

    project_groups: list[Any] = Field(default_factory=list)
    total: int = 0
    page: int = 1


class DinaboxGroupDetail(BaseModel):
    model_config = ConfigDict(extra="allow")


class DinaboxCustomerDetail(BaseModel):
    """Dados estruturados de um cliente Dinabox (GET /api/v1/customer)."""
    model_config = ConfigDict(extra="allow")

    customer_id: str | None = None
    customer_name: str | None = None
    customer_type: str | None = None  # "pf" ou "pj" ou None
    customer_status: str | None = None  # "on" ou "off" ou None
    customer_emails: list[str] | list[dict] | str | None = None
    customer_phones: list[str] | list[dict] | str | None = None
    customer_note: str | None = None
    customer_addresses: list[dict[str, Any]] | None = None
    customer_pf_data: dict[str, Any] | None = None
    customer_pj_data: dict[str, Any] | None = None
    custom_fields: list[Any] | dict[str, Any] | None = None
    created_at: str | None = None
    updated_at: str | None = None
    actions: list[str] | None = None


class DinaboxCustomerListResponse(BaseModel):
    model_config = ConfigDict(extra="allow")

    customers: list[Any] = Field(default_factory=list)
    total: int = 0


class DinaboxMaterialListResponse(BaseModel):
    model_config = ConfigDict(extra="allow")

    materials: list[Any] = Field(default_factory=list)
    total: int = 0
    page: int = 1


class DinaboxLabelListResponse(BaseModel):
    model_config = ConfigDict(extra="allow")

    labels: list[Any] = Field(default_factory=list)
    total: int = 0
    page: int = 1
