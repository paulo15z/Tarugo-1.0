from datetime import datetime
from typing import List, Optional, Dict
from pydantic import BaseModel

class ResumoPecas(BaseModel):
    total_entrada: int
    total_saida: int
    ripas_geradas: int
    pecas_consolidadas: int
    variacao: int

class ProcessarRoteiroOutput(BaseModel):
    processamento_id: str
    projeto_id: str
    cliente_nome: str
    data_processamento: datetime

    resumo: ResumoPecas
    pecas_finais: List[dict] #serialized
    arquivo_xls: Optional[str] = None
    auditoria: Optional[List[dict]] = None

    