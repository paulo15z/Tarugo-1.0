# Permissoes e Usuarios Iniciais (Bipagem MVP)

Este arquivo consolida a configuracao inicial de acessos para o MVP de Bipagem por macroetapas.

## Usuarios definidos

| username             | email                   | first_name | last_name  | is_staff |
|----------------------|-------------------------|------------|------------|----------|
| gestao               | gestao@tarugo.local     | Usuario    | Gestao     | True     |
| operador.maquina1    | operador1@tarugo.local  | Operador   | Maquina 1  | False    |
| operador.maquina2    | operador2@tarugo.local  | Operador   | Maquina 2  | False    |
| pcp                  | pcp@tarugo.local        | Usuario    | PCP        | False    |

## Grupos utilizados

- `Gestao`
- `Operador Maquina`
- `PCP`

## Vinculo usuario -> grupo

- `gestao` -> `Gestao`
- `operador.maquina1` -> `Operador Maquina`
- `operador.maquina2` -> `Operador Maquina`
- `pcp` -> `PCP`

## Permissoes por grupo (configurar no /admin)

### Grupo `Gestao`
- Objetivo: visao executiva somente leitura.
- Permissoes recomendadas:
- `view` em todos os modelos de `pcp`, `bipagem` e `estoque`.
- Sem `add/change/delete` operacionais.

### Grupo `Operador Maquina`
- Objetivo: operacao de bipagem no posto, sem administracao.
- Permissoes recomendadas:
- `view` em `pcp.ProcessamentoPCP`, `pcp.LotePCP`, `pcp.AmbientePCP`, `pcp.ModuloPCP`, `pcp.PecaPCP`.
- `add` + `view` em `bipagem.EventoBipagem`.
- Sem `delete` em qualquer modelo.
- Sem `change` estrutural de PCP/Estoque.

### Grupo `PCP`
- Objetivo: controlar ciclo do lote e acompanhamento operacional.
- Permissoes recomendadas:
- `view` + `change` em `pcp.ProcessamentoPCP`, `pcp.LotePCP`, `pcp.PecaPCP`.
- `view` em `bipagem.EventoBipagem`.
- Sem `delete` em eventos.
- `add/change/view` em `estoque.Reserva` (se PCP for dono do fluxo de reserva).

## Regras operacionais complementares

- Acoes sensiveis (estorno, retrocesso de etapa, liberacao de bloqueio) devem exigir validacao de perfil supervisor quando implementadas.
- Mesmo com permissao de modelo, a validacao final deve continuar no backend por regra de negocio.

