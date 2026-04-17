# Refatoração do Módulo PCP

## Situação Atual
- Código principal ainda em `pcp/services/pcp_service.py` (legado)
- Nova estrutura sendo construída em `processamento_service.py`
- Integração com `bipagem` via `importar_de_pcp()`

## Objetivo da Refatoração
Transformar PCP em um módulo que siga 100% o padrão Tarugo.

### Passos Recomendados

1. Criar `schemas/` com Pydantic models para input/output do processamento
2. Migrar lógica de `calcular_roteiro()`, `determinar_plano_de_corte()` e `consolidar_ripas()` para Services
3. Manter `utils/` apenas para funções puras de processamento de arquivos (pandas, xlwt)
4. Atualizar views e API para chamar o novo Service
5. Manter compatibilidade durante migração (usar feature flag se necessário)

## Exemplo de Service Futuro

```python
# services/processamento_service.py
from pydantic import BaseModel
from apps.pcp.schemas import ProcessarRoteiroInput, ProcessarRoteiroOutput

class ProcessamentoPCPService:
    @staticmethod
    def processar_roteiro(input_data: ProcessarRoteiroInput) -> ProcessarRoteiroOutput:
        # toda lógica aqui
        ...
Leia também references/boas-praticas.md para mais detalhes.