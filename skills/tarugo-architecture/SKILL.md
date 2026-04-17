---
name: tarugo-architecture
description: Guia oficial de arquitetura, padrões e fluxo de desenvolvimento do Tarugo (Django para indústria moveleira). Use este skill para criar novo código, revisar PRs, refatorar módulos (especialmente PCP), onboarding de desenvolvedores ou decidir onde colocar lógica. Define separação Models/Services/Selectors/Schemas e regras obrigatórias.
license: MIT
---

# 🏗️ Tarugo Architecture Guide

Guia oficial de arquitetura e padrões do Tarugo.

## Quando Usar Este Skill

Use obrigatoriamente quando:
- Criar ou modificar qualquer código no projeto
- Revisar Pull Requests
- Refatorar módulos (principalmente PCP)
- Onboard novos desenvolvedores
- Decidir arquitetura de novas funcionalidades

## Princípios Arquiteturais Obrigatórios

**Separação clara de responsabilidades**:

| Camada          | Responsabilidade                          | Localização       | Regra de Ouro |
|-----------------|-------------------------------------------|-------------------|---------------|
| **Models**      | Estrutura de dados + ORM + properties     | `models/`         | Sem regras de negócio |
| **Services**    | **Regras de negócio**                     | `services/`       | **Toda** lógica aqui |
| **Selectors**   | Consultas complexas e reutilizáveis       | `selectors/`      | Centralizar queries |
| **Schemas**     | Validação de negócio (Pydantic)           | `schemas/`        | Validação dupla |
| **Mappers**     | Conversão Model ↔ Schema                  | `mappers/`        | Manter models limpos |
| **Domain**      | Enums, tipos e lógica pura                | `domain/`         | Independente |
| **API**         | Camada HTTP (DRF)                         | `api/`            | Apenas serialização + chamar Service |

**Fluxo padrão**:
Request → DRF Serializer → Service (Pydantic) → Selector/Model → Banco → Response
text**Nunca** coloque regra de negócio em views, api/views ou serializers.

## Módulos Atuais e Status

| App              | Responsabilidade                              | Status               | Padrão |
|------------------|-----------------------------------------------|----------------------|--------|
| `core`           | Autenticação e base                           | ✅                   | Bom |
| `estoque`        | Produtos, movimentações, categorias           | ✅ MVP maduro         | **Melhor exemplo** |
| `pcp`            | Roteiros Dinabox, ripas, planos de corte      | ✅ Em produção        | Parcial (ainda tem legado) |
| `bipagem`        | Scanner + controle de produção                | ✅ Em produção        | Bom |
| `integracoes`    | Importação Dinabox                            | ✅ Em evolução        | Bom |

**Referência**: App `estoque` é o que mais segue o padrão ideal atualmente.

## Estrutura Recomendada por App

Veja o template completo em `templates/app_structure_template.md`.

## Regras Críticas (não negociáveis)

- Toda lógica de negócio deve estar em **Service**
- Validação de negócio → **Pydantic**
- Consultas complexas → **Selector**
- PCP ainda possui código legado (`pcp_service.py`) → deve ser migrado gradualmente para o novo padrão

## Recursos da Skill

- **references/** → Documentação complementar (leia quando necessário)
- **templates/** → Modelos prontos para copiar
- **scripts/** → Ferramentas auxiliares

---

**Última atualização**: 03 de abril de 2026

**Próximos passos recomendados**:
- Refatorar PCP para seguir 100% o padrão Service + Pydantic (ver `references/pcp-refatoracao.md`)
- Expandir `tarugo-frontend-design` para telas