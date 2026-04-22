# Sprint 02 - Rastreabilidade e Comprometimento de Materiais

## Objetivo
Levar o Estoque do nivel "saldo confiavel" para o nivel "estoque comprometido com a producao". Ao final desta sprint, o sistema ja consegue amarrar material a lotes, projetos ou ordens internas de forma rastreavel.

## Resultado funcional da sprint
- Estoque integrado ao PCP por contratos formais.
- Reservas amarradas a contexto real de producao: lote, modulo, ambiente ou demanda.
- Rastreabilidade minima de entrada e consumo por lote, espessura e origem.
- Visao funcional do que esta:
  - disponivel
  - reservado
  - comprometido com producao
  - consumido

## Problema que esta sprint resolve
Saber saldo total nao basta. Numa industria moveleira, o que importa e saber qual material ja esta prometido para um lote, qual chapa esta comprometida, e o que ainda pode ser usado sem causar ruptura em outro pedido.

## Escopo da entrega

### 1) Reserva deixa de ser generica
- Refatorar `Reserva` para conversar com um contexto operacional mais claro.
- Trocar a nocao antiga de "pedido da bipagem" por um contexto industrial do PCP:
  - `lote_pcp_id`
  - `modulo_id` quando fizer sentido
  - `ambiente`
  - `referencia_externa` para casos manuais
- Permitir reserva por espessura no MDF e por SKU nos demais materiais.

### 2) Rastreabilidade
- Incluir trilha minima de origem e consumo:
  - lote do fornecedor
  - documento de entrada/manual
  - usuario
  - data/hora
  - observacao operacional
- Criar historico consultavel por selector.

### 3) Contrato formal com PCP
- O PCP passa a poder:
  - solicitar reserva preventiva de material para um lote
  - consultar risco de ruptura antes de liberar
  - consultar materiais comprometidos por lote
- A comunicacao deve acontecer por service/interface publica, nunca por acesso direto aos models.

### 4) Regras industriais do MDF
- Tratar MDF nao apenas como "produto por espessura", mas como item critico de planejamento.
- Preparar terreno para:
  - estoque por espessura
  - cobertura minima
  - comprometimento por lote
- Sem entrar ainda em otimizacao de corte ou reaproveitamento.

## Conexoes com outros apps

### PCP
- Integracao principal desta sprint.
- O PCP utiliza o Estoque para:
  - validar disponibilidade antes de liberar lotes
  - reservar materiais chave ao confirmar um lote
  - ler status de comprometimento no historico do lote

### Bipagem
- A Bipagem continua sem ser dona do estoque.
- Nesta fase ela pode, no maximo, consultar informacoes consolidadas do Estoque para exibicao, sem alterar dominio.

### Futuro app de compras
- Preparar campo e trilha para futura entrada de mercadoria, sem precisar reabrir o dominio depois.

## Entregaveis tecnicos
- Novo modelo ou remodelagem de reserva/comprometimento.
- Schemas e services formais para integracao com PCP.
- Selectors para:
  - materiais por lote
  - disponibilidade por familia/espessura
  - historico de consumo e comprometimento
- UI funcional de consulta por lote, ambiente e familia de material.

## Criterios de aceite
- Um lote PCP consegue reservar materiais via interface publica do Estoque.
- O Estoque consegue mostrar claramente o que esta comprometido com cada lote.
- Cancelar ou reverter um lote recompõe os compromissos corretamente.
- Nao existe mais dependencia da Reserva em `Pedido` da Bipagem.
- Historico de entrada e consumo e consultavel por operador administrativo.

## Fora do escopo
- Sugestao de compra automatica.
- Integracao com fornecedor externo.
- OEE, apontamento de maquina ou consumo automatico por equipamento.

## Valor para a operacao
Esta sprint faz o Estoque deixar de ser apenas almoxarifado e passar a ser parte real do planejamento. A empresa passa a enxergar o que existe e, principalmente, o que ja esta comprometido.
