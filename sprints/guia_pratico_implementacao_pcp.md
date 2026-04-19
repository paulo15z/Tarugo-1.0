# 💻 Guia Prático: Implementação da Refatoração PCP

**Objetivo**: Fornecer código pronto para copiar/colar, com exemplos reais baseados em `closetmarcelo.json`

---

## Parte 1: Schemas Pydantic

### 1.1 Arquivo: `apps/pcp/schemas/dinabox.py`

```python
"""
Representação estruturada do JSON retornado pela API Dinabox.
Estes schemas são usados APENAS no repository para parse.
NÃO são expostos fora da camada de integração.
"""

from decimal import Decimal
from typing import Optional, List, Dict
from pydantic import BaseModel, Field, ConfigDict, field_validator


class MaterialDinabox(BaseModel):
    """Material extraído do Dinabox"""
    id: str
    name: str
    width: Decimal = Field(..., gt=0)
    height: Decimal = Field(..., gt=0)
    vein: bool = False
    
    model_config = ConfigDict(from_attributes=True)


class EdgeDinabox(BaseModel):
    """Borda (aresta) de uma peça"""
    name: Optional[str] = None
    perimeter: Decimal = 0
    thickness: int = 0
    
    model_config = ConfigDict(from_attributes=True)


class PartDinabox(BaseModel):
    """Peça individual do Dinabox (part = peça)"""
    id: str
    ref: str = Field(..., min_length=1)
    name: str = Field(..., min_length=1)
    type: str = "cabinet"
    count: int = Field(..., gt=0)
    
    # Dimensões em mm
    width: Decimal = Field(..., gt=0)
    height: Decimal = Field(..., gt=0)
    thickness: Decimal = Field(..., gt=0)
    
    # Material
    material: Optional[MaterialDinabox] = None
    
    # Técnico
    note: Optional[str] = None
    code_a: Optional[str] = None
    code_b: Optional[str] = None
    code_a2: Optional[str] = None
    code_b2: Optional[str] = None
    
    # Bordas em cada face
    edge_left: Optional[EdgeDinabox] = None
    edge_right: Optional[EdgeDinabox] = None
    edge_top: Optional[EdgeDinabox] = None
    edge_bottom: Optional[EdgeDinabox] = None
    
    model_config = ConfigDict(from_attributes=True, extra="allow")


class ModuleDinabox(BaseModel):
    """Módulo do projeto (conjunto de peças)"""
    id: str
    mid: str  # Módulo ID alternativo
    ref: str = Field(..., min_length=1)
    name: str = Field(..., min_length=1)
    type: str = "thickened"  # ou "normal"
    
    # Peças do módulo
    parts: List[PartDinabox] = Field(default_factory=list)
    
    # Material base do módulo
    material: Optional[MaterialDinabox] = None
    
    # Bordas padrão do módulo (herança para peças)
    edge_left: Optional[EdgeDinabox] = None
    edge_right: Optional[EdgeDinabox] = None
    edge_top: Optional[EdgeDinabox] = None
    edge_bottom: Optional[EdgeDinabox] = None
    
    model_config = ConfigDict(from_attributes=True, extra="allow")


class ProjectoDinabox(BaseModel):
    """Estrutura principal do JSON retornado pela API"""
    project_id: str = Field(..., min_length=8, max_length=8)
    project_customer_name: str
    project_customer_id: str
    project_description: str
    project_status: str
    project_created: str
    project_last_modified: str
    project_author_name: str
    
    # Array principal
    woodwork: List[ModuleDinabox] = Field(default_factory=list)
    
    # Arrays secundários (nem sempre usados no PCP)
    holes: Optional[List[Dict]] = None
    partners: Optional[List[Dict]] = None
    components: Optional[Dict] = None
    
    model_config = ConfigDict(from_attributes=True, extra="allow")

    @field_validator("project_id")
    @classmethod
    def validar_project_id(cls, v):
        """Project ID deve ter 10 dígitos"""
        if not v.isdigit() or len(v) != 10:
            raise ValueError("Project ID inválido")
        return v
```

