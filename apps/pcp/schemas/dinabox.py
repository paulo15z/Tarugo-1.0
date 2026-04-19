from decimal import Decimal
from typing import Optional
from pydantic import BaseModel, Field, ConfigDict

class MaterialDInabox(BaseModel):
    id: str
    name: str
    width: Decimal = Field(..., gt=0)
    height: Decimal = Field(..., gt=0)
    vein: bool = False

    model_config = ConfigDict(from_attributes=True)

class EdgeDinabox(BaseModel):
    