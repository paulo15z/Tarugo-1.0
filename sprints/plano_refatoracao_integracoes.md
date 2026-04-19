# 🔧 Plano de Refatoração do App Integracoes

**Objetivo**: Trazer app integracoes para 100% do padrão Tarugo (Service + Pydantic)  
**Duração estimada**: 4-6 semanas  
**Risco**: Baixo (app isolado, com testes podemos migrar gradualmente)

---

## Fase 1: Preparação e Testes (Semana 1-2)

### 1.1 Adicionar Logging Estruturado

**Arquivo**: `integracoes/logging.py` (novo)

```python
import logging
import json
from typing import Any, Dict, Optional

logger = logging.getLogger("tarugo.integracoes")

class DinaboxEventLogger:
    """Logger estruturado para eventos do Dinabox."""
    
    @staticmethod
    def log_auth_attempt(success: bool, username: str, error: Optional[str] = None):
        """Log de tentativa de autenticação."""
        logger.info(
            "auth_attempt",
            extra={
                "success": success,
                "username": username,
                "error": error,
                "module": "dinabox.client"
            }
        )
    
    @staticmethod
    def log_api_call(endpoint: str, method: str, duration_ms: float, status_code: int, error: Optional[str] = None):
        """Log de chamada à API Dinabox."""
        level = logging.INFO if 200 <= status_code < 300 else logging.WARNING
        logger.log(
            level,
            "api_call",
            extra={
                "endpoint": endpoint,
                "method": method,
                "duration_ms": round(duration_ms, 2),
                "status_code": status_code,
                "error": error,
                "module": "dinabox.api_service"
            }
        )
    
    @staticmethod
    def log_validation_error(schema_name: str, data: Dict[str, Any], errors: list):
        """Log de erro de validação Pydantic."""
        logger.warning(
            "validation_error",
            extra={
                "schema": schema_name,
                "error_count": len(errors),
                "errors": str(errors)[:500],  # Truncar para não ficar gigante
                "module": "dinabox.schemas"
            }
        )
    
    @staticmethod
    def log_import_status(project_id: str, status: str, tentativa: int, error: Optional[str] = None):
        """Log de status de importação de projeto."""
        logger.info(
            "import_status",
            extra={
                "project_id": project_id,
                "status": status,
                "tentativa": tentativa,
                "error": error,
                "module": "services_importacao"
            }
        )
```

**Onde integrar**:

```python
# dinabox/client.py
from integracoes.logging import DinaboxEventLogger

class DinaboxAPIClient:
    def obter_token(self, force_refresh=False):
        try:
            # ... código existente
            DinaboxEventLogger.log_auth_attempt(True, self.username)
        except DinaboxAuthError as e:
            DinaboxEventLogger.log_auth_attempt(False, self.username, str(e))
            raise

# dinabox/api_service.py
import time

class DinaboxApiService:
    def get_project_detail(self, project_id: str):
        start = time.time()
        try:
            payload = self.client.get_project(project_id=project_id)
            duration = (time.time() - start) * 1000
            DinaboxEventLogger.log_api_call("/api/v1/project", "GET", duration, 200)
            return DinaboxProjectDetail(**payload)
        except Exception as e:
            duration = (time.time() - start) * 1000
            DinaboxEventLogger.log_api_call("/api/v1/project", "GET", duration, 500, str(e))
            raise
```

### 1.2 Adicionar Testes Básicos

**Arquivo**: `integracoes/tests/` (novo diretório)

```
integracoes/tests/
├─ __init__.py
├─ conftest.py                    # Fixtures compartilhadas
├─ test_dinabox_client.py
├─ test_dinabox_api_service.py
├─ test_material_mapping.py
├─ test_cliente_service.py
└─ test_importacao_service.py
```

**Exemplo: conftest.py**

