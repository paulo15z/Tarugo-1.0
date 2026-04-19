# 📋 Análise e Refatoração do Módulo PCP - Estrutura de Dados e Roteamento

**Data**: Abril/2026  
**Projeto**: Tarugo 1.0  
**Objetivo**: Refatorar fluxo de importação Dinabox → Processamento → XLS seguindo padrões de arquitetura

---

## 1. ANÁLISE DO ARQUIVO closetmarcelo.json

### 1.1 Estrutura de Entrada da API Dinabox

O JSON retornado pela API Dinabox contem:

```
┌─ Project Metadata
│  ├─ project_id: "0108966599"
│  ├─ project_status: "production"
│  ├─ project_customer_name: "1101 - MARCELO E KELLY"
│  ├─ project_description: "CLOSET MASTER"
│  └─ [timestamps, versão, autor]
│
├─ components (categorias de peças)
│  └─ data[]: Array de categorias
│     └─ category_data[]: Peças por categoria (CONSTRUTOR 2.0, etc)
│
├─ woodwork[]: **Array principal de peças**
│  ├─ id, mid, ref, name (descrição do módulo)
│  ├─ type: "thickened" | "normal"
│  ├─ material: { id, name, width, height, vein }
│  ├─ edge_*: bordas (top, bottom, left, right)
│  ├─ parts[]: Peças individuais do módulo
│  │  ├─ id, ref, type, name, count
│  │  ├─ width, height, thickness, weight
│  │  ├─ material_id, material_name, material_m2
│  │  ├─ edge_*: bordas (top, bottom, left, right)
│  │  ├─ code_a, code_b, code_a2, code_b2 (furações/bipagem)
│  │  └─ note: "encaminhar p/ duplagem" (instrução técnica)
│  └─ inputs[]: Ferragens do módulo
│     ├─ id, name, category_id, category_name
│     ├─ qt: quantidade
│     └─ dimensions, weight, factory_price
│
└─ holes[]: Array de furos/conectores
   └─ id, qt, weight (Minifix, Cavilha, etc)
```

### 1.2 Fluxo Atual de Processamento

**Problema**: O fluxo atual é **linear e pouco estruturado**:

```
DinaboxService.get_project_as_dataframe(project_id)
    ↓
Constrói manualmente linhas do DataFrame com mapeamento 1:1
    ↓
pcp_service.processar_projeto_dinabox(project_id)
    ↓
Passa DataFrame para consolidar_ripas() [transforma dados]
    ↓
calcular_roteiro() [regra de negócio simples/inline]
    ↓
determinar_plano_de_corte() [regra de negócio simples/inline]
    ↓
gerar_xls_roteiro() [serializa para XLS]
    ↓
XLS final + lote criado no banco
```

### 1.3 Dados que Circulam

**De `closetmarcelo.json` para o DataFrame:**

| Origem JSON | Campo DataFrame | Transformação | Status |
|-------------|-----------------|---------------|--------|
| `module.ref` | `REFERÊNCIA DA PEÇA` | Parte 1 (antes de `-`) | ✅ |
| `part.ref` | `REFERÊNCIA DA PEÇA` | Parte 2 (depois de `-`) | ✅ |
| `module.name` | `DESCRIÇÃO MÓDULO` | Direto | ✅ |
| `part.name` | `DESCRIÇÃO DA PEÇA` | Direto + sinalização n/m se duplada | ✅ |
| `part.width/height/thickness` | Dimensões | String com `,` | ✅ |
| `part.material` | `MATERIAL DA PEÇA` + `CÓDIGO DO MATERIAL` | Extração de objeto | ✅ |
| `part.edge_*` | `BORDA_FACE_*` | 4 bordas nomeadas | ✅ |
| `part.code_a/b/a2/b2` | `FURACAO_A/B/A2/B2` | Direto | ✅ |
| `part.note` | `OBSERVAÇÃO` + `OBS` | Duplicado | ❌ Redundância |
| `module.ref` | `CONTEXTO` | "MOD: {module.name} ({ref})" | ✅ |

**Problemas identificados**:
1. ✅ Dupla referência (OBS + OBSERVAÇÃO) → confusão
2. ✅ `CONTEXTO` é string gerada, não campo direto
3. ✅ Dados de ferragens (`holes`, `inputs` do módulo) **NÃO** são mapeados → ignorados
4. ✅ Lógica de "sinalização 1/n para dupladas" está inline em `DinaboxService`
5. ✅ Tags Markdown (`_ripa_`, `_painel_`, etc) são espalhadas por vários campos

---

## 2. PROBLEMAS NA ARQUITETURA ATUAL

### 2.1 Falta de Abstração entre Camadas

**Problema 1: Dinabox → DataFrame é acoplado**
- `DinaboxService.get_project_as_dataframe()` monta o DataFrame diretamente
- Lógica de transformação está misturada com mapeamento de campos
- Se Dinabox mudar API, todo o fluxo quebra

**Problema 2: DataFrame é a "linguagem universal"**
- DataFrame viaja entre `Integracoes → PCP → Bipagem`
- Sem tipagem: qualquer coluna pode estar faltando
- Sem validação: erros aparecem apenas no final (XLS gerado errado)

**Problema 3: Regras de negócio em funções utils**
- `calcular_roteiro()` e `determinar_plano_de_corte()` estão em `utils/roteiros.py`
- São regras de negócio puro, não utilitários
- Sem versionamento: mudança em 1 linha afeta todo processamento histórico

**Problema 4: Consolidação de Ripas é um "black box"**
```python
consolidar_ripas(df) → df  # Muta o DataFrame
```
- 300+ linhas de lógica complexa
- Sem testes isolados (precisa de DataFrame válido)
- Difícil de reutilizar em contextos diferentes

