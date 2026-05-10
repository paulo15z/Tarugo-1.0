---
name: tarugo-frontend-design
description: Cria interfaces frontend profissionais, limpas e otimizadas para o Tarugo (sistema industrial moveleiro). Use este skill sempre que precisar construir ou melhorar telas, componentes ou páginas (ex: dashboard de lotes, tela de bipagem, listagem de PCP, formulários de estoque). Prioriza legibilidade em ambiente fabril, hierarquia clara, usabilidade rápida e estética Industrial Clean. Evita designs genéricos ou excessivamente artísticos.
license: MIT
---

# 🎨 Tarugo Frontend Design

Guia oficial de design frontend para o Tarugo — sistema para indústria moveleira.

## Quando Usar Este Skill

Use sempre que precisar:
- Criar uma nova tela ou página (dashboard, bipagem, PCP, estoque, etc.)
- Melhorar ou refatorar interface existente
- Desenvolver componentes reutilizáveis (cards de progresso, tabelas, feedback de bipagem)
- Definir estilo visual consistente em todo o sistema

## Diretrizes de Design do Tarugo

**Estilo principal**: **Industrial Clean**

Características obrigatórias:
- Legibilidade máxima (ambiente de fábrica com iluminação variável)
- Hierarquia visual forte
- Feedback rápido e claro
- Interface pensada para uso em telas grandes (computadores e tablets)
- Pouca distração visual — foco na informação

### Paleta de Cores (CSS Variables)

```css
:root {
  --bg: #0a0a0a;
  --surface: #1a1a1a;
  --surface-2: #252525;
  --primary: #3b82f6;        /* Azul industrial */
  --success: #22c55e;
  --warning: #eab308;
  --danger: #ef4444;
  --text: #f1f1f1;
  --text-muted: #a3a3a3;
  --border: #3f3f46;
}
Tipografia

Headings: Fonte com personalidade (Satoshi, Space Grotesk ou Inter Display — peso 600/700)
Body / Textos: Inter ou system sans-serif (peso 400/500)
Tamanhos generosos:
Base: 16px
Headings: 20–28px
Labels e textos pequenos: 14px


Princípios de Layout

Cards grandes e bem espaçados (especialmente para progresso de lotes e módulos)
Tabelas com status coloridos e legíveis
Área de bipagem com feedback gigante (sucesso/erro)
Sidebar de navegação limpa
Muito espaço negativo (breathing room)
Suporte a modo escuro como padrão (melhor para fábrica)

Motion & Interações

Transições suaves (200–300ms)
Feedback imediato na bipagem (scale + cor + ícone)
Loading states claros e não intrusivos
Hover states sutis em botões e cards
Animações de entrada com stagger apenas quando agrega valor

Componentes Mais Usados

Card de Progresso (Pedido / Lote / Módulo)
Tela de Bipagem (foco total)
Tabela de Peças com status
Dashboard por lote base
Formulários simples e grandes


Como Criar Interfaces com Este Skill

Escolha o tipo de tela/componente
Defina o objetivo principal (ex: "usuário precisa bipar rápido")
Aplique a paleta Industrial Clean
Garanta hierarquia clara (informação crítica em destaque)
Inclua estados: vazio, loading, sucesso, erro
Teste legibilidade em fundo escuro

Exemplos de prompts bons:

"Crie a tela principal de bipagem com feedback grande"
"Melhore o dashboard de lotes mantendo estilo industrial clean"
"Desenvolva o card de progresso de módulo"

Referências Complementares

Veja references/component-examples.md para exemplos de código de componentes comuns
Veja references/color-system.md para paleta detalhada e casos de uso
Veja templates/ para boilerplates prontos


Última atualização: 03 de abril de 2026
Regra de Ouro:
"Deve parecer um sistema profissional de fábrica — confiável, rápido e sem frescuras, nunca um dashboard bonito de startup."