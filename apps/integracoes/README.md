# App Integracoes - Tarugo 1.1

## 🎯 Objetivo

O app `integracoes` é responsável por **receber, validar e processar dados do Dinabox**, transformando-os em três visões setorizadas: **Operacional**, **Logístico** e **Administrativo**.

Funciona como um **gateway de dados** entre o Dinabox (sistema de design moveleiro) e os demais apps do Tarugo (PCP, Estoque, Bipagem, etc).

---

## 🏗️ Arquitetura

Segue rigorosamente o padrão **API-First** definido em `tarugo-architecture`:

```
Request → API View → Service (Pydantic) → Selector → Model → Response
```

### Camadas

| Camada | Arquivo | Responsabilidade |
|--------|---------|-----------------|
| **Models** | `models.py` | ORM apenas (sem lógica) |
| **Services** | `services.py` | Regras de negócio |
| **Selectors** | `selectors.py` | Consultas reutilizáveis |
| **Schemas** | `dinabox/schemas/` | Validação Pydantic |
| **API** | `dinabox/api/` | Camada HTTP (DRF) |

---

## 📂 Estrutura de Arquivos

```
apps/integracoes/
├── models.py                    # ORM (MapeamentoMaterial, DinaboxClienteIndex)
├── services.py                  # Lógica de negócio
├── selectors.py                 # Consultas ao banco
├── admin.py                     # Interface Django Admin
├── apps.py                      # Configuração do app
├── migrations/                  # Migrações do banco
├── dinabox/
│   ├── client.py                # Cliente HTTP da API Dinabox
│   ├── schemas/
│   │   ├── base.py              # DinaboxBaseModel (Pydantic)
│   │   ├── dinabox_operacional.py   # Visão operacional
│   │   ├── dinabox_logistico.py     # Visão logística
│   │   └── dinabox_administrativo.py # Visão administrativa
│   ├── api/
│   │   ├── views.py             # Endpoints DRF
│   │   ├── serializers.py       # Serializers DRF
│   │   └── urls.py              # Rotas
│   └── parsers/                 # (Vazio por enquanto; para parsers futuros)
└── management/
    └── commands/
        └── dinabox_manifesto.py # Comando para testar integração
```

---

## 🔄 Fluxo de Dados

### 1. Processamento de Projeto JSON

```python
# Cliente envia JSON bruto do Dinabox
POST /api/integracoes/dinabox/projetos/processar/
{
  "project_id": "0310366465",
  "project_description": "COZINHA",
  "project_customer_id": "2539544",
  ...
}

# Retorna 3 visões validadas
{
  "operacional": { ... },    # Fabricação, usinagem, rastreabilidade
  "logistico": { ... },      # Expedição, viagens, tracking
  "administrativo": { ... }  # BOM, custos, compras
}
```

### 2. Mapeamento de Materiais

```python
# Criar mapeamento (Dinabox → Estoque)
POST /api/integracoes/mapeamentos/
{
  "nome_dinabox": "Carvalho Poro - ARAUCO",
  "produto": 123,
  "fator_conversao": 1.1
}

# Usar para consumo digital
mapeamento = MaterialMappingService.obter_mapeamento("Carvalho Poro - ARAUCO")
consumo_real = consumo_digital * mapeamento.fator_conversao
```

### 3. Sincronização de Clientes

```python
# Sincronizar cliente individual
cliente_data = {
  "customer_id": "2539544",
  "customer_name": "1067 - THIAGO E GABY",
  "customer_type": "pf",
  "customer_status": "on"
}
DinaboxClienteService.sincronizar_cliente(cliente_data)

# Buscar cliente
cliente = DinaboxClienteSelector.get_by_customer_id("2539544")
```

---

## 📊 Modelos de Dados

### MapeamentoMaterial

Vínculo entre materiais Dinabox e Produtos do Estoque. **Essencial para o Gêmeo Digital**.

```python
class MapeamentoMaterial(models.Model):
    nome_dinabox: str          # Ex: "Carvalho Poro - ARAUCO"
    produto: ForeignKey        # Produto no Estoque
    fator_conversao: Decimal   # Multiplicador para consumo
    ativo: bool                # Soft-delete
    criado_em: DateTime
    atualizado_em: DateTime
```

### DinaboxClienteIndex

Índice local de clientes para busca rápida. Sincronizado via API Dinabox.

```python
class DinaboxClienteIndex(models.Model):
    customer_id: str           # ID único Dinabox
    customer_name: str         # Nome do cliente
    customer_name_normalized: str  # Para busca case-insensitive
    customer_type: str         # "pf" ou "pj"
    customer_status: str       # "on", "off", etc
    customer_emails_text: str  # Emails (texto)
    customer_phones_text: str  # Telefones (texto)
    raw_payload: JSONField     # Dados brutos Dinabox
    synced_at: DateTime        # Última sincronização
```