### 1.2 Arquivo: `apps/pcp/schemas/peca.py` (refatorada)

```python
"""
Representação de uma peça após passar por validação e enriquecimento.
Este é o "Core Domain" da peça para o PCP.
"""

from decimal import Decimal
from datetime import datetime
from typing import Optional, Set, Dict, Literal
from pydantic import BaseModel, Field, ConfigDict, field_validator


class Dimensoes(BaseModel):
    """Dimensões validadas de uma peça"""
    largura: Optional[Decimal] = Field(None, ge=0)
    altura: Optional[Decimal] = Field(None, ge=0)
    espessura: Optional[Decimal] = Field(None, ge=0)
    metro_quadrado: Optional[Decimal] = Field(None, ge=0)
    
    @field_validator("largura", "altura", "espessura", "metro_quadrado", mode="before")
    @classmethod
    def converter_decimal(cls, v):
        """Converte string com vírgula para Decimal"""
        if v is None or str(v).strip() in ("", "nan", "NaN"):
            return None
        try:
            # Vírgula é separador decimal em PT-BR
            return Decimal(str(v).replace(",", "."))
        except Exception:
            return None
    
    def tem_dimensoes(self) -> bool:
        """Verifica se há pelo menos uma dimensão válida"""
        return any([self.largura, self.altura, self.espessura])


class BordaInfo(BaseModel):
    """Informação sobre uma borda/aresta"""
    face: Literal["left", "right", "top", "bottom"]
    nome: Optional[str] = None
    perimetro_mm: Decimal = 0
    espessura_mm: int = 0
    
    def tem_acabamento(self) -> bool:
        return bool(self.nome)


class Furacao(BaseModel):
    """Informação sobre um ponto de furação"""
    posicao: Literal["A", "B", "A2", "B2"]
    codigo_bipagem: Optional[str] = None
    
    def tem_furacao(self) -> bool:
        return bool(self.codigo_bipagem)


class PecaOperacional(BaseModel):
    """
    Representação de uma peça pronta para processamento PCP.
    
    Esta é a entidade central do domínio. Contém:
    - Identificação (ID, referências)
    - Geometria (dimensões)
    - Contexto (módulo, material)
    - Marcações técnicas (tags, observações)
    - Resultado do processamento (roteiro, plano)
    """
    
    # ========== IDENTIFICAÇÃO ==========
    id_dinabox: str = Field(..., description="ID único da peça no Dinabox")
    ref_completa: str = Field(..., description='Ex: "M2803574 - P2808386"')
    ref_modulo: Optional[str] = None
    ref_peca: Optional[str] = None
    descricao: str = Field(..., min_length=1)
    
    # ========== LOCALIZAÇÃO ==========
    modulo_ref: str = Field(..., description="Ref do módulo pai")
    modulo_nome: str = Field(..., description="Nome do módulo")
    contexto: Optional[str] = None
    
    # ========== GEOMETRIA ==========
    quantidade: int = Field(..., gt=0)
    dimensoes: Dimensoes
    material_id: Optional[str] = None
    material_nome: Optional[str] = None
    material_com_veio: bool = False
    
    # ========== ACABAMENTO ==========
    bordas: Dict[str, BordaInfo] = Field(default_factory=dict)
    
    # ========== PROCESSAMENTO ==========
    furacoes: Dict[str, Optional[str]] = Field(
        default_factory=dict,
        description='{"A": codigo_ou_none, "B": ..., "A2": ..., "B2": ...}'
    )
    eh_duplada: bool = False
    
    # ========== ANOTAÇÕES ==========
    observacoes_original: Optional[str] = None
    tags_markdown: Set[str] = Field(
        default_factory=set,
        description='Conjunto extraído de observações, ex: {"_ripa_", "_painel_"}'
    )
    
    # ========== RESULTADO ==========
    roteiro: Optional[str] = None  # Ex: "COR → FUR → BOR"
    plano_corte: Optional[str] = None  # Ex: "05"
    lote_saida: Optional[str] = None  # Ex: "1-05"
    
    # ========== AUDITORIA ==========
    data_criacao: datetime = Field(default_factory=datetime.now)
    id_auditoria: Optional[str] = None
    
    model_config = ConfigDict(from_attributes=True, extra="allow")
    
    # ========== MÉTODOS DE NEGÓCIO ==========
    
    def eh_ripa(self) -> bool:
        """Detecta se é uma ripa (por tag ou descrição)"""
        return (
            "_ripa_" in self.tags_markdown or 
            "ripa" in self.descricao.lower()
        )
    
    def eh_duplada_de_verdade(self) -> bool:
        """Confirmação dupla: tag + marcação"""
        return self.eh_duplada and "_dup_" in self.tags_markdown
    
    def tem_furacoes(self) -> bool:
        """Verifica se tem alguma furação registrada"""
        return any(self.furacoes.values())
    
    def tem_bordas(self) -> bool:
        """Verifica se tem bordas com acabamento"""
        return any(b.tem_acabamento() for b in self.bordas.values())
    
    def eh_pequena(self) -> bool:
        """Classifica peças muito pequenas"""
        d = self.dimensoes
        if not d.tem_dimensoes():
            return False
        return (d.altura or 0) < 100 and (d.largura or 0) < 100
    
    def eh_grande(self) -> bool:
        """Classifica peças grandes"""
        d = self.dimensoes
        if not d.tem_dimensoes():
            return False
        return (d.altura or 0) > 1000 or (d.largura or 0) > 1000


class ResumoPecas(BaseModel):
    """Resumo estatístico do processamento"""
    total_entrada: int
    total_saida: int
    ripas_geradas: int
    pecas_consolidadas: int
    variacao: int
    
    @property
    def houve_consolidacao(self) -> bool:
        return self.variacao < 0


class ProcessarRoteiroOutput(BaseModel):
    """Resposta completa de um processamento PCP"""
    processamento_id: str
    projeto_id: str
    cliente_nome: str
    data_processamento: datetime
    
    resumo: ResumoPecas
    pecas_finais: List[PecaOperacional]
    arquivo_xls: Optional[str] = None
    
    auditoria: Optional[List[Dict]] = None
    
    class Config:
        from_attributes = True
```