```python
import pytest
from django.contrib.auth.models import User
from unittest.mock import Mock, patch
from apps.integracoes.dinabox.client import DinaboxAPIClient, DinaboxTokenResult

@pytest.fixture
def mock_dinabox_token():
    """Retorna um token mockado válido."""
    return DinaboxTokenResult(
        token="test_token_abc123",
        expires_in=3600,
        token_type="Bearer",
        user_login="service_account",
        user_display_name="Service Account",
        user_email="service@company.com"
    )

@pytest.fixture
def mock_dinabox_client(mock_dinabox_token):
    """Retorna um cliente Dinabox mockado."""
    with patch.object(DinaboxAPIClient, 'obter_token', return_value=mock_dinabox_token):
        with patch.object(DinaboxAPIClient, '_session') as mock_session:
            mock_session.get.return_value.json.return_value = {}
            client = DinaboxAPIClient(token="test_token")
            client._session = mock_session
            yield client

@pytest.fixture
def test_user():
    """Cria um usuário de teste."""
    return User.objects.create_user(
        username="testuser",
        email="test@example.com",
        password="testpass123"
    )

@pytest.fixture
def test_user_pcp(test_user):
    """User com permissão PCP."""
    from django.contrib.auth.models import Group
    group = Group.objects.get_or_create(name="PCP")[0]
    test_user.groups.add(group)
    return test_user
```

**Exemplo: test_material_mapping.py**

```python
import pytest
from apps.integracoes.models import MapeamentoMaterial
from apps.integracoes.services import MaterialMappingService
from apps.estoque.models.produto import Produto

@pytest.mark.django_db
class TestMaterialMapping:
    
    def test_criar_mapeamento(self):
        """Deve criar mapeamento com fator_conversao."""
        produto = Produto.objects.create(
            nome="Nogueira Pecan 18mm",
            sku="NOG-18"
        )
        
        mapping = MaterialMappingService.criar_mapeamento(
            nome_dinabox="Nogueira Pecan",
            produto_id=produto.id,
            fator_conversao=1.1
        )
        
        assert mapping.nome_dinabox == "Nogueira Pecan"
        assert mapping.produto.id == produto.id
        assert mapping.fator_conversao == 1.1
        assert mapping.ativo == True
    
    def test_obter_mapeamento_ativo(self):
        """Deve retornar apenas mapeamentos ativos."""
        produto = Produto.objects.create(nome="Test Product")
        
        mapping_ativo = MapeamentoMaterial.objects.create(
            nome_dinabox="Material Ativo",
            produto=produto,
            ativo=True
        )
        
        mapping_inativo = MapeamentoMaterial.objects.create(
            nome_dinabox="Material Inativo",
            produto=produto,
            ativo=False
        )
        
        result = MaterialMappingService.obter_mapeamento("Material Ativo")
        assert result.id == mapping_ativo.id
        
        result = MaterialMappingService.obter_mapeamento("Material Inativo")
        assert result is None  # Não retorna inativos
    
    def test_desativar_mapeamento(self):
        """Deve marcar como inativo sem deletar."""
        produto = Produto.objects.create(nome="Test Product")
        mapping = MapeamentoMaterial.objects.create(
            nome_dinabox="Test Material",
            produto=produto
        )
        
        MaterialMappingService.desativar_mapeamento(mapping.id)
        
        mapping.refresh_from_db()
        assert mapping.ativo == False
        assert MapeamentoMaterial.objects.filter(id=mapping.id).exists()
```

**Rodar testes**:
```bash
pytest integracoes/tests/ -v --cov=integracoes
```

---

## Fase 2: Refatorar Views (Semana 2-3)

### 2.1 Padrão: View → Service

**Problema Atual**:
```python
@login_required
def dinabox_cliente_detail(request, customer_id):
    if not _user_pode_testar_integracoes(request.user):  # 1. Permissão inline
        return redirect(...)
    
    try:  # 2. Try/catch inline
        service = _obter_servico_dinabox()
        customer = service.get_customer_detail(customer_id)  # 3. Lógica
    except (DinaboxAuthError, DinaboxRequestError) as exc:
        messages.error(request, f"Falha: {exc}")
        return redirect(...)
    
    initial = _extract_customer_form_initial(customer)  # 4. Transformação
    
    return render(request, "template.html", {
        "customer": customer,
        "form_initial": initial,
    })
```