### 2.2 Falta de Validação entre Etapas

| Etapa | Input | Validação | Output |
|-------|-------|-----------|--------|
| DinaboxService | JSON API | ❌ Nenhuma | DataFrame (tipagem = str) |
| consolidar_ripas() | DataFrame | ❌ Apenas try/except de valores | DataFrame modificado |
| calcular_roteiro() | Row do DataFrame | ❌ Apenas get/coalesce | String de roteiro |
| determinar_plano() | Row do DataFrame | ❌ Apenas if/elif | String de plano |
| gerar_xls() | DataFrame | ❌ Apenas write/save | Bytes do XLS |

**Resultado**: Erros aparecem no final (usuário recebe XLS ruim).

### 2.3 Ausência de Logging e Auditoria

- Não há rastreamento de qual regra de negócio foi aplicada
- Não há log de transformações intermediárias
- Se um roteiro está errado, é impossível debugar

---

## 3. ESTRUTURA PROPOSTA

### 3.1 Nova Arquitetura em Camadas

```
┌─────────────────────────────────────────────────────────────┐
│                    API / Views (Django)                      │
├─────────────────────────────────────────────────────────────┤
│                 PCP Service Layer                             │
│  ┌──────────────────────────────────────────────────────┐    │
│  │ ProcessadorRoteiroService                            │    │
│  │  • processar_projeto_dinabox(project_id) → Output    │    │
│  │  • processar_arquivo_dinabox(file) → Output          │    │
│  └──────────────────────────────────────────────────────┘    │
├─────────────────────────────────────────────────────────────┤
│              Domain / Regras de Negócio                       │
│  ┌──────────────────────────────────────────────────────┐    │
│  │ RoteiroCalculator                                    │    │
│  │  • calcular_roteiro(peca: PecaOperacional) → Roteiro │    │
│  │                                                       │    │
│  │ PlanoCorteCalculator                                 │    │
│  │  • determinar_plano(peca: PecaOperacional) → Plano   │    │
│  │                                                       │    │
│  │ ConsolidadorRipas                                    │    │
│  │  • consolidar(pecas: List[Peca]) → List[RipaCorte]   │    │
│  └──────────────────────────────────────────────────────┘    │
├─────────────────────────────────────────────────────────────┤
│                   Schemas (Pydantic)                          │
│  • PecaOperacional: Peça com regras de negócio               │
│  • RipaCorte: Ripa consolidada                               │
│  • RoteiroOutput: Resultado do processamento                 │
│  • AuditoriaRoteamento: Log de transformações                │
├─────────────────────────────────────────────────────────────┤
│                 Repository/Selector Layer                     │
│  • get_peca_by_id()                                          │
│  • salvar_lote_pcp()                                         │
│  • get_historico_processamento()                             │
├─────────────────────────────────────────────────────────────┤
│                      Models (Django ORM)                      │
│  • LotePCP, ProcessamentoPCP, PecaPCP, AuditoriaRoteamento   │
├─────────────────────────────────────────────────────────────┤
│                 Integrations (Externos)                       │
│  • DinaboxAPIClient (em integracoes.dinabox)                 │
│  • ExcelGenerator (utils.excel)                              │
└─────────────────────────────────────────────────────────────┘
```

### 3.2 Fluxo Refatorado

```
Request: POST /api/pcp/processar?project_id=0108966599
    ↓
[API View] PCP_ProcessarView.post()
    → Valida input com DRF Serializer
    ↓
[Service] ProcessadorRoteiroService.processar_projeto_dinabox(project_id)
    ↓
    ├─ [Integration] DinaboxAPIClient.get_project(project_id)
    │  → raw_data: Dict
    │  ↓
    └─ [Repository] DinaboxRepository.parsear_para_pecas_operacionais(raw_data)
       → List[PecaOperacional] (Pydantic validado)
    ↓
    ├─ [Domain] ConsolidadorRipas.consolidar(pecas)
    │  → List[PecaOperacional | RipaCorte]
    │  → Auditoria criada: "consolidadas 15 ripas em 3 tiras"
    │  ↓
    └─ [Domain] RoteiroCalculator.calcular_para_lista(pecas)
       → Auditoria criada: "roteiro [1,2,3] = COR→FUR→BOR"
    ↓
    ├─ [Domain] PlanoCorteCalculator.determinar_para_lista(pecas)
    │  → Auditoria criada: "plano 05 = DUP"
    │  ↓
    └─ [Models/Selector] LotePCPRepository.criar_com_pecas(pecas_finais)
       → LotePCP salvo no banco com PecaPCP + AuditoriaRoteamento
    ↓
    ├─ [Utils] ExcelGenerator.gerar_xls(pecas_finais)
    │  → Bytes do XLS
    │  ↓
    └─ [Models] ProcessamentoPCP.criar(arquivo_saida)
       → Registro de processamento
    ↓
Response: {
    "status": "ok",
    "processamento_id": "abc123",
    "resumo": {
        "total_entrada": 45,
        "total_saida": 42,
        "ripas_geradas": 8,
        "pecas_consolidadas": 6,
        "arquivo_xls": "abc123_closetmarcelo.xls",
        "auditoria": [...]
    }
}
```

---

## 4. ESTRUTURA DETALHADA DE SCHEMAS

### 4.1 Nova Hierarquia de Schemas

