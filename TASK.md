# TODO – Tarugo (Atualizado 29/03/2026)

## Fase Atual: Fortalecer Estoque (B → A → C)

### B – Refinar Backend do Estoque (Próximo)
- [ ] Melhorar `MovimentacaoService` (adicionar usuário logado automaticamente, observação obrigatória opcional)
- [ ] Criar/aperfeiçoar `EstoqueSelector` (get_saldo_atual, get_movimentacoes_recentes, get_produtos_baixo_estoque)
- [ ] Adicionar transaction.atomic em todas as movimentações
- [ ] Criar service para ajuste em lote (opcional)

### A – Controle de Acessos
- [ ] Criar grupos padrão via data migration (`Almoxarife`, `PCP`, `Gerente`)
- [ ] Adicionar custom permissions nos models de estoque
- [ ] Criar `EstoquePermissionMixin` em `apps/core/mixins.py`
- [ ] Proteger views e templates

### C – Frontend para Almoxarife
- [ ] Criar templates em `apps/estoque/templates/estoque/`
- [ ] `EstoqueDashboardView`
- [ ] `MovimentacaoCreateView` (form simples e rápido)
- [ ] `ProdutoListView` com filtros
- [ ] Tabelas legíveis + botões de ação

### Futuro (após fase atual)
- Histórico completo de movimentações
- Relatórios simples (CSV/XLS)
- Celery para tarefas pesadas
- Migração para PostgreSQL

Prioridade: Simplicidade + usabilidade para o almoxarife.