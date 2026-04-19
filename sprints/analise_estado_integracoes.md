# 📊 Análise do App Integrações - Estado Atual

**Data**: Abril/2026  
**Escopo**: App `integracoes` (3.974 linhas, 38 arquivos Python)  
**Foco**: Integração com API Dinabox

---

## 1. VISÃO GERAL

### 1.1 Propósito

O app `integracoes` é o **hub central de interoperabilidade** entre o Tarugo e o Dinabox (software de design de móveis). Suas responsabilidades:

```
Dinabox (SaaS externo)
    ↓
DinaboxAPIClient (HTTP requests)
    ↓
DinaboxApiService (tipos/schemas)
    ↓
Services + Selectors (lógica de negócio)
    ↓
3 views setorizadas (Operacional, Logístico, Administrativo)
    ↓
Tarugo Apps (PCP, Estoque, Bipagem)
```

### 1.2 Módulos Principais

| Módulo | Linhas | Responsabilidade | Status |
|--------|--------|------------------|--------|
| `dinabox/client.py` | ~400 | Cliente HTTP autenticado (Bearer token) | ✅ Produção |
| `dinabox/api_service.py` | ~500 | Wrapper tipado da API Dinabox | ✅ Produção |
| `dinabox/service.py` | ~400 | Conversão JSON → 3 views Pydantic | ✅ Produção |
| `dinabox/schemas/` | ~800 | Schemas Pydantic (operacional, logístico, admin) | ✅ Produção |
| `services.py` | ~200 | Lógica de negócio (material mapping, clientes) | ✅ Produção |
| `services_importacao.py` | ~300 | Fila de importação de projetos | ✅ Produção |
| `models.py` | ~200 | 3 modelos Django (MapeamentoMaterial, DinaboxClienteIndex, DinaboxImportacaoProjeto) | ✅ Produção |
| `views.py` | ~700 | 20+ endpoints HTTP (conexão, projetos, clientes, importação) | ✅ Produção |
| `management/commands/` | ~200 | 2 commands: manifesto + processador de fila | ✅ Produção |

---

## 2. ARQUITETURA ATUAL

### 2.1 Estrutura de Camadas

```
┌─────────────────────────────────────────────────────────┐
│                   Views (Django)                         │
│  dinabox_conectar, dinabox_projetos_list, etc          │
└─────────────────────────────────────────────────────────┘
                          ↓
┌─────────────────────────────────────────────────────────┐
│              API Service Layer                           │
│  DinaboxApiService (parse response → Pydantic)          │
└─────────────────────────────────────────────────────────┘
                          ↓
┌─────────────────────────────────────────────────────────┐
│            Client Layer (HTTP + Auth)                    │
│  DinaboxAPIClient (Bearer token, retry, cache)          │
└─────────────────────────────────────────────────────────┘
                          ↓
                   Dinabox API (SaaS)
```

### 2.2 Schemas Pydantic (3 visões)

A arquitetura implementa **separação por domínio** via schemas:

```
DinaboxProjectOperacional
├─ Focado em: Fabricação, usinagem, rastreabilidade
├─ Consome: PartOperacional (peças com furos, bordas)
├─ Para: apps/pcp, apps/bipagem
├─ Exemplo de campo: holes (furação), edges (bordas)
└─ Status: ✅ Implementado

DinaboxProjectLogistico
├─ Focado em: Expedição, viagens, tracking
├─ Consome: PartLogistico (peso, volume, embalagem)
├─ Para: apps/logistica (futuro)
├─ Exemplo de campo: weight (kg), volume (m³)
└─ Status: ⏳ Implementado mas não consumido

DinaboxProjectAdministrativo
├─ Focado em: BOM, custos, compras, fornecimentos
├─ Consome: PartAdministrativo (preço, custo, markup)
├─ Para: apps/compras, apps/financeiro (futuro)
├─ Exemplo de campo: factory_price, buy_price
└─ Status: ⏳ Implementado mas não consumido
```

**Dados Brutos** → **DinaboxIntegrationService.process_raw_json()** → **3 Views Pydantic** → **Consumidores Tipados**

### 2.3 Fluxo de Dados

#### 2.3.1 Buscar um Projeto (simplificado)

```
Frontend (views.py:dinabox_projeto_detail)
    ↓ POST /integracoes/dinabox/projeto/<project_id>/
    ↓
DinaboxApiService.get_project_detail(project_id)
    ↓
DinaboxAPIClient.get_project(project_id)
    ↓ GET /api/v1/project?project_id=0108966599 (Bearer token)
    ↓
Dinabox API → Raw JSON
    ↓
JSON → DinaboxProjectDetail (Pydantic validado)
    ↓
(opcional) parse_project_detail() → normalização extra
    ↓
render("projeto_detail.html", {"projeto": projeto})
```