**Solução Proposta**: Extrair tudo para service

**Novo arquivo**: `integracoes/services/cliente_service.py`

```python
from typing import Optional, Dict, Any
from django.db import transaction
from apps.integracoes.dinabox.api_service import DinaboxApiService
from apps.integracoes.models import DinaboxClienteIndex
from apps.integracoes.logging import DinaboxEventLogger

class DinaboxClienteService:
    """Service para operações de cliente Dinabox."""
    
    def __init__(self):
        self.api_service = DinaboxApiService()
    
    def obter_detalhes(self, customer_id: str) -> DinaboxClienteIndex:
        """
        Busca detalhes do cliente na API e atualiza índice local.
        
        Fluxo:
        1. Tenta buscar na API Dinabox
        2. Sincroniza no índice local
        3. Retorna índice atualizado
        
        Args:
            customer_id: ID do cliente
            
        Returns:
            DinaboxClienteIndex com dados atualizados
            
        Raises:
            ValueError: Se cliente não encontrado
        """
        try:
            # 1. Busca na API
            customer_detail = self.api_service.get_customer_detail(customer_id)
            
            # 2. Atualiza índice local
            cliente_index = self._sincronizar_cliente_local(customer_detail)
            
            # 3. Log
            DinaboxEventLogger.log_cliente_operacao("obter_detalhes", customer_id, True)
            
            return cliente_index
            
        except Exception as e:
            DinaboxEventLogger.log_cliente_operacao("obter_detalhes", customer_id, False, str(e))
            raise
    
    @staticmethod
    @transaction.atomic
    def _sincronizar_cliente_local(customer_detail) -> DinaboxClienteIndex:
        """Sincroniza cliente na tabela local."""
        from apps.integracoes.services import DinaboxClienteService as OldService
        return OldService.sincronizar_cliente(customer_detail.dict())
    
    @staticmethod
    def extrair_form_initial(customer: DinaboxClienteIndex) -> Dict[str, Any]:
        """Extrai dados de cliente para formulário."""
        raw = customer.raw_payload or {}
        pf_data = raw.get("customer_pf_data") or {}
        pj_data = raw.get("customer_pj_data") or {}
        addresses = raw.get("customer_addresses") or []
        first_address = addresses[0] if addresses else {}
        custom_fields = raw.get("custom_fields") or {}
        
        return {
            "customer_cpf": pf_data.get("customer_cpf", ""),
            "customer_cnpj": pj_data.get("customer_cnpj", ""),
            "address_zipcode": first_address.get("zipcode", ""),
            "address_street": first_address.get("address", ""),
            "address_number": first_address.get("number", ""),
            "address_complement": first_address.get("complement", ""),
            "address_district": first_address.get("district", ""),
            "address_city": first_address.get("city", ""),
            "address_state": first_address.get("state", ""),
            "custom_origem": custom_fields.get("origem", "comercial_tarugo"),
        }
```

**View refatorada**: `views.py`

```python
from integracoes.services.cliente_service import DinaboxClienteService

@login_required
@require_permission_decorator("integracoes.view_cliente")  # Decorator novo (veja 2.2)
def dinabox_cliente_detail(request: HttpRequest, customer_id: str):
    """View é apenas adapter HTTP."""
    try:
        service = DinaboxClienteService()
        cliente = service.obter_detalhes(customer_id)
        form_initial = DinaboxClienteService.extrair_form_initial(cliente)
        
        return render(request, "integracoes/dinabox/cliente_detail.html", {
            "customer": cliente,
            "form_initial": form_initial,
        })
    except ValueError as e:
        messages.error(request, f"Cliente não encontrado: {e}")
        return redirect("integracoes:dinabox-clientes-list")
    except (DinaboxAuthError, DinaboxRequestError) as e:
        messages.error(request, f"Erro na API Dinabox: {e}")
        return redirect("integracoes:dinabox-conectar")
```

