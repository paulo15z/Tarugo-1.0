#!/usr/bin/env sh
set -eu

echo "[bootstrap] Aplicando migrations..."
python manage.py migrate --noinput
echo "[bootstrap] Migrations concluidas."
