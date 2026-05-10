# apps/integracoes/dinabox/schemas/base.py
from pydantic import BaseModel, ConfigDict

class DinaboxBaseModel(BaseModel):
    """
    Modelo base Pydantic com configurações compartilhadas para todos os schemas do Dinabox.
    """
    model_config = ConfigDict(
        populate_by_name=True,
        extra="allow",
        arbitrary_types_allowed=True
    )