#### 2.3.2 Importar Projeto (async via fila)

```
Frontend/Webhook (dinabox_enfileirar_projeto_concluido)
    ↓ POST /integracoes/dinabox/enfileirar (com payload JSON)
    ↓
DinaboxImportacaoProjetoService.enfileirar_importacao_por_evento()
    ↓
DinaboxImportacaoProjeto.objects.create(status=PENDENTE, prioridade=100)
    ↓
(separadamente) management command (processar_importacoes_dinabox)
    ↓
Busca items com status=PENDENTE, prioridade DESC
    ↓
Para cada item:
    1. Chama get_project_detail() → DinaboxProjectOperacional
    2. Valida com Pydantic
    3. Passa para PCP via app.pcp.services.processar_projeto_dinabox()
    4. Marca status=CONCLUIDO ou ERRO
```

---

## 3. ESTADO ATUAL DETALHADO

### 3.1 O Que Funciona Bem ✅

#### 3.1.1 Cliente HTTP (DinaboxAPIClient)

**Força**: Autenticação robusta com cache global de token

```python
class DinaboxAPIClient:
    _GLOBAL_TOKEN_CACHE = {}  # Cache compartilhado entre instâncias
    
    def __init__(self, token=None):
        self._session = requests.Session()  # Conexão reutilizável
        self._token_cache = None
        self._token_expira_em = None
    
    def obter_token(self, force_refresh=False):
        # 1. Verifica cache global
        # 2. Se expirado, autentica com username/password
        # 3. Salva no cache global
        # 4. Configura Authorization header
```

**Benefícios**:
- ✅ Bearer token automático (sem gerenciar manualmente)
- ✅ Cache global evita N autenticações em N requisições
- ✅ Suporta força refresh (botão no admin)
- ✅ Fallback: aceita token explícito se fornecido

#### 3.1.2 Três Visões Separadas (Pydantic)

```python
# Operacional: para fabricação
PartOperacional(
    id, ref, name, count,
    width, height, thickness,  # Dimensões críticas
    holes: PartHoles,  # Furação
    edge_left, edge_right, edge_top, edge_bottom,  # Bordas
    code_a, code_b, code_a2, code_b2  # Bipagem
)

# Logístico: para expedição
PartLogistico(
    id, ref, name,
    weight, volume,  # Crítico para transporte
    packaging_type, packaging_qty
)

# Administrativo: para compras
PartAdministrativo(
    id, ref, name,
    factory_price, buy_price, sale_price,  # Financeiro
    supplier_id, supplier_name
)
```

**Benefício**: Cada app consome apenas os campos que precisa (sem poluição).

#### 3.1.3 Mapeamento Material (MapeamentoMaterial)

```python
class MapeamentoMaterial(models.Model):
    nome_dinabox = models.CharField(unique=True)  # "Nogueira Pecan"
    produto = models.ForeignKey(Produto, ...)  # Estoque
    fator_conversao = models.DecimalField(default=1.0)  # Margem
    
    @staticmethod
    def obter_mapeamento(nome_dinabox: str) -> MapeamentoMaterial:
        return MapeamentoMaterial.objects.filter(
            nome_dinabox=nome_dinabox, ativo=True
        ).select_related('produto').first()
```

**Implementação do Gêmeo Digital**: Consumo em Dinabox → atualiza Estoque via fator_conversao.

#### 3.1.4 Índice de Clientes (DinaboxClienteIndex)

```python
class DinaboxClienteIndex(models.Model):
    customer_id = models.CharField(unique=True, db_index=True)
    customer_name = models.CharField()
    customer_name_normalized = models.CharField(db_index=True)  # Busca rápida
    customer_type = models.CharField(db_index=True)  # PF/PJ
    customer_status = models.CharField(db_index=True)  # Ativo/Inativo
    customer_emails_text = models.TextField()
    customer_phones_text = models.TextField()
    raw_payload = models.JSONField()  # Guarda dados brutos
    synced_at = models.DateTimeField(auto_now=True, db_index=True)
    
    # Busca normalizada
    DinaboxClienteIndex._normalize("JOÃO SILVA") → "joao silva"
```

**Benefício**: Índice local permite:
- ✅ Busca rápida sem chamar Dinabox toda vez
- ✅ Cache de clientes sincronizado periodicamente
- ✅ Normalização inteligente (case-insensitive, espaços extras)