---

## 🔌 API Endpoints

### Processamento de Projetos

| Método | Endpoint | Descrição |
|--------|----------|-----------|
| POST | `/api/integracoes/dinabox/projetos/processar/` | Processa JSON bruto → 3 visões |

### Mapeamentos de Materiais

| Método | Endpoint | Descrição |
|--------|----------|-----------|
| GET | `/api/integracoes/mapeamentos/` | Lista mapeamentos ativos |
| POST | `/api/integracoes/mapeamentos/` | Cria novo mapeamento |
| GET | `/api/integracoes/mapeamentos/{id}/` | Detalhes de um mapeamento |
| PATCH | `/api/integracoes/mapeamentos/{id}/` | Atualiza mapeamento |
| DELETE | `/api/integracoes/mapeamentos/{id}/` | Desativa mapeamento |

### Clientes Dinabox

| Método | Endpoint | Descrição |
|--------|----------|-----------|
| GET | `/api/integracoes/clientes/` | Lista clientes (com filtros) |
| GET | `/api/integracoes/clientes/?search=termo` | Busca por nome |
| GET | `/api/integracoes/clientes/?type=pf` | Filtra por tipo |
| GET | `/api/integracoes/clientes/?status=on` | Filtra por status |
| GET | `/api/integracoes/clientes/{customer_id}/` | Detalhes de um cliente |
| GET | `/api/integracoes/clientes/stats/` | Estatísticas |

---

## 🔧 Services

### DinaboxIntegrationService

Processa dados brutos do Dinabox.

```python
# Processar JSON completo
result = DinaboxIntegrationService.process_raw_json(raw_data)
operacional = result["operacional"]  # DinaboxProjectOperacional
logistico = result["logistico"]      # DinaboxProjectLogistico
administrativo = result["administrativo"]  # DinaboxProjectAdministrativo

# Obter apenas uma visão
operacional = DinaboxIntegrationService.get_operacional_view(raw_data)
```

### MaterialMappingService

Gerencia mapeamentos de materiais.

```python
# Criar mapeamento
mapeamento = MaterialMappingService.criar_mapeamento(
    nome_dinabox="Carvalho Poro - ARAUCO",
    produto_id=123,
    fator_conversao=1.1
)

# Obter mapeamento
mapeamento = MaterialMappingService.obter_mapeamento("Carvalho Poro - ARAUCO")

# Desativar
MaterialMappingService.desativar_mapeamento(mapeamento_id)
```

### DinaboxClienteService

Sincroniza clientes do Dinabox.

```python
# Sincronizar cliente
cliente = DinaboxClienteService.sincronizar_cliente(customer_data)

# Buscar cliente
cliente = DinaboxClienteService.obter_cliente("2539544")

# Buscar por nome
clientes = DinaboxClienteService.buscar_clientes("THIAGO", limit=10)
```

---

## 🔍 Selectors

### MapeamentoMaterialSelector

```python
# Buscar por nome
mapeamento = MapeamentoMaterialSelector.get_by_nome_dinabox("Carvalho Poro")

# Listar ativos
mapeamentos = MapeamentoMaterialSelector.list_ativos()

# Buscar por produto
mapeamentos = MapeamentoMaterialSelector.list_por_produto(produto_id=123)

# Buscar (parcial)
mapeamentos = MapeamentoMaterialSelector.search("carvalho")

# Contar
total = MapeamentoMaterialSelector.count_ativos()
```

### DinaboxClienteSelector

```python
# Buscar por ID
cliente = DinaboxClienteSelector.get_by_customer_id("2539544")

# Listar todos
clientes = DinaboxClienteSelector.list_todos()

# Filtrar por tipo
clientes = DinaboxClienteSelector.list_por_tipo("pf")

# Filtrar por status
clientes = DinaboxClienteSelector.list_por_status("on")

# Buscar por nome
clientes = DinaboxClienteSelector.search_por_nome("THIAGO", limit=10)

# Estatísticas
total = DinaboxClienteSelector.count_total()
por_tipo = DinaboxClienteSelector.count_por_tipo()
por_status = DinaboxClienteSelector.count_por_status()
```

---

## 📋 Schemas Pydantic

### DinaboxProjectOperacional

Visão focada em **fabricação, usinagem e rastreabilidade**.

