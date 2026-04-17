from pydantic import BaseModel


class Chapa(BaseModel):
    material: str

    largura: int
    altura: int
    espessura: int

    area_total: float
    area_disponivel: float

    identificador: str | None = None