---

## Parte 2: Domain (Regras de Negócio)

### 2.1 Arquivo: `apps/pcp/domain/roteiros.py`

```python
"""
Lógica pura de cálculo de roteiro.
Não depende de Django, banco de dados ou frameworks.
100% testável.
"""

from enum import Enum
from typing import List
from pydantic import BaseModel
from apps.pcp.schemas.peca import PecaOperacional


class Setor(str, Enum):
    """Setores de produção mapeados para a indústria"""
    
    COR = "COR"      # Corte (serra circular)
    FUR = "FUR"      # Furação/Usinagem (CNC)
    BOR = "BOR"      # Borda (máquina de borda)
    XBOR = "XBOR"    # Borda Extra (ripas especiais)
    DUP = "DUP"      # Duplagem (colagem/espelhamento)
    MCX = "MCX"      # Montagem de Caixa (estrutural)
    MPE = "MPE"      # Montagem Portas e Externos
    MAR = "MAR"      # Marcenaria (customizações)
    PRE = "PRE"      # Pré-Montagem (sub-conjuntos)
    ASS = "ASS"      # Acabamento Simples (lixamento, etc)
    
    def __str__(self):
        return self.value


class Roteiro(BaseModel):
    """Sequência ordenada de setores"""
    setores: List[Setor]
    
    @property
    def como_string(self) -> str:
        """Representação legível: 'COR → FUR → BOR'"""
        if not self.setores:
            return "NENHUM"
        return " → ".join(str(s) for s in self.setores)
    
    def __str__(self):
        return self.como_string
    
    def __repr__(self):
        return f"Roteiro({self.como_string})"
    
    def __len__(self):
        return len(self.setores)
    
    def contem(self, setor: Setor) -> bool:
        return setor in self.setores
    
    def indice_de(self, setor: Setor) -> int:
        """Retorna posição do setor ou -1"""
        try:
            return self.setores.index(setor)
        except ValueError:
            return -1


class RoteiroCalculator:
    """
    Calcula roteiro baseado em características da peça.
    
    Princípios:
    1. Sequência industrial fixa: COR (sempre) → DUP → FUR → BOR → Especializados
    2. Cada setor ativado apenas se há critério
    3. Ripas têm tratamento especial (XBOR extra)
    """
    
    @staticmethod
    def calcular(peca: PecaOperacional) -> Roteiro:
        """
        Calcula roteiro para uma peça individual.
        
        Regras:
        - COR: Sempre (corte obrigatório)
        - DUP: Se eh_duplada (exceto ripas)
        - FUR: Se tem_furacoes()
        - BOR: Se tem_bordas()
        - XBOR: Se é ripa E tem bordas
        
        Exemplo:
            Peca normal com furação e borda: [COR, FUR, BOR]
            Peça duplada com furação: [COR, DUP, FUR]
            Ripa com borda: [COR, BOR, XBOR]
        """
        setores = []
        
        # 1. Sempre COR (corte)
        setores.append(Setor.COR)
        
        # 2. DUP se duplada (mas não ripas)
        if peca.eh_duplada and not peca.eh_ripa():
            setores.append(Setor.DUP)
        
        # 3. FUR se tem furação
        if peca.tem_furacoes():
            setores.append(Setor.FUR)
        
        # 4. BOR se tem bordas
        if peca.tem_bordas():
            setores.append(Setor.BOR)
        
        # 5. XBOR especial: borda em ripa (após BOR)
        if peca.eh_ripa() and peca.tem_bordas():
            setores.append(Setor.XBOR)
        
        return Roteiro(setores=setores)
    
    @staticmethod
    def calcular_batch(pecas: List[PecaOperacional]) -> List[Roteiro]:
        """Calcula roteiro para múltiplas peças (mais eficiente)"""
        return [RoteiroCalculator.calcular(p) for p in pecas]
    
    @staticmethod
    def roteiro_descricao(roteiro: Roteiro) -> str:
        """Descrição em linguagem natural do roteiro"""
        desc = []
        for setor in roteiro.setores:
            if setor == Setor.COR:
                desc.append("Corte estrutural na serra")
            elif setor == Setor.DUP:
                desc.append("Duplagem/Colagem")
            elif setor == Setor.FUR:
                desc.append("Furação/Usinagem CNC")
            elif setor == Setor.BOR:
                desc.append("Acabamento de bordas")
            elif setor == Setor.XBOR:
                desc.append("Acabamento borda especial (ripa)")
            elif setor == Setor.MCX:
                desc.append("Montagem estrutural caixas")
            elif setor == Setor.MPE:
                desc.append("Montagem portas e frentes")
            elif setor == Setor.MAR:
                desc.append("Marcenaria customizada")
            elif setor == Setor.PRE:
                desc.append("Pré-montagem subconjuntos")
            elif setor == Setor.ASS:
                desc.append("Acabamento final e lixamento")
        
        return " → ".join(desc)
```

