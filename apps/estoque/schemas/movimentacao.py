from pydantic import BaseModel, ConfigDict, field_validator, model_validator

from apps.estoque.domain.tipos import TipoMovimentacao

ORIGENS_RESERVA = {"pcp", "manual", "integracao"}


class MovimentacaoCreateSchema(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    produto_id: int
    tipo: TipoMovimentacao
    quantidade: int
    espessura: int | None = None
    observacao: str | None = None

    @field_validator("quantidade")
    @classmethod
    def quantidade_positiva(cls, value: int) -> int:
        if value <= 0:
            raise ValueError("Quantidade deve ser maior que zero.")
        return value

    @field_validator("espessura")
    @classmethod
    def espessura_positiva(cls, value: int | None) -> int | None:
        if value is not None and value <= 0:
            raise ValueError("Espessura deve ser maior que zero.")
        return value


class AjusteLoteSchema(BaseModel):
    movimentacoes: list[MovimentacaoCreateSchema]

    @field_validator("movimentacoes")
    @classmethod
    def lista_nao_vazia(cls, value: list[MovimentacaoCreateSchema]) -> list[MovimentacaoCreateSchema]:
        if not value:
            raise ValueError("A lista de movimentacoes nao pode estar vazia.")
        return value


class ReservaCreateSchema(BaseModel):
    produto_id: int
    quantidade: int
    espessura: int | None = None
    referencia_externa: str | None = None
    lote_pcp_id: str | None = None
    modulo_id: str | None = None
    ambiente: str | None = None
    origem_externa: str = "pcp"
    observacao: str | None = None

    @field_validator("quantidade")
    @classmethod
    def quantidade_reserva_positiva(cls, value: int) -> int:
        if value <= 0:
            raise ValueError("Quantidade da reserva deve ser positiva.")
        return value

    @field_validator("origem_externa")
    @classmethod
    def origem_valida(cls, value: str) -> str:
        origem = (value or "").strip().lower()
        if origem not in ORIGENS_RESERVA:
            raise ValueError(f"Origem invalida. Use uma de: {', '.join(sorted(ORIGENS_RESERVA))}.")
        return origem

    @model_validator(mode="after")
    def contexto_pcp(self):
        origem = self.origem_externa
        lote_id = self.lote_pcp_id
        referencia = self.referencia_externa

        if origem == "pcp" and not lote_id:
            raise ValueError("Lote PCP deve ser informado quando a origem for PCP.")
        if origem != "pcp" and not referencia:
            raise ValueError("Referencia externa eh obrigatoria para reservas manuais ou integradas.")
        return self
