'''
Este módulo define o Pydantic BaseModel padrão para todos os schemas de integração do Dinabox, garantindo uma configuração consistente.
'''
from pydantic import BaseModel, ConfigDict

class DinaboxBaseModel(BaseModel):
    """
    Modelo base Pydantic com configurações compartilhadas para todos os schemas do Dinabox.

    A configuração inclui:
    - `populate_by_name=True`: Permite que os campos sejam preenchidos por seus nomes de alias.
    - `extra="allow"`: Permite campos extras no JSON de entrada que não estão definidos no schema.
    - `arbitrary_types_allowed=True`: Permite o uso de tipos arbitrários nos campos do modelo.
    """
    model_config = ConfigDict(
        populate_by_name=True,
        extra="allow",
        arbitrary_types_allowed=True
    )
