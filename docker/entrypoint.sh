#!/bin/sh
set -eu

if [ "${HOARD_RUN_MIGRATIONS:-false}" = "true" ]; then
    python manage.py migrate --noinput
    python manage.py update_compendium_registries --no-registry --if-missing
fi

exec "$@"