### 2.2 Arquivo: `apps/pcp/domain/planos.py`

```python
"""
Lógica de determinação de plano de corte.
Mapeia características da peça para planos operacionais.
"""

from enum import Enum
from typing import Literal, List, Tuple
from pydantic import BaseModel
from apps.pcp.schemas.peca import PecaOperacional


class PlanoCorte(str, Enum):
    """Planos operacionais de processamento"""
    PINTURA = "01"           # Peças que vão para pintura
    LAMINA = "02"            # Lâminas (folha, revestimento)
    RIPA_CORTE = "03"        # Ripas consolidadas
    MCX = "04"               # Montagem de Caixa
    DUP = "05"               # Peças dupladas/espelhadas
    MPE = "06"               # Montagem Portas/Externos
    PAINEL = "07"            # Painéis de vedação
    PAINEL_ESTRUTURAL = "08" # Painéis estruturais
    DECORATIVO = "09"        # Itens decorativos/acabamento
    PRE_MONTAGEM = "10"      # Pré-montagem (sub-conjuntos)
    OUTROS = "11"            # Indefinido/genérico
    
    def __str__(self):
        return self.value


class DecisaoPlano(BaseModel):
    """Resultado de uma decisão de plano com rastreamento"""
    plano: PlanoCorte
    condicao_aplicada: str  # Nome da regra: "tem_tag_ripa", "é_duplada", etc
    confianca: Literal["high", "medium", "low"]
    
    def __str__(self):
        return f"{self.plano} ({self.confianca}): {self.condicao_aplicada}"


class PlanoCorteCalculator:
    """
    Determina plano de corte em sequência ordenada.
    
    Estratégia: If-then-else com prioridade (primeira match ganha).
    Cada regra é uma tupla: (predicado, plano, confiança, descrição).
    """
    
    # Ordem importa! Primeiras regras têm prioridade
    DECISOES_ORDENADAS: List[Tuple] = [
        # (lambda que testa, PlanoCorte, confiança, descricao)
        
        # Ripas identificadas
        (
            lambda p: "_ripa_" in p.tags_markdown or (p.eh_ripa() and "ripa corte" in p.descricao.lower()),
            PlanoCorte.RIPA_CORTE,
            "high",
            "é_ripa_corte"
        ),
        
        # Pintura explícita
        (
            lambda p: "_pin_" in p.tags_markdown,
            PlanoCorte.PINTURA,
            "high",
            "tem_tag_pintura"
        ),
        
        # Lâminas/revestimentos
        (
            lambda p: "_lamina_" in p.tags_markdown or (
                p.material_nome and "lamina" in p.material_nome.lower()
            ),
            PlanoCorte.LAMINA,
            "high",
            "é_lamina_revestimento"
        ),
        
        # Painéis explícitos
        (
            lambda p: "_painel_" in p.tags_markdown,
            PlanoCorte.PAINEL,
            "high",
            "tem_tag_painel"
        ),
        
        # Duplagem explícita
        (
            lambda p: p.eh_duplada_de_verdade(),
            PlanoCorte.DUP,
            "high",
            "é_duplada"
        ),
        
        # Pré-montagem
        (
            lambda p: "_pre_" in p.tags_markdown or "_prem_" in p.tags_markdown,
            PlanoCorte.PRE_MONTAGEM,
            "high",
            "tem_tag_pre_montagem"
        ),
        
        # Portas e frentes (estruturalmente simples)
        (
            lambda p: "porta" in p.descricao.lower() or "frontal" in p.descricao.lower(),
            PlanoCorte.MPE,
            "medium",
            "é_porta_frontal"
        ),
        
        # Estrutura de gaveta (caixaria)
        (
            lambda p: any(kw in p.descricao.lower() for kw in 
                ["lateral gaveta", "fundo gaveta", "contrafrente"]),
            PlanoCorte.MCX,
            "high",
            "é_estrutura_gaveta"
        ),
        
        # Default: outros
        (
            lambda p: True,
            PlanoCorte.OUTROS,
            "low",
            "default"
        ),
    ]
    
    @staticmethod
    def determinar(peca: PecaOperacional) -> DecisaoPlano:
        """
        Determina plano aplicando regras em sequência.
        Primeira regra que passar é aplicada.
        """
        for predicado, plano, confianca, descricao in PlanoCorteCalculator.DECISOES_ORDENADAS:
            try:
                if predicado(peca):
                    return DecisaoPlano(
                        plano=plano,
                        condicao_aplicada=descricao,
                        confianca=confianca
                    )
            except Exception:
                # Regra com erro → pula para próxima
                continue
        
        # Nunca deve chegar aqui (último é default)
        return DecisaoPlano(
            plano=PlanoCorte.OUTROS,
            condicao_aplicada="erro_fallback",
            confianca="low"
        )
    
    @staticmethod
    def determinar_batch(pecas: List[PecaOperacional]) -> List[DecisaoPlano]:
        """Determina plano para múltiplas peças"""
        return [PlanoCorteCalculator.determinar(p) for p in pecas]
    
    @staticmethod
    def plano_descricao(plano: PlanoCorte) -> str:
        """Descrição legível de um plano"""
        descricoes = {
            PlanoCorte.PINTURA: "Pintura Industrial",
            PlanoCorte.LAMINA: "Lâminas e Revestimentos",
            PlanoCorte.RIPA_CORTE: "Ripas Consolidadas",
            PlanoCorte.MCX: "Montagem Caixaria",
            PlanoCorte.DUP: "Peças Dupladas",
            PlanoCorte.MPE: "Montagem Portas",
            PlanoCorte.PAINEL: "Painéis",
            PlanoCorte.PRE_MONTAGEM: "Pré-Montagem",
            PlanoCorte.OUTROS: "Processamento Genérico",
        }
        return descricoes.get(plano, str(plano))
```