#### 3.1.5 Fila de Importação (DinaboxImportacaoProjeto)

```python
class DinaboxImportacaoProjeto(models.Model):
    project_id = models.CharField(db_index=True)
    status = StatusImportacaoProjeto.PENDENTE  # PENDENTE → PROCESSANDO → CONCLUIDO/ERRO
    prioridade = models.PositiveSmallIntegerField(default=100)  # Ordenação
    tentativas = models.PositiveIntegerField(default=0)  # Retry tracking
    payload_bruto = models.JSONField()  # Dados originais (audit)
    resultado_resumo = models.JSONField()  # Resultado final
    ultimo_erro = models.TextField()  # Mensagem de erro
    
    class Meta:
        ordering = ["prioridade", "criado_em"]  # Processa prioritários primeiro
```

**Benefício**: Sistema resiliente de importação:
- ✅ Webhook dispara rapidamente (202 Accepted)
- ✅ Background job processa depois (sem bloquear frontend)
- ✅ Retry automático com tentativas limitadas
- ✅ Auditoria completa (payload bruto + resultado)

---

### 3.2 Problemas / Débitos Técnicos ⚠️

#### 3.2.1 Views (700 linhas) - Falta de Padrão

**Problema**: Views mistura lógica de negócio, acesso a BD e renderização HTML

```python
# views.py:dinabox_cliente_detail (exemplo)
@login_required
def dinabox_cliente_detail(request, customer_id: str):
    # 1. Validação de permissão (repetida 20 vezes)
    if not _user_pode_testar_integracoes(request.user):
        messages.error(request, "...")
        return redirect(...)
    
    # 2. Lógica de negócio inline
    try:
        service = _obter_servico_dinabox()
        customer = service.get_customer_detail(customer_id)
    except (DinaboxAuthError, DinaboxRequestError) as exc:
        messages.error(request, f"Falha: {exc}")
        return redirect(...)
    
    # 3. Transformação de dados (extração inline)
    initial = _extract_customer_form_initial(customer)
    
    # 4. Renderização
    return render(request, "template.html", {...})
```

**Impacto**:
- ❌ Difícil testar (tudo acoplado a Django)
- ❌ Repetição de permissão + try/catch em 20 funções
- ❌ Funções `_extract_*` e `_normalize_*` espalhadas
- ❌ Impossível reutilizar fora do contexto HTTP

**Solução esperada**: Mover lógica para Services, deixar views apenas como adaptadores HTTP.

#### 3.2.2 Services_Importacao.py - Lógica Escondida

```python
# services_importacao.py:enfileirar_importacao_por_evento
@staticmethod
def enfileirar_importacao_por_evento(payload: dict) -> DinaboxImportacaoProjeto:
    # 1. Valida payload (Pydantic - bom)
    # 2. Extrai campos e cria item na fila
    # 3. Retorna item criado
```

**Problemas**:
- ❌ Lógica de processamento da fila está no management command
- ❌ Não há interface clara entre `enfileirar` e `processar`
- ❌ Retry logic está espalhada em múltiplos lugares
- ⚠️ Transações não estão explícitas

#### 3.2.3 Parsers (dinabox/parsers/) - Duplicação

Existem dois parsers para a mesma tarefa:

```
dinabox/parsers/
├── customer_detail.py (normaliza cliente para frontend)
└── project_detail.py (extrai peças/módulos para frontend)

dinabox/schemas/
├── dinabox_operacional.py (PartOperacional com tipos)
├── dinabox_logistico.py (PartLogistico)
└── dinabox_administrativo.py (PartAdministrativo)
```

**Problema**: Dois "formatos de verdade":
- Schemas Pydantic (para validação + tipagem)
- Parsers dict (para transformação em frontend)

**Esperado**: Unificar em um único fluxo: JSON → Pydantic → dict (se necessário)

#### 3.2.4 Falta de Logging Estruturado

```python
# Não há rastreamento de:
# - Qual visualização (Operacional/Logístico/Admin) foi usada
# - Quantos erros de validação ocorreram
# - Tempo de resposta por endpoint
# - Tentativas de retry da fila

# Apenas messages.success/error (frontend-facing)
# Nada no logger do Django
```

#### 3.2.5 Ausência de Testes Unitários

```
integracoes/tests.py  ← vazio ou apenas smoke tests
```

**Impacto**:
- ❌ Impossível garantir que refatorações não quebrem
- ❌ Difícil validar parsing JSON complexo
- ❌ Sem cobertura para retry logic

---

