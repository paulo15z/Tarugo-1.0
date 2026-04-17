# Bootstrap (Deploy / Docker)

Diretorio unico para scripts de inicializacao, ao lado do `manage.py`.

## Scripts

- `bootstrap/01_migrate.sh`
  - Aplica migrations.
- `bootstrap/02_seed_initial_access.sh`
  - Garante grupos e usuarios iniciais.
- `bootstrap/99_bootstrap_all.sh`
  - Executa migrate + acesso.
  - Opcionalmente executa seeds de estoque.

## Variaveis de ambiente

- `DEFAULT_PASSWORD` (default: `Trocar123!`)
- `RESET_PASSWORDS` (`0` ou `1`, default: `0`)
- `RUN_ESTOQUE_SEEDS` (`0` ou `1`, default: `0`)

## Execucao manual (container ou host Linux)

```sh
sh ./bootstrap/99_bootstrap_all.sh
```

Com reset de senha e seed de estoque:

```sh
DEFAULT_PASSWORD='SenhaForte123!' RESET_PASSWORDS=1 RUN_ESTOQUE_SEEDS=1 sh ./bootstrap/99_bootstrap_all.sh
```