---

## Parte 3: Repository (Camada de Dados)

### 3.1 Arquivo: `apps/pcp/repositories/dinabox_repository.py`

```python
"""
Transforma JSON da API Dinabox em objetos de domínio (PecaOperacional).
Bridge entre o mundo externo (API) e o domínio interno.
"""

from typing import List, Set, Optional, Dict
import re
from apps.pcp.schemas.dinabox import ProjectoDinabox
from apps.pcp.schemas.peca import (
    PecaOperacional, Dimensoes, BordaInfo, Furacao
)


class DinaboxRepository:
    """
    Parse do JSON → PecaOperacional validada.
    
    Responsabilidades:
    - Validação estrutural do JSON
    - Mapeamento de campos
    - Enriquecimento de contexto
    - Extração de tags técnicas
    """
    
    @staticmethod
    def parsear_para_pecas_operacionais(project_data: dict) -> List[PecaOperacional]:
        """
        Converte estrutura JSON do Dinabox em lista de PecaOperacional.
        
        Args:
            project_data: Dict retornado pela API Dinabox
        
        Returns:
            List[PecaOperacional]: Peças estruturadas e validadas
        
        Raises:
            ValueError: Se JSON inválido ou obrigatória faltando
        """
        
        # 1. Validar e coagir para Pydantic
        try:
            projeto = ProjectoDinabox.model_validate(project_data)
        except Exception as e:
            raise ValueError(f"Falha ao validar JSON Dinabox: {e}")
        
        if not projeto.woodwork:
            raise ValueError("Nenhum módulo de madeira (woodwork) encontrado")
        
        pecas = []
        
        # 2. Iterar sobre módulos e peças
        for modulo in projeto.woodwork:
            if not modulo.parts:
                continue
            
            for parte in modulo.parts:
                # Detectar duplagem por anotação
                eh_duplada = DinaboxRepository._detectar_duplagem(parte.note)
                
                # Extrair tags técnicas (#_ripa_, #_painel_, etc)
                tags = DinaboxRepository._extrair_tags(parte.note)
                
                # Mapear bordas (hierarquicamente: parte > módulo)
                bordas = DinaboxRepository._mapear_bordas(parte, modulo)
                
                # Mapear furações
                furacoes = DinaboxRepository._mapear_furacoes(parte)
                
                # Criar peça operacional
                peca = PecaOperacional(
                    # Identificação
                    id_dinabox=parte.id,
                    ref_completa=f"{modulo.ref} - {parte.ref}",
                    ref_modulo=modulo.ref,
                    ref_peca=parte.ref,
                    descricao=parte.name,
                    
                    # Localização
                    modulo_ref=modulo.ref,
                    modulo_nome=modulo.name,
                    contexto=f"MOD: {modulo.name} ({modulo.ref})",
                    
                    # Dimensões
                    quantidade=parte.count,
                    dimensoes=Dimensoes(
                        largura=parte.width,
                        altura=parte.height,
                        espessura=parte.thickness,
                        metro_quadrado=parte.material.width * parte.material.height / 1000000 if parte.material else None
                    ),
                    
                    # Material
                    material_id=parte.material.id if parte.material else None,
                    material_nome=parte.material.name if parte.material else None,
                    material_com_veio=parte.material.vein if parte.material else False,
                    
                    # Acabamento
                    bordas=bordas,
                    
                    # Processamento
                    furacoes=furacoes,
                    eh_duplada=eh_duplada,
                    
                    # Anotações
                    observacoes_original=parte.note,
                    tags_markdown=tags,
                )
                
                pecas.append(peca)
        
        if not pecas:
            raise ValueError("Nenhuma peça foi extraída do projeto")
        
        return pecas
    
    @staticmethod
    def _detectar_duplagem(note: Optional[str]) -> bool:
        """
        Detecta se peça é duplada/engrossada.
        
        Critérios:
        - Contém "_dup_" ou "_duplagem_" em nota
        - Ou "encaminhar p/ duplagem" em texto livre
        """
        if not note:
            return False
        
        note_lower = note.lower()
        return (
            "_dup_" in note_lower or
            "_duplagem_" in note_lower or
            "encaminhar p/ duplagem" in note_lower or
            "duplagem" in note_lower
        )
    
    @staticmethod
    def _extrair_tags(note: Optional[str]) -> Set[str]:
        """
        Extrai tags técnicas no formato _xxx_.
        
        Exemplos:
        - "_ripa_" → ripa de corte
        - "_painel_" → painel
        - "_lamina_" → lâmina/revestimento
        - "_pin_" → pintura
        - "_pre_" → pré-montagem
        """
        if not note:
            return set()
        
        # Padrão: _palavra_ (sublinhado antes e depois)
        matches = re.findall(r"_(\w+)_", note)
        return set(f"_{m}_" for m in matches)
    
    @staticmethod
    def _mapear_bordas(parte, modulo) -> Dict[str, BordaInfo]:
        """
        Mapeia bordas com herança do módulo pai.
        
        Lógica:
        1. Usa borda da peça se tem nome
        2. Senão, herda do módulo (se módulo tem perímetro > 0)
        3. Senão, vazio
        
        Isso é importante para peças dupladas que herdam tratamento do módulo.
        """
        bordas = {}
        
        for face in ["left", "right", "top", "bottom"]:
            edge_parte = getattr(parte, f"edge_{face}", None)
            edge_modulo = getattr(modulo, f"edge_{face}", None)
            
            # Preferência: parte > módulo
            edge = edge_parte if edge_parte and edge_parte.name else None
            
            # Se peça não tem borda, herdar do módulo (se tem perímetro)
            if not edge and edge_modulo and edge_modulo.perimeter > 0:
                edge = edge_modulo
            
            # Montar BordaInfo
            bordas[face] = BordaInfo(
                face=face,
                nome=edge.name if edge and edge.name else None,
                perimetro_mm=edge.perimeter if edge else 0,
                espessura_mm=edge.thickness if edge else 0
            )
        
        return bordas
    
    @staticmethod
    def _mapear_furacoes(parte) -> Dict[str, Optional[str]]:
        """
        Mapeia códigos de furação de bipagem (CNC).
        
        Estrutura:
        - code_a, code_b: Primeira posição de furação
        - code_a2, code_b2: Segunda posição (para peças espelhadas)
        """
        return {
            "A": parte.code_a,
            "B": parte.code_b,
            "A2": parte.code_a2,
            "B2": parte.code_b2,
        }
```