## 4. INTEGRAÇÃO COM OUTROS APPS

### 4.1 PCP (Principal consumer)

```
integracoes/dinabox/service.py
    ↓
DinaboxIntegrationService.get_operacional_view()
    ↓
DinaboxProjectOperacional (Pydantic)
    ↓
apps/pcp/services/pcp_service.py
    ↓
processar_projeto_dinabox(project_id)
    ↓
Gera roteiros, planos de corte
    ↓
XLS para CutPlanning
```

**Status**: ✅ Funcionando mas pode ser melhorado
- Hoje: DataFrame intermediário (sem tipagem)
- Futuro (conforme refatoração PCP): Pydantic → PecaOperacional

### 4.2 Estoque (Planejado - Mapeamento Material)

```
MapeamentoMaterial
    ↓
Quando PCP consome material Dinabox:
    ↓
Material "Nogueira Pecan" (Dinabox)
    → Mapeado para Produto "Nogueira Pecan 18mm" (Estoque)
    → Fator 1.1 (10% margem de perda)
    ↓
Estoque atualiza consumo
```

**Status**: ⏳ Infraestrutura pronta, falta integração em PCP

### 4.3 Bipagem (Planejado)

```
DinaboxProjectOperacional.holes (furação)
    ↓
apps/bipagem/services
    ↓
Importar códigos de furação
```

**Status**: ⏳ Schema pronto, falta consumidor

---

## 5. PROBLEMAS CRÍTICOS POR ORDEM DE SEVERIDADE

### 🔴 CRÍTICO

#### 5.1 Sem Logging Estruturado

```
Impacto: Impossível debugar problemas em produção
Exemplo: "Por que a importação falhou?" → só tem status ERRO, sem mensagem clara
Solução: Adicionar Python logging + Sentry/LogDNA
```

#### 5.2 Validação Inconsistente

```
Impacto: Alguns campos opcionais quando deveriam ser obrigatórios
Exemplo: customer_id pode ser None em alguns fluxos
Solução: Revisar todos os Pydantic models, adicionar Field(...) obrigatório
```

---

### 🟠 ALTO

#### 5.3 Falta de Testes

```
Impacto: Risco de regressão em refatorações
Solução: Implementar testes unitários para:
  - DinaboxAPIClient (mock requests)
  - DinaboxApiService (mock client)
  - Services (mock models)
```

#### 5.4 Lógica Espalhada em Views

```
Impacto: Reutilização impossível fora HTTP
Exemplo: Não posso chamar "sincronizar clientes" de um task runner
Solução: Services para toda lógica, views apenas chamam services
```

---

### 🟡 MÉDIO

#### 5.5 Duplicação Parsers vs Schemas

```
Impacto: Manutenção difícil quando Dinabox muda
Solução: Unificar em um único fluxo Pydantic
```

#### 5.6 Fila de Importação Minimalista

```
Impacto: Sem circuit breaker, sem backoff exponencial
Solução: Implementar retry policy mais sofisticada
```

---

## 6. RECOMENDAÇÕES ARQUITETURAIS

### 6.1 Padrão Proposto (Seguindo Tarugo)

```
┌──────────────────────────────────┐
│    API Views (HTTP adapters)     │
│  - Validação de permissão        │
│  - Extração de parametros        │
│  - Renderização HTTP/JSON        │
└──────────┬───────────────────────┘
           ↓
┌──────────────────────────────────┐
│ Services (Regras de negócio)     │
│  - Orquestração de operações     │
│  - Uso de Selectors/Repositories │
│  - Transações explícitas         │
└──────────┬───────────────────────┘
           ↓
┌──────────────────────────────────┐
│  Selectors/Repositories          │
│  - Queries complexas             │
│  - CRUD de modelos               │
│  - Cache local (índices)         │
└──────────┬───────────────────────┘
           ↓
┌──────────────────────────────────┐
│  Models (Django ORM)             │
└──────────┬───────────────────────┘
           ↓
┌──────────────────────────────────┐
│ External (Dinabox API)           │
│  - HTTP client                   │
│  - Autenticação                  │
│  - Schemas Pydantic (validação)  │
└──────────────────────────────────┘
```

### 6.2 Refatoração de Views

**Hoje**:
```python
@login_required
def dinabox_cliente_detail(request, customer_id):
    _user_pode_testar_integracoes(request.user)  # 1. Permissão
    service = _obter_servico_dinabox()  # 2. Serviço
    customer = service.get_customer_detail(customer_id)  # 3. Lógica
    initial = _extract_customer_form_initial(customer)  # 4. Transformação
    return render(...)  # 5. Render
```