```python
# schemas/dinabox.py - Representação da API
PecaDinaboxRaw
├─ id: str
├─ ref: str
├─ name: str
├─ width, height, thickness: Decimal
├─ material: MaterialDinabox
├─ edges: Dict[str, EdgeDinabox]
├─ code_a, code_b: Optional[str]
├─ note: str
└─ [...]

# schemas/operacional.py - Após validação de negócio
PecaOperacional (Pydantic)
├─ # Identificação
├─ id_dinabox: str
├─ ref_completa: str  # "M2803574 - P2808386"
├─ descricao: str
├─ quantidade: int
│
├─ # Localização e agrupamento
├─ modulo_ref: str
├─ modulo_nome: str
├─ contexto: str
│
├─ # Dimensões (validadas)
├─ dimensoes: Dimensoes
│  └─ largura, altura, espessura: Decimal (> 0)
├─ material_id: str
├─ material_nome: str
│
├─ # Processamento
├─ bordas: Dict[str, BordaInfo]
├─ furacoes: Dict[str, Optional[str]]  # {"A": "2260947", "B": null}
├─ eh_duplada: bool
├─ observacoes_original: str
├─ tags_markdown: Set[str]  # {"_ripa_", "_painel_"}
│
├─ # Saída após processamento
├─ roteiro: Optional[Roteiro] = None
├─ plano_corte: Optional[str] = None
├─ lote_saida: Optional[str] = None
│
└─ # Rastreamento
└─ id_auditoria: Optional[str] = None

# schemas/output.py - Resultado do processamento
RipaCorte(Pydantic)
├─ # Herança de PecaOperacional
├─ peca_base: PecaOperacional
│
├─ # Consolidação
├─ numero_tira: int  # 1, 2, 3...
├─ total_tiras: int  # 3
├─ pecas_por_tira: int  # 4
├─ altura_tira_mm: Decimal
├─ largura_tira_mm: Decimal
├─ refilo_aplicado_mm: Decimal
├─ serra_entre_pecas_mm: Decimal
│
└─ observacao_consolidacao: str

ProcessarRoteiroOutput(Pydantic)
├─ processamento_id: str
├─ projeto_id: str
├─ cliente_nome: str
├─ data_processamento: datetime
├─ resumo: ResumoPeca
│  ├─ total_entrada: int
│  ├─ total_saida: int
│  ├─ ripas_geradas: int
│  ├─ pecas_consolidadas: int
├─ pecas_finais: List[PecaOperacional | RipaCorte]
├─ auditoria: List[AuditoriaRoteamento]
└─ arquivo_xls: str

AuditoriaRoteamento(Pydantic)
├─ id: str (UUID)
├─ id_peca: str
├─ tipo_transformacao: Literal["consolidacao", "roteiro", "plano", "validacao"]
├─ valor_antes: str
├─ valor_depois: str
├─ regra_aplicada: str  # Qual decisão foi tomada
├─ confianca: Literal["high", "medium", "low"]
├─ timestamp: datetime
└─ executor: str  # "ConsolidadorRipas", "RoteiroCalculator"
```

### 4.2 Enum para Roteiros e Planos

```python
# domain/roteiros.py
class Setor(str, Enum):
    COR = "COR"  # Corte rígido (serra circular)
    FUR = "FUR"  # Furação/Usinagem
    BOR = "BOR"  # Borda
    XBOR = "XBOR"  # Borda extra (ripas)
    DUP = "DUP"  # Duplagem/Espelhamento
    # ... etc

class Roteiro(BaseModel):
    """Sequência de setores para uma peça"""
    setores: List[Setor]  # [COR, FUR, BOR]
    
    @property
    def como_string(self) -> str:
        return " → ".join([s.value for s in self.setores])
    
    def __str__(self) -> str:
        return self.como_string

# domain/planos.py
class PlanoCorte(str, Enum):
    PINTURA = "01"
    LAMINA = "02"
    RIPA_CORTE = "03"
    MCX = "04"
    DUP = "05"
    MPE = "06"
    PAINEL = "07"
    # ... até "11"

PlanoCorteDecisao = {
    "aplicar_tag_ripa": "03",
    "aplicar_tag_pintura": "01",
    "é_duplada": "05",
    "é_estrutura_gaveta": "04",  # MCX
}
```

---

## 5. IMPLEMENTAÇÃO PASSO A PASSO

### Fase 1: Preparação (Semana 1)

#### 1.1 Criar Estrutura de Pastas

```bash
apps/pcp/
├─ domain/                          # ← NEW
│  ├─ __init__.py
│  ├─ roteiros.py                  # Enums e lógica de roteiro
│  ├─ planos.py                    # Enums e lógica de plano
│  ├─ consolidador_ripas.py        # Classe principal
│  └─ calculadores.py              # RoteiroCalculator, PlanoCalculator
│
├─ repositories/                    # ← NEW (antes "selectors")
│  ├─ __init__.py
│  ├─ dinabox_repository.py       # Parse JSON → PecaOperacional
│  ├─ lote_pcp_repository.py      # CRUD de lotes
│  └─ auditoria_repository.py     # Log de transformações
│
├─ schemas/                        # ← EXPANDIR
│  ├─ __init__.py
│  ├─ peca.py                     # PecaOperacional (atual + novo)
│  ├─ dinabox.py                  # Schemas Dinabox raw (novo)
│  ├─ processamento.py            # Input/Output de processamento (novo)
│  └─ auditoria.py                # AuditoriaRoteamento (novo)
│
├─ services/                       # ← REFATORAR
│  ├─ __init__.py
│  ├─ processador_roteiro.py      # ← NEW: Main service
│  ├─ lote_service.py             # (manter, ajustar)
│  ├─ pcp_interface.py            # (manter: interface com Bipagem)
│  └─ [DEPRECATE] pcp_service.py  # (mover lógica, depois deletar)
│
├─ utils/                          # ← REFATORAR
│  ├─ __init__.py
│  ├─ excel.py                    # (manter: geração de XLS)
│  ├─ conversores.py              # ← NEW: PecaOperacional → Row do DataFrame
│  └─ [DEPRECATE] roteiros.py     # (mover para domain/)
│
├─ models.py                       # ← AJUSTAR
│  └─ ProcessamentoPCP             # (modelo existente, ok)
│  └─ AuditoriaRoteamento         # ← NEW
│
├─ api/                            # ← AJUSTAR
│  └─ views.py                    # (agora chama ProcessadorRoteiroService)
│
└─ tests/                          # ← NEW (testes isolados)
   ├─ test_consolidador_ripas.py
   ├─ test_roteiros.py
   ├─ test_planos.py
   └─ test_dinabox_repository.py
```