```python
class DinaboxProjectOperacional(DinaboxBaseModel):
    project_id: str
    project_description: str
    project_customer_id: str
    project_customer_name: str
    
    woodwork: List[ModuleOperacional]  # Módulos para fabricação
    holes_summary: List[ProjectHoleSummary]  # Resumo de hardware
    
    @property
    def total_holes(self) -> int:
        """Total de operações de usinagem"""
    
    def get_manufacturing_summary(self) -> dict:
        """Resumo para planning de fábrica"""
```

### DinaboxProjectLogistico

Visão focada em **expedição, viagens e tracking**.

```python
class DinaboxProjectLogistico(DinaboxBaseModel):
    project_id: str
    project_description: str
    customer: CustomerInfo
    
    woodwork: List[ModuleLogistico]  # Módulos para expedição
    
    @property
    def total_volume_m3(self) -> float:
        """Volume total em m³"""
    
    def get_shipment_summary(self) -> dict:
        """Resumo para criação de viagem"""
```

### DinaboxProjectAdministrativo

Visão focada em **BOM, custos e compras**.

```python
class DinaboxProjectAdministrativo(DinaboxBaseModel):
    project_id: str
    project_description: str
    project_customer_id: str
    project_customer_name: str
    
    woodwork: List[ModuleAdministrativo]  # Módulos para BOM
    
    @property
    def total_materials_cost(self) -> float:
        """Custo total de materiais"""
    
    def get_bom_summary(self) -> Dict[str, Any]:
        """Resumo de BOM para relatórios"""
```

---

## 🚀 Uso Prático

### Exemplo 1: Processar Projeto Completo

```python
from apps.integracoes.services import DinaboxIntegrationService
import json

# Ler JSON do Dinabox
with open('projeto.json') as f:
    raw_data = json.load(f)

# Processar
result = DinaboxIntegrationService.process_raw_json(raw_data)

# Usar visão operacional para PCP
operacional = result["operacional"]
print(f"Total de módulos: {operacional.total_modules}")
print(f"Total de peças: {operacional.total_parts}")
print(f"Total de furos: {operacional.total_holes}")

# Usar visão logística para expedição
logistico = result["logistico"]
print(f"Volume total: {logistico.total_volume_m3} m³")
shipment = logistico.get_shipment_summary()

# Usar visão administrativa para financeiro
administrativo = result["administrativo"]
print(f"Custo total: R$ {administrativo.total_materials_cost}")
bom = administrativo.get_bom_summary()
```

### Exemplo 2: Mapeamento de Materiais

```python
from apps.integracoes.services import MaterialMappingService
from apps.integracoes.selectors import MapeamentoMaterialSelector

# Criar mapeamento
MaterialMappingService.criar_mapeamento(
    nome_dinabox="Carvalho Poro - ARAUCO",
    produto_id=123,
    fator_conversao=1.1  # 10% de margem
)

# Usar no consumo
mapeamento = MapeamentoMaterialSelector.get_by_nome_dinabox("Carvalho Poro - ARAUCO")
if mapeamento:
    consumo_real = consumo_digital * float(mapeamento.fator_conversao)
```

### Exemplo 3: Buscar Cliente

```python
from apps.integracoes.selectors import DinaboxClienteSelector

# Buscar por ID
cliente = DinaboxClienteSelector.get_by_customer_id("2539544")
print(f"Cliente: {cliente.customer_name}")

# Buscar por nome
clientes = DinaboxClienteSelector.search_por_nome("THIAGO", limit=5)
for cliente in clientes:
    print(f"- {cliente.customer_name} ({cliente.customer_type})")
```

---

## 🔐 Segurança

- **Validação dupla:** DRF (entrada HTTP) + Pydantic (regra de negócio)
- **Soft-delete:** Mapeamentos desativados, não deletados (auditoria)
- **Normalização:** Nomes de clientes normalizados para busca segura
- **Isolamento:** Dados brutos preservados em `raw_payload` para debug

---

## 📝 Notas Importantes

1. **Toda lógica de negócio está em `services.py`** — Views apenas chamam services.
2. **Schemas Pydantic validam ao entrar** — Garante tipagem forte.
3. **Selectors centralizam queries** — Reutilizável e testável.
4. **Soft-delete em Mapeamentos** — Nunca deletar, apenas desativar.
5. **Cliente Index é sincronizado** — Não editar manualmente; usar service.

---

## 🔗 Integração com Outros Apps

- **PCP:** Usa `operacional` para planning
- **Estoque:** Usa `administrativo` para BOM e mapeamentos
- **Bipagem:** Usa `operacional` para rastreabilidade
- **Expedição:** Usa `logistico` para shipment

---

**Última atualização:** 11/04/2026  
**Padrão:** Tarugo Architecture (API-First, SaaS Modular)