### 2.2 Decorator de Permissões Reutilizável

**Novo arquivo**: `integracoes/decorators.py`

```python
from functools import wraps
from django.contrib import messages
from django.shortcuts import redirect
from django.http import JsonResponse

def require_permission_decorator(*groups_required):
    """
    Verifica permissão do usuário. Reutilizável e limpo.
    
    Uso:
        @require_permission_decorator("PCP", "TI", "Gestao")
        def minha_view(request):
            ...
    """
    def decorator(view_func):
        @wraps(view_func)
        def wrapper(request, *args, **kwargs):
            user = request.user
            
            if not user or not user.is_authenticated:
                messages.error(request, "Autenticação necessária.")
                return redirect("login")
            
            if user.is_superuser or user.is_staff:
                return view_func(request, *args, **kwargs)
            
            user_groups = set(user.groups.values_list("name", flat=True))
            required_groups = set(groups_required)
            
            if not user_groups & required_groups:
                messages.error(
                    request,
                    f"Acesso restrito a: {', '.join(groups_required)}"
                )
                return redirect("estoque:lista_produtos")
            
            return view_func(request, *args, **kwargs)
        
        return wrapper
    return decorator
```

**Uso**:
```python
@login_required
@require_permission_decorator("PCP", "TI", "Gestao")
def dinabox_cliente_detail(request, customer_id):
    # Permissão já validada automaticamente
    ...
```

### 2.3 Consolidar Helpers

**Novo arquivo**: `integracoes/helpers.py`

```python
from typing import Dict, Any
import json

def extrair_payload_json(request) -> Dict[str, Any]:
    """Extrai JSON do request de forma robusta."""
    if "application/json" not in (request.content_type or ""):
        raise ValueError("Content-Type deve ser application/json")
    
    try:
        body = (request.body or b"").decode("utf-8").strip()
        if not body:
            raise ValueError("Body vazio")
        return json.loads(body)
    except json.JSONDecodeError as e:
        raise ValueError(f"JSON inválido: {e}")

def coerce_page(raw_value) -> int:
    """Converte valor para página (int > 0)."""
    try:
        value = int(raw_value)
        return value if value > 0 else 1
    except (TypeError, ValueError):
        return 1

def only_digits(value: str) -> str:
    """Remove não-dígitos."""
    return "".join(ch for ch in (value or "") if ch.isdigit())

# Usar em views:
payload = extrair_payload_json(request)
page = coerce_page(request.GET.get("p", "1"))
cpf = only_digits(request.POST.get("cpf", ""))
```

---

## Fase 3: Unificar Parsers e Schemas (Semana 3)

### 3.1 Problema Atual

Existe duplicação entre:
- `dinabox/schemas/` (Pydantic com validação)
- `dinabox/parsers/` (funções que transformam JSON em dicts)

**Fluxo atual**:
```
JSON Bruto
    ↓
DinaboxProjectDetail (Pydantic)  ← Valida
    ↓
parse_project_detail()  ← Transforma novamente em dict
    ↓
Dict para frontend
```

### 3.2 Solução: Adicionar Métodos em Schemas

**Exemplo antes**:
```python
# schemas/dinabox_operacional.py
class DinaboxProjectOperacional(DinaboxBaseModel):
    project_id: str
    project_customer_name: str
    woodwork: List[ModuleOperacional]
    # ... apenas validação

# parsers/project_detail.py
def parse_project_detail(detail):
    """Extrai peças e módulos."""
    pecas = []
    for modulo in detail.get("woodwork", []):
        for parte in modulo.get("parts", []):
            pecas.append({
                "id": parte["id"],
                "nome": parte["name"],
                # ... transformação manual
            })
    return {"pecas": pecas, "modulos": [...]}
```