### Fase 2: Schemas Pydantic (Semana 2)

#### 2.1 `schemas/dinabox.py` - Representação raw da API

```python
from decimal import Decimal
from typing import Optional, List, Dict
from pydantic import BaseModel, Field, ConfigDict

class MaterialDinabox(BaseModel):
    id: str
    name: str
    width: Decimal
    height: Decimal
    vein: bool = False
    
    model_config = ConfigDict(from_attributes=True)

class EdgeDinabox(BaseModel):
    name: Optional[str] = None
    perimeter: Decimal = 0
    thickness: int = 0

class PartDinabox(BaseModel):
    id: str
    ref: str
    name: str
    type: str
    count: int
    width: Decimal
    height: Decimal
    thickness: Decimal
    material: Optional[MaterialDinabox]
    note: Optional[str] = None
    code_a: Optional[str] = None
    code_b: Optional[str] = None
    code_a2: Optional[str] = None
    code_b2: Optional[str] = None
    edge_left: Optional[EdgeDinabox] = None
    edge_right: Optional[EdgeDinabox] = None
    edge_top: Optional[EdgeDinabox] = None
    edge_bottom: Optional[EdgeDinabox] = None
    
    model_config = ConfigDict(from_attributes=True, extra="allow")

class ModuleDinabox(BaseModel):
    id: str
    mid: str
    ref: str
    name: str
    type: str
    parts: List[PartDinabox]
    material: Optional[MaterialDinabox]
    edge_left: Optional[EdgeDinabox]
    edge_right: Optional[EdgeDinabox]
    edge_top: Optional[EdgeDinabox]
    edge_bottom: Optional[EdgeDinabox]
    
    model_config = ConfigDict(from_attributes=True, extra="allow")

class ProjectoDinabox(BaseModel):
    project_id: str
    project_customer_name: str
    project_description: str
    project_status: str
    woodwork: List[ModuleDinabox]
    holes: List[Dict]  # Não necessário processar detalhes agora
    
    model_config = ConfigDict(from_attributes=True, extra="allow")
```

#### 2.2 `schemas/peca.py` - PecaOperacional refatorada

```python
from decimal import Decimal
from datetime import datetime
from typing import Optional, List, Set, Dict
from pydantic import BaseModel, Field, ConfigDict, field_validator

class Dimensoes(BaseModel):
    largura: Optional[Decimal] = None
    altura: Optional[Decimal] = None
    espessura: Optional[Decimal] = None
    
    @field_validator("largura", "altura", "espessura", mode="before")
    @classmethod
    def validar_positivo(cls, v):
        if v is None:
            return None
        val = Decimal(str(v).replace(",", "."))
        if val < 0:
            raise ValueError("Dimensão não pode ser negativa")
        return val

class BordaInfo(BaseModel):
    nome: Optional[str] = None
    perimetro_mm: Decimal = 0
    espessura: int = 0

class PecaOperacional(BaseModel):
    # === Identificação ===
    id_dinabox: str
    ref_completa: str  # "M2803574 - P2808386"
    ref_modulo: Optional[str] = None
    ref_peca: Optional[str] = None
    descricao: str
    
    # === Localização ===
    modulo_ref: str
    modulo_nome: str
    contexto: Optional[str] = None
    
    # === Dimensões ===
    quantidade: int = Field(..., gt=0)
    dimensoes: Dimensoes
    metro_quadrado: Optional[Decimal] = None
    
    # === Material e Acabamento ===
    material_id: Optional[str] = None
    material_nome: Optional[str] = None
    material_com_veio: bool = False
    bordas: Dict[str, BordaInfo] = Field(default_factory=dict)
    
    # === Processamento ===
    furacoes: Dict[str, Optional[str]] = Field(default_factory=dict)  # {"A": id, "B": None, ...}
    eh_duplada: bool = False
    
    # === Tags (do campo "note" do Dinabox) ===
    observacoes_original: Optional[str] = None
    tags_markdown: Set[str] = Field(default_factory=set)  # {"_ripa_", "_painel_"}
    
    # === Saída após processamento ===
    roteiro: Optional[str] = None  # Ex: "COR → FUR → BOR"
    plano_corte: Optional[str] = None  # Ex: "05" (DUP)
    lote_saida: Optional[str] = None  # Ex: "2-05"
    
    # === Auditoria ===
    id_auditoria: Optional[str] = None
    data_criacao: datetime = Field(default_factory=datetime.now)
    
    model_config = ConfigDict(from_attributes=True, extra="allow")
    
    @field_validator("tags_markdown", mode="before")
    @classmethod
    def extrair_tags(cls, v, info):
        """Extrai tags Markdown do campo observacoes_original"""
        if v:  # Já fornecidas
            return v if isinstance(v, set) else set(v)
        
        obs = info.data.get("observacoes_original", "")
        if not obs:
            return set()
        
        import re
        tags = set(re.findall(r"_(\w+)_", obs))
        return tags
```

#### 2.3 `schemas/processamento.py` - Input/Output

```python
from typing import List, Optional
from datetime import datetime
from pydantic import BaseModel, Field

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
    pecas_finais: List[dict]  # List[PecaOperacional] serializado
    arquivo_xls: Optional[str] = None  # Nome do arquivo gerado
    
    auditoria: Optional[List[dict]] = None  # Histórico de transformações
    
    class Config:
        from_attributes = True
```