**Depois**:
```python
@login_required
@require_permission("integracoes.view_customer")
def dinabox_cliente_detail(request, customer_id):
    # View é apenas adapter HTTP
    customer_view = DinaboxClienteService.obter_detalhes(customer_id)
    return render(request, "template.html", {
        "customer": customer_view.dict(),
    })
```

### 6.3 Adicionar Logging

```python
import logging
logger = logging.getLogger("integracoes.dinabox")

logger.info(
    "importacao_iniciada",
    extra={
        "project_id": project_id,
        "tentativa": tentativa,
        "timestamp": datetime.now().isoformat(),
    }
)

logger.error(
    "falha_validacao",
    exc_info=True,
    extra={"error_type": "validation_error"}
)
```

### 6.4 Adicionar Testes

```python
# tests/test_dinabox_client.py
@pytest.fixture
def mock_client():
    with patch('requests.Session.get') as mock:
        mock.return_value.json.return_value = {"token": "abc123"}
        yield mock

def test_get_token_caches(mock_client):
    client1 = DinaboxAPIClient()
    token1 = client1.obter_token()
    
    client2 = DinaboxAPIClient()
    token2 = client2.obter_token()
    
    assert token1 == token2
    assert mock_client.call_count == 1  # Chamou uma única vez

# tests/test_material_mapping.py
def test_mapear_material():
    mapeamento = MapeamentoMaterial.objects.create(
        nome_dinabox="Nogueira Pecan",
        produto=produto,
        fator_conversao=1.1
    )
    
    encontrado = MaterialMappingService.obter_mapeamento("Nogueira Pecan")
    assert encontrado.fator_conversao == 1.1
```

---

## 7. RECOMENDAÇÕES POR SEVERIDADE

| Ação | Severidade | Esforço | Impacto | Prazo |
|------|-----------|--------|--------|-------|
| Adicionar logging estruturado | 🔴 Crítico | 2-3h | Alto | Imediato |
| Implementar testes básicos | 🔴 Crítico | 8-10h | Alto | 1 semana |
| Refatorar views para services | 🟠 Alto | 16h | Médio | 2 semanas |
| Unificar parsers/schemas | 🟠 Alto | 6-8h | Médio | 2 semanas |
| Circuit breaker fila importação | 🟡 Médio | 4-6h | Médio | 3 semanas |
| Integração com Estoque (consumir mapeamento) | 🟡 Médio | 8h | Alto | 4 semanas |

---

## 8. CHECKLIST DE SAÚDE

| Item | Status | Notas |
|------|--------|-------|
| Autenticação Dinabox | ✅ | Token em cache, refresh automático |
| Parse JSON → Pydantic | ✅ | 3 visões separadas, validação robusta |
| Mapeamento Material | ⏳ | Criado mas não consumido por PCP |
| Índice de Clientes | ✅ | Sincronização funciona, busca rápida |
| Fila de Importação | ⚠️ | Básica, sem retry exponencial |
| Testes unitários | ❌ | Nenhum teste automatizado |
| Logging estruturado | ❌ | Apenas messages.success/error (frontend) |
| Documentação | ⚠️ | Código documentado mas arquitetura pouco clara |
| Tratamento de erros | ⚠️ | Básico, mensagens genéricas |
| Performance | ✅ | Cache de token + índice local de clientes |

---

## 9. CONCLUSÃO

### Pontos Fortes

1. **Separação de responsabilidades**: Schemas Pydantic bem estruturados
2. **Autenticação robusta**: Cache global de token
3. **Escalabilidade inicial**: Fila permite processamento async
4. **Tipagem**: Schemas para 3 visões diferentes

### Pontos Fracos

1. **Falta de testes**: Nenhum teste automatizado
2. **Views com lógica**: Impossível reutilizar fora HTTP
3. **Logging minimalista**: Difícil debugar em produção
4. **Parsers duplicados**: Confusão entre schemas e transformação

### Caminho para Maturidade

```
Curto prazo (1-2 semanas):
├─ Adicionar logging estruturado
├─ Implementar tests básicos
└─ Refatorar views → services

Médio prazo (3-4 semanas):
├─ Unificar parsers/schemas
├─ Melhorar retry policy
└─ Integrar com Estoque (mapeamento material)

Longo prazo (1-2 meses):
├─ Circuit breaker
├─ Webhooks em ambos sentidos (Tarugo → Dinabox)
└─ Sincronização incremental (não apenas full-sync)
```

O app é **funcional em produção** mas precisar de **refatoração técnica** para melhor manutenibilidade.