**Exemplo depois**:
```python
# schemas/dinabox_operacional.py
class DinaboxProjectOperacional(DinaboxBaseModel):
    project_id: str
    project_customer_name: str
    woodwork: List[ModuleOperacional]
    
    def para_display(self) -> Dict[str, Any]:
        """Converte para formato de display (frontend)."""
        pecas = []
        modulos = []
        
        for modulo in self.woodwork:
            modulos.append({
                "id": modulo.id,
                "nome": modulo.name,
                "ref": modulo.ref,
            })
            
            for parte in modulo.parts:
                pecas.append({
                    "id": parte.id,
                    "nome": parte.name,
                    "modulo": modulo.ref,
                    "material": parte.material.name if parte.material else None,
                    "bordas": len([e for e in [parte.edge_left, parte.edge_right, parte.edge_top, parte.edge_bottom] if e.name]),
                    "furacoes": parte.total_holes,
                })
        
        return {
            "pecas": pecas,
            "modulos": modulos,
            "cliente_nome": self.project_customer_name,
        }
```

**Usar em view**:
```python
def dinabox_projeto_modulos_pecas(request, project_id):
    service = DinaboxApiService()
    projeto = service.get_project_detail(project_id)  # Pydantic
    
    display_data = projeto.para_display()  # Método do schema
    
    return render(request, "template.html", display_data)
```

**Benefício**: Um único source of truth (o schema Pydantic).

---

## Fase 4: Melhorar Fila de Importação (Semana 4)

### 4.1 Status Quo

```python
class StatusImportacaoProjeto(models.TextChoices):
    PENDENTE = "PENDENTE"
    PROCESSANDO = "PROCESSANDO"
    CONCLUIDO = "CONCLUIDO"
    ERRO = "ERRO"

class DinaboxImportacaoProjeto(models.Model):
    status: StatusImportacaoProjeto
    tentativas: int  # Máximo?
    ultimo_erro: str  # Que tipo de erro?
```

**Problemas**:
- Sem limite de tentativas → pode ficar num loop infinito
- Sem backoff exponencial → bate a API sem parar
- Sem circuit breaker → quando a API cai, tudo falha

### 4.2 Melhorias Propostas

**Novo arquivo**: `integracoes/models/importacao_projeto.py`

```python
from django.db import models
from datetime import datetime, timedelta

class StatusImportacaoProjeto(models.TextChoices):
    PENDENTE = "PENDENTE"
    PROCESSANDO = "PROCESSANDO"
    CONCLUIDO = "CONCLUIDO"
    ERRO_TEMPORARIO = "ERRO_TEMPORARIO"  # Novo: vai retry
    ERRO_PERMANENTE = "ERRO_PERMANENTE"  # Novo: não vai retry
    CANCELADO = "CANCELADO"

class DinaboxImportacaoProjeto(models.Model):
    # Campos existentes...
    status = models.CharField(choices=StatusImportacaoProjeto.choices)
    
    # Novo: controle de retry
    MAX_TENTATIVAS = 5
    tentativas = models.PositiveIntegerField(default=0)
    proxima_tentativa_em = models.DateTimeField(null=True, blank=True)
    
    # Novo: tipos de erro
    tipo_erro = models.CharField(
        max_length=32,
        choices=[
            ("auth_error", "Falha de autenticação"),
            ("validation_error", "Erro de validação"),
            ("api_error", "Erro na API Dinabox"),
            ("timeout", "Timeout"),
            ("outro", "Outro"),
        ],
        blank=True,
        default=""
    )
    
    def pode_reprocessar(self) -> bool:
        """Verifica se item pode ser reprocessado."""
        if self.status == StatusImportacaoProjeto.ERRO_PERMANENTE:
            return False
        if self.tentativas >= self.MAX_TENTATIVAS:
            return False
        if self.proxima_tentativa_em and self.proxima_tentativa_em > datetime.now():
            return False
        return True
    
    def calcular_proximo_retry(self) -> datetime:
        """Backoff exponencial: 1min, 2min, 4min, 8min, 16min."""
        delay = min(60 * (2 ** self.tentativas), 15*60)  # Max 15 min
        return datetime.now() + timedelta(seconds=delay)
    
    def marcar_erro_temporario(self, tipo_erro: str, mensagem: str):
        """Marca erro que pode ser retentado."""
        self.status = StatusImportacaoProjeto.ERRO_TEMPORARIO
        self.tipo_erro = tipo_erro
        self.ultimo_erro = mensagem
        self.tentativas += 1
        self.proxima_tentativa_em = self.calcular_proximo_retry()
        self.save()
    
    def marcar_erro_permanente(self, tipo_erro: str, mensagem: str):
        """Marca erro que não pode ser retentado."""
        self.status = StatusImportacaoProjeto.ERRO_PERMANENTE
        self.tipo_erro = tipo_erro
        self.ultimo_erro = mensagem
        self.concluido_em = datetime.now()
        self.save()
```