### Fase 3: Domain / Regras de Negócio (Semana 2-3)

#### 3.1 `domain/roteiros.py`

```python
from enum import Enum
from typing import List, Set
from pydantic import BaseModel

class Setor(str, Enum):
    """Setores de produção da indústria moveleira"""
    COR = "COR"
    FUR = "FUR"
    BOR = "BOR"
    XBOR = "XBOR"  # Borda extra (ripas)
    DUP = "DUP"
    MCX = "MCX"  # Montagem de Caixa
    MPE = "MPE"  # Montagem Portas e Externos
    MAR = "MAR"  # Marcenaria
    PRE = "PRE"  # Pré-montagem
    # ... adicionar conforme necessário

class Roteiro(BaseModel):
    """Sequência de setores para uma peça"""
    setores: List[Setor]
    
    @property
    def como_string(self) -> str:
        """Ex: 'COR → FUR → BOR'"""
        return " → ".join([s.value for s in self.setores])
    
    def __str__(self) -> str:
        return self.como_string
    
    def __repr__(self) -> str:
        return f"Roteiro({self.como_string})"

class RoteiroCalculator:
    """
    Calcula roteiro baseado em características da peça.
    
    Sequência industrial:
    1. COR (corte obrigatório)
    2. DUP (duplagem se peça é duplada)
    3. FUR (furação se tem furos)
    4. BOR (borda se tem acabamento)
    5. XBOR (borda extra se é ripa com borda)
    6. Setores especializados (MCX, MPE, MAR, etc)
    """
    
    # Regras para ativar cada setor
    REGRAS_ATIVACAO = {
        Setor.COR: lambda p: True,  # Sempre
        Setor.DUP: lambda p: p.eh_duplada,
        Setor.FUR: lambda p: any(v for v in p.furacoes.values()),
        Setor.BOR: lambda p: any(b.nome for b in p.bordas.values()),
        Setor.XBOR: lambda p: p.eh_ripa() and any(b.nome for b in p.bordas.values()),
        # ... etc
    }
    
    @staticmethod
    def calcular(peca: "PecaOperacional") -> Roteiro:
        """Calcula roteiro para uma peça individual"""
        setores = []
        
        # 1. Sempre COR
        setores.append(Setor.COR)
        
        # 2. DUP
        if peca.eh_duplada and not peca.eh_ripa():
            setores.append(Setor.DUP)
        
        # 3. FUR
        if any(peca.furacoes.values()):
            setores.append(Setor.FUR)
        
        # 4. BOR
        if any(b.nome for b in peca.bordas.values()):
            setores.append(Setor.BOR)
            # Se ripa com borda, adicionar XBOR
            if peca.eh_ripa():
                setores.append(Setor.XBOR)
        
        return Roteiro(setores=setores)
    
    @staticmethod
    def calcular_batch(pecas: List["PecaOperacional"]) -> List[Roteiro]:
        """Calcula roteiro para múltiplas peças"""
        return [RoteiroCalculator.calcular(p) for p in pecas]
```

#### 3.2 `domain/planos.py`

```python
from enum import Enum
from typing import Tuple
from pydantic import BaseModel

class PlanoCorte(str, Enum):
    """Planos de corte operacionais"""
    PINTURA = "01"
    LAMINA = "02"
    RIPA_CORTE = "03"
    MCX = "04"
    DUP = "05"
    MPE = "06"
    PAINEL = "07"
    # ... até "11"

class DecisaoPlano(BaseModel):
    """Resultado da decisão + explicação"""
    plano: PlanoCorte
    condicao_aplicada: str  # Ex: "tem_tag_ripa"
    confianca: Literal["high", "medium", "low"]

class PlanoCorteCalculator:
    """Determina plano de corte baseado em características"""
    
    DECISOES_ORDENADAS = [
        # (condicao_lambda, plano, confianca, descricao_condicao)
        (lambda p: "_ripa_" in p.tags_markdown or p.eh_ripa(), 
         PlanoCorte.RIPA_CORTE, "high", "tem_tag_ripa"),
        
        (lambda p: "_pin_" in p.tags_markdown, 
         PlanoCorte.PINTURA, "high", "tem_tag_pintura"),
        
        (lambda p: "_lamina_" in p.tags_markdown or "lamina" in p.material_nome.lower(), 
         PlanoCorte.LAMINA, "high", "é_lamina"),
        
        (lambda p: p.eh_duplada, 
         PlanoCorte.DUP, "high", "é_duplada"),
        
        # ... etc
    ]
    
    @staticmethod
    def determinar(peca: "PecaOperacional") -> DecisaoPlano:
        """Determina plano com rastreamento de decisão"""
        for condicao, plano, confianca, descricao in PlanoCorteCalculator.DECISOES_ORDENADAS:
            if condicao(peca):
                return DecisaoPlano(
                    plano=plano,
                    condicao_aplicada=descricao,
                    confianca=confianca
                )
        
        # Default
        return DecisaoPlano(
            plano=PlanoCorte.PAINEL,
            condicao_aplicada="default",
            confianca="low"
        )
```

#### 3.3 `domain/consolidador_ripas.py` (Main)

