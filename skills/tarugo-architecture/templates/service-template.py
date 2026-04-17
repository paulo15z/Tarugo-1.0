# apps/{app_name}/services/{nome}_service.py
from pydantic import BaseModel
from typing import Optional

class {InputClass}(BaseModel):
    # defina os campos de entrada aqui
    ...

class {OutputClass}(BaseModel):
    sucesso: bool
    mensagem: str
    # outros campos de retorno

class {ServiceClass}:

    @staticmethod
    def {metodo_principal}(data: {InputClass}) -> {OutputClass}:
        """Descreva aqui o que o método faz"""
        # TODO: implementar lógica de negócio
        ...