#!/usr/bin/env sh
set -eu

RUN_ESTOQUE_SEEDS="${RUN_ESTOQUE_SEEDS:-0}"

sh ./bootstrap/01_migrate.sh
sh ./bootstrap/02_seed_initial_access.sh

if [ "$RUN_ESTOQUE_SEEDS" = "1" ]; then
  echo "[bootstrap] Executando seeds de estoque..."
  python manage.py seed_categorias
  python manage.py seed_estoque_padroes
fi

echo "[bootstrap] Bootstrap completo finalizado."