```python
from typing import List, Tuple
from dataclasses import dataclass
import math

@dataclass
class Configuracao:
    altura_chapa_bruta_mm: float = 2750.0
    refilo_total_mm: float = 10.0
    espessura_serra_mm: float = 4.0

class ConsolidadorRipas:
    """
    Consolida ripas em tiras otimizadas.
    
    Lógica:
    1. Identifica ripas por tag ou descrição
    2. Agrupa por material + dimensões
    3. Calcula quantas peças cabem por tira
    4. Distribui entre tiras, gerando novas peças de "RIPA CORTE"
    """
    
    def __init__(self, config: Configuracao = None):
        self.config = config or Configuracao()
    
    def consolidar(self, pecas: List["PecaOperacional"]) -> Tuple[List["PecaOperacional"], List["AuditoriaRoteamento"]]:
        """
        Consolida ripas de uma lista de peças.
        
        Returns:
            - Lista de peças (originais + novas ripas de corte)
            - Lista de auditorias (transformações aplicadas)
        """
        ripas = [p for p in pecas if p.eh_ripa()]
        nao_ripas = [p for p in pecas if not p.eh_ripa()]
        
        if not ripas:
            return pecas, []
        
        ripas_consolidadas, auditorias = self._consolidar_ripas(ripas)
        return nao_ripas + ripas_consolidadas, auditorias
    
    def _consolidar_ripas(self, ripas: List["PecaOperacional"]) -> Tuple[List, List]:
        """Lógica principal de consolidação"""
        # Agrupamento...
        # Cálculo de tiras...
        # Criação de novas peças...
        pass
```

### Fase 4: Repository / Data Access (Semana 3)

#### 4.1 `repositories/dinabox_repository.py`

```python
from typing import List
from apps.pcp.schemas.peca import PecaOperacional

class DinaboxRepository:
    """
    Converte dados da API Dinabox (JSON) para PecaOperacional (domain).
    
    Responsabilidades:
    - Parse do JSON bruto
    - Validação estrutural
    - Mapeamento de campos
    - Enriquecimento de contexto
    """
    
    @staticmethod
    def parsear_para_pecas_operacionais(project_data: dict) -> List[PecaOperacional]:
        """
        Converte estrutura JSON do Dinabox para lista de PecaOperacional.
        
        Args:
            project_data: Dict retornado da API Dinabox
        
        Returns:
            List[PecaOperacional]: Peças validadas e prontas para processamento
        
        Raises:
            ValueError: Se estrutura não estiver válida
        """
        try:
            projeto = ProjectoDinabox.model_validate(project_data)
        except Exception as e:
            raise ValueError(f"Falha ao validar JSON Dinabox: {e}")
        
        pecas = []
        for modulo in projeto.woodwork:
            for parte in modulo.parts:
                # Detectar duplagem por nota
                eh_duplada = "_dup_" in (parte.note or "").lower()
                
                # Extrair tags
                tags = DinaboxRepository._extrair_tags(parte.note)
                
                # Mapear bordas
                bordas = DinaboxRepository._mapear_bordas(parte, modulo)
                
                # Mapear furações
                furacoes = DinaboxRepository._mapear_furacoes(parte)
                
                peca = PecaOperacional(
                    id_dinabox=parte.id,
                    ref_completa=f"{modulo.ref} - {parte.ref}",
                    ref_modulo=modulo.ref,
                    ref_peca=parte.ref,
                    descricao=parte.name,
                    modulo_ref=modulo.ref,
                    modulo_nome=modulo.name,
                    quantidade=parte.count,
                    dimensoes=Dimensoes(
                        largura=parte.width,
                        altura=parte.height,
                        espessura=parte.thickness
                    ),
                    material_id=parte.material.id if parte.material else None,
                    material_nome=parte.material.name if parte.material else None,
                    bordas=bordas,
                    eh_duplada=eh_duplada,
                    observacoes_original=parte.note,
                    tags_markdown=tags,
                    furacoes=furacoes,
                    contexto=f"MOD: {modulo.name} ({modulo.ref})"
                )
                pecas.append(peca)
        
        return pecas
    
    @staticmethod
    def _extrair_tags(note: Optional[str]) -> Set[str]:
        """Extrai tags Markdown como _ripa_, _painel_, etc"""
        if not note:
            return set()
        import re
        return set(re.findall(r"_(\w+)_", note))
    
    @staticmethod
    def _mapear_bordas(parte, modulo) -> Dict:
        """Mapeia bordas de forma hierárquica (parte > módulo)"""
        bordas = {}
        for face in ["top", "bottom", "left", "right"]:
            edge_parte = getattr(parte, f"edge_{face}", None)
            edge_modulo = getattr(modulo, f"edge_{face}", None)
            
            edge = edge_parte or edge_modulo
            bordas[face] = BordaInfo(
                nome=edge.name if edge else None,
                perimetro_mm=edge.perimeter if edge else 0,
                espessura=edge.thickness if edge else 0
            )
        return bordas
    
    @staticmethod
    def _mapear_furacoes(parte) -> Dict[str, Optional[str]]:
        """Mapeia códigos de furação"""
        return {
            "A": parte.code_a,
            "B": parte.code_b,
            "A2": parte.code_a2,
            "B2": parte.code_b2,
        }
```

#### 4.2 `repositories/lote_pcp_repository.py`

```python
from typing import List
from apps.pcp.models import LotePCP, PecaPCP

class LotePCPRepository:
    """CRUD e queries para LotePCP"""
    
    @staticmethod
    def criar_com_pecas(
        processamento_id: str,
        projeto_id: str,
        cliente_nome: str,
        pecas: List["PecaOperacional"],
        numero_lote: Optional[int] = None
    ) -> LotePCP:
        """Cria novo lote PCP com peças"""
        lote = LotePCP.objects.create(
            id=processamento_id,
            numero_lote=numero_lote,
            projeto_id=projeto_id,
            cliente_nome=cliente_nome,
            total_pecas=len(pecas)
        )
        
        for peca_op in pecas:
            PecaPCP.objects.create(
                lote=lote,
                id_dinabox=peca_op.id_dinabox,
                referencia=peca_op.ref_completa,
                descricao=peca_op.descricao,
                roteiro=peca_op.roteiro,
                plano_corte=peca_op.plano_corte,
                quantidade=peca_op.quantidade
            )
        
        return lote
    
    @staticmethod
    def get_by_id(lote_id: str) -> LotePCP:
        return LotePCP.objects.get(id=lote_id)
```

