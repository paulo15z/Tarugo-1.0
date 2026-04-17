# Sprint Roadmap - App Pedidos

## Contexto
O app `Pedidos` sera o kanban macro de acompanhamento por `Ambiente`.

Regras centrais do dominio:
- `Pedido` e o cabecalho.
- `Ambiente` e o cartao operacional real.
- Um pedido so termina quando todos os seus ambientes terminam.
- `HistoricoEtapa` guarda cada passagem de um ambiente por uma etapa.
- Integracoes com `Bipagem`, `PCP`, `Estoque` e `Compras` existem como dependencias, nao como sprints separadas.

Etapas iniciais do fluxo:
- `COMERCIAL`
- `PROJETOS`
- `COMPRAS`
- `PCP`
- `PRODUCAO`
- `CQL + EXPEDICAO`
- `MONTAGEM`

## Sprint 1 - Fundacao do dominio de Pedidos

### Objetivo
Criar a base estrutural do app `Pedidos` com os modelos e regras essenciais para trabalhar por ambiente.

### Escopo
- Criar `Etapa` como catalogo configuravel.
- Criar `Pedido` como entidade pai.
- Criar `Ambiente` como unidade operacional do kanban.
- Criar `HistoricoEtapa` como trilha de auditoria do fluxo.
- Definir status agregado do pedido com base nos ambientes.
- Calcular previsao final do pedido como a maior previsao entre os ambientes.

### Entregaveis
- Modelos principais definidos.
- Services com regras basicas de criacao e atualizacao.
- Selectors para consolidar pedido, ambientes e historico.
- Admin ou API minima para inspecao do dominio.

### Criterios de aceite
- Um pedido pode existir com zero ou mais ambientes.
- Um ambiente pertence a um unico pedido.
- O pedido mostra progresso agregado sem depender de etapa atual unica.
- O historico registra entrada e saida de etapa por ambiente.

### Fora do escopo
- Automacao com PCP.
- Reservas de estoque.
- Lista de compras.

## Sprint 2 - Entrada comercial e montagem rapida de ambientes

### Objetivo
Permitir que o Comercial crie pedidos e ambientes de forma rapida, com pouco atrito operacional.

### Escopo
- Criacao de pedido a partir de dados basicos do cliente.
- Adicao em massa de ambientes.
- Ordenacao de ambientes dentro do pedido.
- Edicao de nome, descricao e previsao por ambiente.
- Definicao do ambiente inicial por regra do negocio.
- Opcional de vinculacao com orcamento.

### Entregaveis
- Tela ou endpoint de criacao rapida.
- Validacoes para nomes duplicados de ambiente no mesmo pedido.
- Regras para ativar o primeiro status de cada ambiente.
- Fluxo comercial simples para abrir e revisar pedidos.

### Criterios de aceite
- O Comercial consegue abrir um pedido e cadastrar varios ambientes em uma unica interacao.
- Cada ambiente nasce ja posicionado na etapa inicial correta.
- Nao ha duplicidade de ambiente no mesmo pedido.
- A previsao individual do ambiente fica visivel e editavel.

### Fora do escopo
- Avanco automatico por PCP.
- Movimentacao de estoque.
- Sugestao de compra.

## Sprint 3 - Fluxo operacional por ambiente e integracao com PCP

### Objetivo
Fazer o pedido refletir a execucao real da producao por ambiente, com integracao flexivel ao PCP.

### Escopo
- Vinculo flexivel entre `Pedido`/`Ambiente` e `ProcessamentoPCP`.
- Permitir que um lote do PCP aponte para varios ambientes.
- Permitir que um ambiente seja encontrado em mais de um contexto de lote quando necessario.
- Avancar ambiente para a etapa `PCP` quando identificado no processamento.
- Registrar no historico a origem da movimentacao.
- Exibir um resumo por pedido com ambientes em cada etapa.

### Entregaveis
- Relacionamento de integracao com PCP.
- Service para receber o retorno do PCP e atualizar ambientes.
- Historico completo das transicoes originadas por lote.
- Resumo operacional do pedido com contagem por status.

### Criterios de aceite
- Um lote pode atualizar varios ambientes sem forcar relacao 1:1.
- O historico mostra quando o PCP moveu um ambiente.
- O pedido consolida corretamente ambientes em andamento, concluidos e pendentes.
- O fluxo nao quebra quando o mesmo lote envolve varios pedidos.

### Fora do escopo
- Planejamento de producao dentro do PCP.
- Compras automatizadas.
- Liberacao de material no estoque.

## Sprint 4 - Kanban operacional, governanca e visibilidade

### Objetivo
Transformar o pedido em uma tela operacional de acompanhamento com leitura clara para comercial, producao e gestao.

### Escopo
- Kanban por etapa com cartoes de ambiente.
- Filtros por cliente, pedido, etapa e status.
- Marcacao de atrasos e previsao vencida.
- Tela de detalhe do pedido com resumo do progresso.
- Trilha visual do historico de etapas do ambiente.
- Regras de permissao para visualizar e mover ambientes.

### Entregaveis
- Interface principal do kanban.
- Visao consolidada do pedido.
- Componentes de status e atraso.
- Controle minimo de permissao por perfil.

### Criterios de aceite
- Um usuario consegue enxergar rapidamente em que etapa esta cada ambiente.
- O pedido mostra progresso agregado sem ambiguidade.
- A visao de historico permite auditar o caminho de um ambiente.
- Apenas perfis autorizados conseguem executar acoes sensiveis.

### Fora do escopo
- Integracao financeira.
- Regras de reserva de estoque.
- Compra efetiva em lista externa.

## Sprint 5 - Orquestracao para estoque e compras

### Objetivo
Fechar o ciclo do `Pedidos` criando os ganchos operacionais para estoque e compras, sem transformar esses apps em requisito da sprint.

### Escopo
- Gerar sinalizacao de necessidade de material a partir do pedido e de seus ambientes.
- Expor contexto de consumo esperado por ambiente.
- Preparar dados para reserva futura no estoque.
- Preparar dados para sugestao na lista de compras.
- Consolidar falta, urgencia e prioridade por pedido.
- Criar contrato para integracao com a lista de compras.

### Entregaveis
- Service de consolidacao de necessidades por pedido.
- Estrutura para exportar demandas por ambiente.
- Contrato de integracao com estoque e compras.
- Resumo de pendencias para compras com base no pedido.

### Criterios de aceite
- O app `Pedidos` consegue indicar o que falta para atender um pedido.
- A necessidade fica ligada a um ambiente, nao apenas ao pedido inteiro.
- O mesmo dado pode alimentar estoque e compras sem retrabalho manual.
- A lista de compras recebe um contexto claro de origem e prioridade.

### Fora do escopo
- Tela completa de compras.
- Movimentacao fisica de estoque.
- Regras detalhadas do app de compras.

## Sequencia recomendada
1. Sprint 1 - Fundacao do dominio de Pedidos
2. Sprint 2 - Entrada comercial e montagem rapida de ambientes
3. Sprint 3 - Fluxo operacional por ambiente e integracao com PCP
4. Sprint 4 - Kanban operacional, governanca e visibilidade
5. Sprint 5 - Orquestracao para estoque e compras

## Observacao final
Este roadmap foi desenhado so para o app `Pedidos`.
As dependencias `Bipagem`, `PCP`, `Estoque` e `Compras` entram apenas como integracoes externas que o app precisa consumir ou acionar.
