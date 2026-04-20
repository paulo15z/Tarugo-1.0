# Sprint 03 - Inteligencia Operacional e Prontidao para Industrializacao

## Objetivo
Transformar o Estoque em apoio ativo ao planejamento industrial, com sinais claros de ruptura, cobertura e necessidade de reposicao. Ao final desta sprint, o Estoque passa a responder nao so "o que tenho hoje", mas "o que vou precisar para sustentar a producao".

## Resultado funcional da sprint
- Dashboard operacional com foco industrial.
- Alertas reais de ruptura e cobertura por familia/espessura/material critico.
- Base pronta para conversar com compras e com futuras celulas de usinagem/furacao sem retrabalho estrutural.
- App entregue como modulo funcional e util mesmo sem depender de uma futura automacao avancada.

## Problema que esta sprint resolve
Ter saldo e reserva ainda nao basta para industrializar. A marcenaria planejada precisa prever falta, enxergar gargalos de material e agir antes que o PCP ou a fabrica parem.

## Escopo da entrega

### 1) Painel industrial de estoque
- Criar visoes praticas para gestao:
  - materiais criticos
  - baixo estoque
  - alta demanda por lote/periodo
  - MDF por espessura
  - itens sem localizacao
  - itens sem rastreabilidade minima
- Priorizar legibilidade e decisao rapida, nao apenas listagem administrativa.

### 2) Cobertura e risco de ruptura
- Introduzir indicadores simples e acionaveis:
  - saldo disponivel
  - saldo comprometido
  - consumo recente
  - cobertura estimada
  - risco de ruptura
- Regras devem ser pragmaticas e transparentes, sem "caixa preta".

### 3) Preparacao para compras e abastecimento
- Gerar lista de necessidade baseada em:
  - minimo configurado
  - disponibilidade atual
  - comprometimento com lotes
  - materiais criticos
- Mesmo sem um app de compras pronto, a saida ja deve ser util para acao manual.

### 4) Preparacao para industria moveleira 4.0
- Deixar o dominio pronto para crescer em direcao a:
  - consumo por etapa
  - integracao com usinagem e furacao
  - apontamento por ordem/lote
  - rastreabilidade de entrada ate consumo
- Sem prometer automacao completa agora, mas sem bloquear a evolucao.

## Conexoes com outros apps

### PCP
- O PCP passa a consumir:
  - alertas de ruptura por lote
  - materiais comprometidos
  - disponibilidade consolidada para decisao de liberacao
- O historico do PCP pode exibir resumo de impacto em estoque por lote quando isso agregar valor.

### Bipagem
- A Bipagem pode consultar dados consolidados de material apenas para contexto visual, sem possuir regra de estoque.
- Nenhuma baixa de estoque deve nascer na Bipagem sem service formal do Estoque.

### Futuro Compras / Suprimentos
- Esta sprint entrega a ponte natural para um futuro modulo de compras:
  - lista de reposicao
  - materiais criticos
  - necessidade por espessura
  - referencia de origem/lote

## Entregaveis tecnicos
- Dashboard do Estoque com filtros operacionais e leitura clara.
- Selectors analiticos para ruptura, cobertura e necessidade.
- Services para consolidacao de sinais e priorizacao de materiais.
- API para outros apps consultarem risco e disponibilidade de forma padronizada.

## Criterios de aceite
- O gestor consegue identificar quais materiais ameacam a producao.
- O PCP consegue consultar risco de ruptura antes de liberar lote.
- O sistema consegue sugerir uma lista de reposicao manual coerente.
- MDF critico por espessura fica visivel e priorizado.
- A estrutura continua seguindo o padrao Tarugo sem empurrar regra para views.

## Fora do escopo
- Integracao direta com fornecedor.
- MRP completo.
- IoT de maquina, leitura de sensores ou apontamento automatico.

## Valor para a operacao
Esta sprint fecha a remodelagem do Estoque com uma entrega que ja conversa com a industrializacao real: previsao, priorizacao e decisao. Nao e ainda uma smart factory completa, mas ja deixa a empresa agindo como industria, e nao apenas reagindo como oficina.