### Fase 5: Services (Semana 4)

#### 5.1 `services/processador_roteiro.py` - MAIN SERVICE

```python
from typing import List, Tuple, Optional
from datetime import datetime
import uuid
import os
from django.conf import settings

from apps.integracoes.dinabox.client import DinaboxAPIClient
from apps.pcp.repositories.dinabox_repository import DinaboxRepository
from apps.pcp.domain.consolidador_ripas import ConsolidadorRipas
from apps.pcp.domain.roteiros import RoteiroCalculator
from apps.pcp.domain.planos import PlanoCorteCalculator
from apps.pcp.repositories.lote_pcp_repository import LotePCPRepository
from apps.pcp.repositories.auditoria_repository import AuditoriaRepository
from apps.pcp.utils.excel import gerar_xls_roteiro
from apps.pcp.schemas.processamento import ProcessarRoteiroOutput, ResumoPecas
from apps.pcp.models import ProcessamentoPCP

class ProcessadorRoteiroService:
    """
    Service principal de processamento de projetos Dinabox.
    
    Orquestra todo o fluxo:
    1. Busca dados da API Dinabox
    2. Parse para domain (PecaOperacional)
    3. Aplicação de regras de negócio (consolidação, roteiro, plano)
    4. Geração de XLS
    5. Salvamento em banco de dados
    """
    
    def __init__(self):
        self.client = DinaboxAPIClient()
        self.consolidador = ConsolidadorRipas()
        self.auditoria_repo = AuditoriaRepository()
    
    def processar_projeto_dinabox(
        self, 
        project_id: str, 
        numero_lote: Optional[int] = None
    ) -> ProcessarRoteiroOutput:
        """
        Processa um projeto inteiro via API.
        
        Fluxo:
        1. Busca projeto na API
        2. Parse para PecaOperacional
        3. Aplicação de regras
        4. Geração de XLS e salvamento
        
        Args:
            project_id: ID do projeto no Dinabox
            numero_lote: Número do lote (opcional, pode ser gerado)
        
        Returns:
            ProcessarRoteiroOutput com status, resumo e arquivo
        """
        processamento_id = str(uuid.uuid4())[:8]
        
        try:
            # 1. Busca na API
            project_data = self.client.get_project(project_id)
            
            # 2. Parse para domain
            pecas = DinaboxRepository.parsear_para_pecas_operacionais(project_data)
            total_entrada = len(pecas)
            
            # 3. Aplicar consolidação de ripas
            pecas, auditorias_consolidacao = self.consolidador.consolidar(pecas)
            total_apos_consolidacao = len(pecas)
            ripas_geradas = total_apos_consolidacao - total_entrada + len([p for p in pecas if p.eh_ripa()])
            
            # 4. Calcular roteiros
            for peca in pecas:
                roteiro_obj = RoteiroCalculator.calcular(peca)
                peca.roteiro = roteiro_obj.como_string
                self.auditoria_repo.criar(
                    id_peca=peca.id_dinabox,
                    tipo="roteiro",
                    valor_antes="",
                    valor_depois=peca.roteiro,
                    regra_aplicada=f"RoteiroCalculator",
                    confianca="high"
                )
            
            # 5. Calcular planos
            for peca in pecas:
                decisao = PlanoCorteCalculator.determinar(peca)
                peca.plano_corte = decisao.plano.value
                self.auditoria_repo.criar(
                    id_peca=peca.id_dinabox,
                    tipo="plano",
                    valor_antes="",
                    valor_depois=peca.plano_corte,
                    regra_aplicada=f"PlanoCorteCalculator: {decisao.condicao_aplicada}",
                    confianca=decisao.confianca
                )
            
            # 6. Gerar lote
            numero_lote = numero_lote or self._gerar_numero_lote()
            lote = LotePCPRepository.criar_com_pecas(
                processamento_id=processamento_id,
                projeto_id=project_id,
                cliente_nome=project_data["project_customer_name"],
                pecas=pecas,
                numero_lote=numero_lote
            )
            
            # 7. Gerar XLS
            nome_arquivo_saida = self._gerar_nome_arquivo(project_id, processamento_id)
            xls_bytes = self._gerar_xls(pecas, nome_arquivo_saida)
            
            # 8. Salvar registro de processamento
            ProcessamentoPCP.objects.create(
                id=processamento_id,
                nome_arquivo=f"projeto_{project_id}.api",
                total_pecas=len(pecas),
                arquivo_saida=nome_arquivo_saida
            )
            
            # 9. Montar resposta
            resumo = ResumoPecas(
                total_entrada=total_entrada,
                total_saida=len(pecas),
                ripas_geradas=ripas_geradas,
                pecas_consolidadas=total_entrada - len([p for p in pecas if not p.eh_ripa()]),
                variacao=len(pecas) - total_entrada
            )
            
            return ProcessarRoteiroOutput(
                processamento_id=processamento_id,
                projeto_id=project_id,
                cliente_nome=project_data["project_customer_name"],
                data_processamento=datetime.now(),
                resumo=resumo,
                pecas_finais=[p.dict() for p in pecas],
                arquivo_xls=nome_arquivo_saida,
                auditoria=[a.dict() for a in self.auditoria_repo.get_all(processamento_id)]
            )
        
        except Exception as e:
            # Registrar erro
            self._registrar_erro(processamento_id, str(e))
            raise
    
    def _gerar_numero_lote(self) -> int:
        """Gera próximo número de lote"""
        from apps.pcp.models import LotePCP
        ultimo = LotePCP.objects.order_by("-numero_lote").first()
        return (ultimo.numero_lote or 0) + 1 if ultimo else 1
    
    def _gerar_nome_arquivo(self, project_id: str, processing_id: str) -> str:
        """Ex: abc123_projeto_0108966599.xls"""
        return f"{processing_id}_projeto_{project_id}.xls"
    
    def _gerar_xls(self, pecas: List["PecaOperacional"], nome_arquivo: str) -> bytes:
        """Converte lista de peças para XLS"""
        # Usar utils/excel.py existente
        return gerar_xls_roteiro(pecas)
    
    def _registrar_erro(self, processamento_id: str, erro: str):
        """Registra erro no banco"""
        ProcessamentoPCP.objects.create(
            id=processamento_id,
            nome_arquivo="ERROR",
            total_pecas=0,
            arquivo_saida=f"ERROR: {erro}"
        )
```

