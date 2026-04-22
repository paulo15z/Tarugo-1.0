from __future__ import annotations

from typing import Any

from pydantic import Field, field_validator

from .base import DinaboxBaseModel


class DinaboxProjetoPedidoSchema(DinaboxBaseModel):
    """Contrato mínimo para integrar um ambiente concluído ao app Pedidos."""

    project_id: str
    project_status: str | None = None
    project_version: int | None = None
    project_description: str
    project_customer_id: str
    project_customer_name: str | None = None
    project_created: str | None = None
    project_last_modified: str | None = None
    project_author_name: str | None = None
    holes: list[dict[str, Any]] = Field(default_factory=list)
    woodwork: list[dict[str, Any]] = Field(default_factory=list)

    @field_validator("project_id", "project_description", "project_customer_id", mode="before")
    @classmethod
    def validate_required_text(cls, value: Any) -> str:
        text = str(value or "").strip()
        if not text:
            raise ValueError("Campo obrigatório vazio.")
        return text

    @field_validator(
        "project_status",
        "project_customer_name",
        "project_created",
        "project_last_modified",
        "project_author_name",
        mode="before",
    )
    @classmethod
    def validate_optional_text(cls, value: Any) -> str | None:
        if value is None:
            return None
        text = str(value).strip()
        return text or None

    @field_validator("holes", "woodwork", mode="before")
    @classmethod
    def validate_list_of_dicts(cls, value: Any) -> list[dict[str, Any]]:
        if not isinstance(value, list):
            return []
        return [item for item in value if isinstance(item, dict)]


class DinaboxProjetoConcluidoEventoSchema(DinaboxBaseModel):
    """Contrato minimo para enfileirar importacao ao concluir projeto no setor Projetos."""

    project_id: str
    project_customer_id: str = ""
    project_description: str = ""
    origem: str = "projetos_concluido"
    prioridade: int = 100

    @field_validator("project_id", mode="before")
    @classmethod
    def validate_project_id(cls, value: Any) -> str:
        text = str(value or "").strip()
        if not text:
            raise ValueError("Campo obrigatorio vazio.")
        return text

    @field_validator("project_customer_id", "project_description", "origem", mode="before")
    @classmethod
    def validate_optional_text(cls, value: Any) -> str:
        return str(value or "").strip()

    @field_validator("prioridade", mode="before")
    @classmethod
    def validate_prioridade(cls, value: Any) -> int:
        try:
            parsed = int(value)
        except (TypeError, ValueError):
            return 100
        if parsed < 1:
            return 1
        if parsed > 999:
            return 999
        return parsed
