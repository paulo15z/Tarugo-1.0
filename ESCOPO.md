# ESCOPO – Tarugo

## Escopo Geral
Sistema para controle de estoque, PCP e orçamentos em indústrias moveleiras.

## Escopo Atual – Módulo Estoque (Fase B → A → C)

### Objetivos do Almoxarife
- Registrar entrada, saída, ajuste e transferência de forma rápida
- Visualizar saldo atual por produto e local
- Ver histórico de movimentações
- Receber alertas simples de baixo estoque

### Requisitos Funcionais
- Movimentação atômica (service com transaction)
- Registro automático do usuário responsável
- Filtros por material, local, data
- Interface limpa e rápida (sem JavaScript pesado por enquanto)

### Requisitos Não Funcionais
- Manter padrão: Service + Pydantic + Selector
- Controle de acesso por grupo (Almoxarife, PCP, Gerente)
- Código testável e reutilizável
- Sem overengineering

### Fora do Escopo Atual
- PCP (congelado)
- Multi-tenant por empresa
- Integração com ERP
- Dashboard avançado com gráficos

Versão: 29/03/2026