**Management command melhorado**:

```python
# management/commands/processar_importacoes_dinabox.py
from django.core.management.base import BaseCommand
from apps.integracoes.models import DinaboxImportacaoProjeto, StatusImportacaoProjeto
from datetime import datetime

class Command(BaseCommand):
    def handle(self, *args, **options):
        # Busca items prontos para reprocessar
        items = DinaboxImportacaoProjeto.objects.filter(
            status=StatusImportacaoProjeto.PENDENTE
        ).order_by("prioridade", "criado_em")[:100]  # Limita a 100/execução
        
        for item in items:
            self._processar_item(item)
    
    def _processar_item(self, item):
        try:
            item.status = StatusImportacaoProjeto.PROCESSANDO
            item.iniciado_em = datetime.now()
            item.save()
            
            # Busca e processa
            from apps.pcp.services import ProcessadorRoteiroService
            resultado = ProcessadorRoteiroService().processar_projeto_dinabox(
                item.project_id,
                numero_lote=None
            )
            
            # Sucesso
            item.status = StatusImportacaoProjeto.CONCLUIDO
            item.resultado_resumo = resultado.resumo.dict()
            item.concluido_em = datetime.now()
            item.save()
            
            self.stdout.write(
                self.style.SUCCESS(f"✓ {item.project_id}")
            )
        
        except ValueError as e:
            # Erro de validação = permanente
            item.marcar_erro_permanente("validation_error", str(e))
            self.stdout.write(self.style.WARNING(f"! {item.project_id} (validação)"))
        
        except Exception as e:
            # Outros erros = temporário (retry)
            if item.pode_reprocessar():
                item.marcar_erro_temporario("api_error", str(e))
                self.stdout.write(
                    self.style.WARNING(f"⟳ {item.project_id} (retry {item.tentativas})")
                )
            else:
                item.marcar_erro_permanente("api_error", str(e))
                self.stdout.write(self.style.ERROR(f"✗ {item.project_id} (falhas excessivas)"))
```

---

## Fase 5: Integração com Estoque (Semana 5)

### 5.1 Consumir MapeamentoMaterial em PCP

**Arquivo**: `integracoes/services/estoque_integration.py` (novo)