---

## 6. TESTES (CRÍTICO)

### 6.1 Estrutura de Testes

```python
# tests/test_consolidador_ripas.py
import pytest
from apps.pcp.domain.consolidador_ripas import ConsolidadorRipas
from apps.pcp.schemas.peca import PecaOperacional, Dimensoes

def test_consolida_ripas_simples():
    """1 ripa com 20 peças de 100mm em chapa de 2750mm"""
    consolidador = ConsolidadorRipas()
    
    ripa = PecaOperacional(
        id_dinabox="test_1",
        ref_completa="M1 - P1",
        descricao="RIPA CORTE",
        quantidade=20,
        dimensoes=Dimensoes(altura=100, largura=500, espessura=18),
        tags_markdown={"_ripa_"},
        modulo_ref="M1",
        modulo_nome="Test",
        ref_peca="P1"
    )
    
    pecas_saida, auditorias = consolidador.consolidar([ripa])
    
    # Deve gerar 1 tira (20 peças de 100mm + refilo)
    assert len(pecas_saida) == 1
    assert pecas_saida[0].descricao == "RIPA CORTE"
    assert pecas_saida[0].quantidade == 1
    
# tests/test_roteiros.py
def test_roteiro_peca_simples():
    """Peça sem duplagem, sem furo, sem borda = apenas COR"""
    from apps.pcp.domain.roteiros import RoteiroCalculator, Setor
    
    peca = PecaOperacional(
        id_dinabox="test_1",
        ref_completa="M1 - P1",
        descricao="PAINEL SIMPLES",
        quantidade=1,
        dimensoes=Dimensoes(altura=100, largura=500, espessura=18),
        modulo_ref="M1",
        modulo_nome="Test",
        ref_peca="P1"
    )
    
    roteiro = RoteiroCalculator.calcular(peca)
    
    assert len(roteiro.setores) == 1
    assert roteiro.setores[0] == Setor.COR
    assert roteiro.como_string == "COR"

# tests/test_dinabox_repository.py
def test_parsear_json_closetmarcelo():
    """Testa parsing do JSON real do closetmarcelo"""
    import json
    with open("tests/fixtures/closetmarcelo.json") as f:
        project_data = json.load(f)
    
    from apps.pcp.repositories.dinabox_repository import DinaboxRepository
    pecas = DinaboxRepository.parsear_para_pecas_operacionais(project_data)
    
    # Verificar estrutura básica
    assert len(pecas) > 0
    assert all(p.id_dinabox for p in pecas)
    assert all(p.ref_completa for p in pecas)
    assert all(p.dimensoes.largura or p.dimensoes.altura for p in pecas)
```

---

## 7. MIGRAÇÃO PASSO A PASSO

### Estratégia: Feature Flag + Gradual

```python
# settings.py
USE_NEW_PCP_PIPELINE = True  # Feature flag

# api/views.py
def processar_view(request):
    if settings.USE_NEW_PCP_PIPELINE:
        # Novo pipeline
        service = ProcessadorRoteiroService()
        output = service.processar_projeto_dinabox(project_id)
    else:
        # Legado
        output = processar_projeto_dinabox_legado(project_id)
    
    return Response(output.dict())
```

**Fase de migração**:
1. **Semana 1-4**: Implementar novo código em paralelo
2. **Semana 5**: Testes intensivos com dados reais (closetmarcelo, outros projetos)
3. **Semana 6**: Feature flag ativada para 10% dos usuários
4. **Semana 7**: 50% dos usuários
5. **Semana 8**: 100% dos usuários
6. **Semana 9**: Remover código legado

---

## 8. BENEFÍCIOS DA REFATORAÇÃO

| Aspecto | Antes | Depois |
|---------|-------|--------|
| **Testabilidade** | Difícil (DataFrame é estado global) | Fácil (Pydantic validado) |
| **Rastreamento** | Nenhum | Auditoria completa por peça |
| **Manutenção** | Espalhada em utils | Centralizada em Services + Domain |
| **Reutilização** | Difícil (acoplado a DataFrame) | Fácil (Services são reutilizáveis) |
| **Tipagem** | Nenhuma | Pydantic em todos os estágios |
| **Debugging** | Impossível ("qual roteiro foi aplicado?") | Trivial (log de cada decisão) |
| **Performance** | OK (DataFrame pesado) | Melhor (Pydantic leve) |
| **Escalabilidade** | Limitada (um projeto por requisição) | Melhor (stateless services) |

---

## 9. PRÓXIMOS PASSOS

1. **Implementar Fase 1-5** seguindo cronograma acima
2. **Escrever testes unitários** para cada Domain class
3. **Testar com closetmarcelo.json** e outros projetos reais
4. **Documentar decisões** em ADR (Architecture Decision Records)
5. **Treinar time** sobre nova estrutura
6. **Remover código legado** após confirmação

---

**Documento revisado**: Paulo (Desenvolvedor PCP)  
**Próxima reunião**: Aprovação e kickoff Fase 1
