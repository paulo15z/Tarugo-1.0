from pydantic import BaseModel
from datetime import datetime


class Metadata(BaseModel):
    origem: str = "dinabox"
    data_importacao: datetime
    versao: int = 1