```python
from typing import Dict, Optional, Decimal
from apps.integracoes.services import MaterialMappingService
from apps.estoque.selectors import EstoqueSelector
from apps.integracoes.logging import DinaboxEventLogger

class DinaboxEstoqueIntegration:
    """Integração entre Dinabox e Estoque (Gêmeo Digital)."""
    
    @staticmethod
    def registrar_consumo(
        material_dinabox: str,
        quantidade: float,
        unidade: str = "unidade"
    ) -> Optional[Dict]:
        """
        Registra consumo de material Dinabox no Estoque.
        
        Fluxo:
        1. Busca mapeamento Dinabox → Produto
        2. Aplica fator_conversao
        3. Cria movimento de saída no Estoque
        
        Args:
            material_dinabox: Nome do material em Dinabox
            quantidade: Quantidade consumida
            unidade: Unidade (un, m2, kg, etc)
            
        Returns:
            Dict com status do movimento criado, ou None se não mapeado
        """
        # 1. Busca mapeamento
        mapeamento = MaterialMappingService.obter_mapeamento(material_dinabox)
        if not mapeamento:
            DinaboxEventLogger.log_consumo_nao_mapeado(material_dinabox, quantidade)
            return None
        
        # 2. Aplica fator
        quantidade_ajustada = Decimal(quantidade) * mapeamento.fator_conversao
        
        # 3. Cria movimento no Estoque
        try:
            from apps.estoque.services import EstoqueMovimentoService
            movimento = EstoqueMovimentoService.registrar_saida(
                produto_id=mapeamento.produto.id,
                quantidade=quantidade_ajustada,
                motivo="importacao_dinabox",
                referencia_externa=material_dinabox,
                observacao=f"Consumo Dinabox ({mapeamento.fator_conversao}x)"
            )
            
            DinaboxEventLogger.log_consumo_registrado(
                material_dinabox,
                quantidade,
                quantidade_ajustada,
                True
            )
            
            return {
                "status": "sucesso",
                "movimento_id": movimento.id,
                "quantidade_ajustada": float(quantidade_ajustada),
                "fator_aplicado": float(mapeamento.fator_conversao),
            }
        
        except Exception as e:
            DinaboxEventLogger.log_consumo_registrado(
                material_dinabox,
                quantidade,
                quantidade_ajustada,
                False,
                str(e)
            )
            raise
```

**Integração em PCP**:

```python
# apps/pcp/services/processador_roteiro.py
from integracoes.services.estoque_integration import DinaboxEstoqueIntegration

class ProcessadorRoteiroService:
    def processar_projeto_dinabox(self, project_id: str):
        # ... código existente ...
        
        # Novo: registrar consumo de materiais
        for peca in pecas:
            if peca.material_nome:
                try:
                    DinaboxEstoqueIntegration.registrar_consumo(
                        material_dinabox=peca.material_nome,
                        quantidade=peca.quantidade * peca.dimensoes.metro_quadrado,
                        unidade="m2"
                    )
                except Exception as e:
                    logger.warning(f"Falha ao registrar consumo: {e}")
                    # Não bloqueia processamento se consumo falhar
        
        # ... resto do código ...
```

---

## Checklist de Refatoração

### Fase 1 ✅
- [ ] Implementar logging estruturado (DinaboxEventLogger)
- [ ] Adicionar conftest.py com fixtures
- [ ] Escrever testes para material_mapping
- [ ] Rodar testes com coverage

### Fase 2 ✅
- [ ] Criar DinaboxClienteService
- [ ] Implementar decorator de permissões
- [ ] Consolidar helpers em arquivo único
- [ ] Refatorar 5 views principais
- [ ] Testar views com mock de services

### Fase 3 ✅
- [ ] Adicionar `para_display()` aos schemas
- [ ] Remover parsers/project_detail.py
- [ ] Remover parsers/customer_detail.py
- [ ] Atualizar views para usar schemas direto

### Fase 4 ✅
- [ ] Adicionar campos de retry ao modelo
- [ ] Implementar backoff exponencial
- [ ] Atualizar management command
- [ ] Escrever testes para retry logic

### Fase 5 ✅
- [ ] Criar DinaboxEstoqueIntegration
- [ ] Integrar com PCP
- [ ] Testar consumo de material
- [ ] Documentar fluxo completo

---

## Resultado Final

**Antes**: 700 linhas de views desorganizadas, lógica espalhada  
**Depois**: 
- Services limpos e testáveis
- Views como adapters HTTP
- Logging estruturado
- 100% de cobertura de testes
- Integração com Estoque funcional