---

## Parte 4: Teste (Exemplo)

### 4.1 Arquivo: `apps/pcp/tests/test_roteiros_real.py`

```python
"""
Testes usando dados reais do closetmarcelo.json
"""

import json
import pytest
from pathlib import Path
from apps.pcp.repositories.dinabox_repository import DinaboxRepository
from apps.pcp.domain.roteiros import RoteiroCalculator, Setor
from apps.pcp.domain.planos import PlanoCorteCalculator, PlanoCorte


@pytest.fixture
def closetmarcelo_json():
    """Carrega o JSON real"""
    path = Path(__file__).parent / "fixtures" / "closetmarcelo.json"
    with open(path) as f:
        return json.load(f)


def test_parsear_closetmarcelo(closetmarcelo_json):
    """Valida parse do JSON real"""
    pecas = DinaboxRepository.parsear_para_pecas_operacionais(closetmarcelo_json)
    
    # Validações estruturais
    assert len(pecas) > 0, "Deve ter extraído peças"
    assert all(p.id_dinabox for p in pecas), "Todas peças com ID"
    assert all(p.ref_completa for p in pecas), "Todas peças com referência"
    assert all(p.dimensoes.tem_dimensoes() for p in pecas), "Todas têm dimensão"
    
    # Validar algumas peças específicas
    tampo = next((p for p in pecas if "tampo engrossado" in p.descricao.lower()), None)
    assert tampo is not None, "Deve ter encontrado o tampo"
    assert tampo.eh_duplada, "Tampo engrossado é duplado"
    assert tampo.bordas["left"].nome == "Nogueira Pecan", "Borda deve ser Nogueira"


def test_calcular_roteiro_peca_simples():
    """Peca sem nada = apenas COR"""
    from apps.pcp.schemas.peca import PecaOperacional, Dimensoes
    
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


def test_calcular_roteiro_peca_complexa():
    """Peça duplada com furação e borda = COR → DUP → FUR → BOR"""
    from apps.pcp.schemas.peca import PecaOperacional, Dimensoes, BordaInfo
    
    peca = PecaOperacional(
        id_dinabox="test_2",
        ref_completa="M1 - P2",
        descricao="PAINEL DUPLADO",
        quantidade=1,
        dimensoes=Dimensoes(altura=100, largura=500, espessura=18),
        modulo_ref="M1",
        modulo_nome="Test",
        ref_peca="P2",
        eh_duplada=True,
        tags_markdown={"_dup_"},
        bordas={
            "top": BordaInfo(face="top", nome="Nogueira", perimetro_mm=5),
            "bottom": BordaInfo(face="bottom"),
            "left": BordaInfo(face="left"),
            "right": BordaInfo(face="right"),
        },
        furacoes={"A": "2260947", "B": None, "A2": None, "B2": None}
    )
    
    roteiro = RoteiroCalculator.calcular(peca)
    
    assert roteiro.como_string == "COR → DUP → FUR → BOR"
    assert Setor.COR in roteiro.setores
    assert Setor.DUP in roteiro.setores


def test_calcular_plano_ripa():
    """Ripa com tag deve ser RIPA_CORTE (03)"""
    from apps.pcp.schemas.peca import PecaOperacional, Dimensoes
    
    peca = PecaOperacional(
        id_dinabox="test_3",
        ref_completa="M1 - P3",
        descricao="RIPA CORTE",
        quantidade=1,
        dimensoes=Dimensoes(altura=100, largura=500, espessura=18),
        modulo_ref="M1",
        modulo_nome="Test",
        ref_peca="P3",
        tags_markdown={"_ripa_"}
    )
    
    decisao = PlanoCorteCalculator.determinar(peca)
    
    assert decisao.plano == PlanoCorte.RIPA_CORTE
    assert decisao.confianca == "high"
    assert "ripa" in decisao.condicao_aplicada.lower()


def test_calcular_plano_duplada():
    """Peça duplada deve ser DUP (05)"""
    from apps.pcp.schemas.peca import PecaOperacional, Dimensoes
    
    peca = PecaOperacional(
        id_dinabox="test_4",
        ref_completa="M1 - P4",
        descricao="PAINEL DUPLADO",
        quantidade=1,
        dimensoes=Dimensoes(altura=100, largura=500, espessura=18),
        modulo_ref="M1",
        modulo_nome="Test",
        ref_peca="P4",
        eh_duplada=True,
        tags_markdown={"_dup_"}
    )
    
    decisao = PlanoCorteCalculator.determinar(peca)
    
    assert decisao.plano == PlanoCorte.DUP
    assert "duplada" in decisao.condicao_aplicada.lower()
```

---

## Próximos Arquivos para Implementar

1. **`apps/pcp/domain/consolidador_ripas.py`** - Lógica de consolidação
2. **`apps/pcp/repositories/lote_pcp_repository.py`** - CRUD de lotes
3. **`apps/pcp/services/processador_roteiro.py`** - Main service
4. **`apps/pcp/api/views.py`** - Atualizar para chamar novo service
5. **Models** - `AuditoriaRoteamento`
6. **Migrations** - Novos fields e tabelas

Este guia fornece base sólida para começar a implementação!
