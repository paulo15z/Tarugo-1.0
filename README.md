# Tarugo

Sistema modular desenvolvido em Django para indústrias moveleiras de alto padrão.

---

## 📌 Contexto

Projeto de estudo e aplicação prática na empresa.  
Objetivo principal: resolver problemas reais do dia a dia (estoque, produção, integrações).  
Pode evoluir para SaaS no futuro, mas prioridade atual é uso interno + aprendizado.

---

## 🎯 Objetivo Atual (Março/2026)

Fortalecer o módulo **estoque** para uso real pelo almoxarife:
- Refinar backend (services e selectors)
- Implementar controle de acessos por papéis
- Criar interface web simples e rápida (templates Django)

Em seguida: PCP fica congelado por enquanto.

---

## 🧱 Arquitetura (mantida)

- **models** → estrutura de dados
- **services** → regras de negócio (nunca na view!)
- **selectors** → consultas otimizadas ao banco
- **api** → DRF (mantida)

**Regra de ouro:** Regra de negócio sempre no Service + validação com Pydantic.

---

## 📦 Módulos

| Módulo       | Status                  | Próximos passos |
|--------------|-------------------------|-----------------|
| **core**     | Base + autenticação     | Controle de acessos (grupos e permissões) |
| **estoque**  | Funcional               | **Foco atual** – refinar para almoxarife + frontend |
| **pcp**      | Funcional               | Congelado temporariamente |
| **integracoes** | Base iniciada        | Futuro |
| **orcamentos** | Planejado             | Após estoque |
| **scripts**  | Planejado               | Biblioteca de utilitários |

---

## 🚀 Próximos Passos (Ordem definida)

1. **B** – Refinar backend do `estoque` (services + selectors)
2. **A** – Controle de acessos (grupos, permissões, mixin)
3. **C** – Frontend para almoxarife (dashboard + form de movimentação rápida)

---

## Stack

Django + DRF + Pydantic + Templates Django (Bootstrap recomendado)