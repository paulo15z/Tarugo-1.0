from typing import Any

from pydantic import BaseModel


class DinaboxProjectItem(BaseModel):
    project_id: str
    project_status: str
    project_description: str
    project_author_id: int | None = None
    project_author_name: str | None = None
    project_client_id: str | None = None
    project_client_name: str | None = None
    project_created: str | None = None
    project_modified: str | None = None
    project_file_path: str | None = None
    project_size: str | None = None
    buy_price: str | None = None
    group_id: str | None = None


class DinaboxProjectListResponse(BaseModel):
    quantity: int
    page: int
    total: int
    projects: list[DinaboxProjectItem]


class DinaboxProjectDetail(BaseModel):
    project_id: str
    project_status: str
    project_version: int | None = None
    project_created: str | None = None
    project_last_modified: str | None = None
    project_author: int | None = None
    project_author_name: str | None = None
    project_description: str | None = None
    project_note: str | None = None
    project_details: str | None = None
    project_customer_id: str | None = None
    project_customer_name: str | None = None
    project_customer_address: str | None = None
    partners: list[Any] = []
    woodwork: list[Any] = []


class DinaboxGroupItem(BaseModel):
    project_group_id: str
    projects: list[str]
    status: str
    author: str | None = None
    date: str | None = None
    last_update: str | None = None


class DinaboxGroupListResponse(BaseModel):
    page: int
    total: int
    project_groups: list[DinaboxGroupItem]


class DinaboxGroupDetail(BaseModel):
    group_id: str
    projects: list[str]
    author: str | None = None
    status: str
    is_new_pcp: bool = False
    last_update: str | None = None
    lot_info: dict[str, Any] | None = None


class DinaboxCustomerItem(BaseModel):
    customer_id: str
    customer_name: str
    customer_emails: Any | None = None
    customer_phones: Any | None = None
    customer_type: str | None = None
    customer_status: str | None = None
    customer_city: str | None = None
    customer_state: str | None = None


class DinaboxCustomerListResponse(BaseModel):
    page: int
    total: int
    customers: list[DinaboxCustomerItem] = []


class DinaboxLabelItem(BaseModel):
    label_id: str
    label_type: str | None = None
    label_name: str | None = None
    label_content: str | None = None


class DinaboxLabelListResponse(BaseModel):
    page: int
    total: int
    labels: list[DinaboxLabelItem] = []


class DinaboxMaterialItem(BaseModel):
    material_id: str | None = None
    name: str | None = None
    category: str | None = None
    category_name: str | None = None
    details: str | None = None


class DinaboxMaterialListResponse(BaseModel):
    page: int
    total: int
    materials: list[DinaboxMaterialItem] = []
