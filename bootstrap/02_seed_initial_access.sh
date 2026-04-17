#!/usr/bin/env sh
set -eu

DEFAULT_PASSWORD="${DEFAULT_PASSWORD:-Trocar123!}"
RESET_PASSWORDS="${RESET_PASSWORDS:-0}"

echo "[bootstrap] Garantindo grupos iniciais..."
python manage.py seed_initial_groups

echo "[bootstrap] Garantindo usuarios iniciais..."
if [ "$RESET_PASSWORDS" = "1" ]; then
  python manage.py seed_initial_users --default-password "$DEFAULT_PASSWORD" --reset-passwords
else
  python manage.py seed_initial_users --default-password "$DEFAULT_PASSWORD"
fi

echo "[bootstrap] Seed de acesso concluido."
