# Sprints do MVP de Bipagem (Separacao -> Usinagem -> Expedicao)

## Sprint 1 - Fundacao de dominio e acesso

### Escopo
- Definir macroetapas fixas: `SEPARACAO`, `USINAGEM`, `EXPEDICAO`.
- Preparar base de permissao por grupo para operar sem acesso amplo.
- Garantir que o scanner funcione com etapa fixa por posto.

### Entregaveis
- Enum/modelagem de macroetapa.
- Ajustes em schema/service para aceitar etapa fixa de contexto.
- Validacao de permissao por perfil no backend.

### Criterios de aceite
- Operador consegue bipar somente com perfil autorizado.
- Requisicao sem permissao retorna erro 403.

## Sprint 2 - Fluxo por unidade e bloqueio de passagem

### Escopo
- Controlar avanco por unidade de peca.
- Impedir salto de etapa.
- Exibir alerta bloqueante quando houver tentativa de passagem indevida.

### Entregaveis
- Regras de sequencia:
- `USINAGEM` depende de unidade em `SEPARACAO`.
- `EXPEDICAO` depende de unidade em `USINAGEM`.
- Mensagem de bloqueio operacional padronizada.

### Criterios de aceite
- Nao e possivel registrar etapa fora da ordem.
- Bloqueio e rastreavel em log.

## Sprint 3 - Estorno e retrocesso supervisor

### Escopo
- Estorno retorna unidade para estado anterior nao-bipado daquela etapa.
- Retrocesso de etapa apenas por supervisor.

### Entregaveis
- Fluxo de estorno por unidade.
- Acao de retrocesso com motivo obrigatorio.
- Trilha de auditoria de liberacoes/retrocessos.

### Criterios de aceite
- Operador nao consegue retroceder etapa sem permissao.
- Supervisor consegue liberar, com motivo registrado.

## Sprint 4 - Painel e retorno operacional

### Escopo
- Ajustar telas de retorno para macroetapas.
- Organizar leitura separando eventos normais e estornos.
- Destacar bloqueios e liberacoes por supervisor.

### Entregaveis
- Painel com status por macroetapa.
- Indicadores por unidade concluida/pendente.
- Log operacional limpo para acompanhamento de PCP e gestao.

### Criterios de aceite
- Leitura de status sem ambiguidade.
- Rastreabilidade completa por unidade e etapa.

## Sprint 5 - Consolidacao tecnica

### Escopo
- Consolidar `PecaPCP` como unica fonte da verdade operacional.
- Reduzir acoplamento com modelos legados de bipagem.

### Entregaveis
- Plano de deprecacao do legado.
- Ajustes finais de seletor/service/admin.
- Documentacao de operacao e suporte.

### Criterios de aceite
- Sem duplicidade de estado de peca entre modelos.
- Fluxo end-to-end validado em homologacao.

