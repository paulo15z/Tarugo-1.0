# Sprint 01 - Fundacao do Estoque Industrial

## Objetivo
Transformar o app `estoque` em fonte confiavel de verdade para materiais, saldos e disponibilidade, alinhado ao padrao Tarugo. Ao final desta sprint, a empresa ja consegue responder com seguranca: "o que existe?", "onde esta?", "o que esta reservado?" e "o que esta disponivel para produzir?".

## Resultado funcional da sprint
- App `estoque` operando com dominio proprio, desacoplado da `bipagem`.
- Estoque com separacao clara entre saldo fisico, saldo reservado e saldo disponivel.
- Movimentacoes e reservas validadas por services, com leitura centralizada em selectors.
- Interface funcional para consulta e operacao basica de estoque sem depender de outros apps.

## Problema que esta sprint resolve
Hoje o estoque tem uma boa base, mas ainda mistura responsabilidades com outros apps e nao representa com clareza a disponibilidade real para a producao. Sem isso, o PCP pode planejar em cima de um saldo ilusorio.

## Escopo da entrega

### 1) Dominio e arquitetura
- Refatorar `apps/estoque` para seguir estritamente:
  - `models/` para persistencia
  - `services/` para regras de negocio
  - `selectors/` para consultas
  - `schemas/` para contratos Pydantic
  - `api/` para endpoints finos
- Eliminar acoplamentos diretos com `apps/bipagem`.
- Criar uma interface publica do Estoque para outros apps consumirem sem acessar models diretamente.

### 2) Modelo operacional minimo
- Formalizar no dominio:
  - `saldo_fisico`
  - `saldo_reservado`
  - `saldo_disponivel`
- Manter tratamento elegante para MDF por espessura.
- Preservar `categoria`, `familia`, `localizacao`, `lote` e `atributos_especificos`, mas com contratos mais claros.

### 3) Movimentacao consistente
- Unificar o schema de movimentacao.
- Padronizar tipos permitidos no dominio.
- Implementar regras transacionais para:
  - entrada
  - saida
  - ajuste
- Remover inconsistencias como `transferencia` existir em um contrato e nao no outro.

### 4) Reserva industrial basica
- Reserva deixa de ser "anotacao" e passa a impactar saldo disponivel.
- Cancelamento libera disponibilidade.
- Consumo baixa a reserva e registra trilha operacional.

## Conexoes com outros apps

### PCP
- O PCP passa a consultar o Estoque por interface publica para saber disponibilidade de materiais criticos antes de liberar ou planejar lotes.
- Nesta sprint, a integracao e de leitura:
  - disponibilidade por SKU/familia/espessura
  - alertas de baixo estoque

### Bipagem
- Nenhuma dependencia de model ou service da Bipagem deve permanecer dentro do Estoque.
- A Bipagem deixa de ser referencia de projeto/pedido dentro do dominio do Estoque.

### Auth / permissoes
- Continuar usando usuarios e grupos do Django.
- Perfis minimos:
  - consulta
  - movimentacao
  - administracao de cadastro

## Entregaveis tecnicos
- Refactor dos services, selectors e schemas do `estoque`.
- Endpoints/API para:
  - listar produtos
  - consultar saldo e disponibilidade
  - movimentar estoque
  - reservar
  - cancelar/consumir reserva
- UI funcional para operacao basica e consulta.
- Migrations necessarias para suportar os novos campos e regras.

## Criterios de aceite
- Um item comum e um item MDF podem ser movimentados sem inconsistencia.
- Uma reserva reduz disponibilidade sem reduzir saldo fisico.
- Cancelar reserva recompõe a disponibilidade.
- Consumir reserva conclui a baixa corretamente.
- PCP consegue consultar disponibilidade sem acessar models do Estoque.
- `estoque` nao importa models/services da `bipagem`.

## Fora do escopo
- Sugestao automatica de compras.
- Rastreabilidade completa por fornecedor e nota fiscal.
- Integracao profunda com lote/modulo do PCP.

## Valor para a operacao
Esta sprint entrega o primeiro bloco realmente industrial: parar de planejar no escuro. Mesmo sem compras automatizadas, a empresa passa a ter base confiavel para decidir se pode ou nao produzir.
