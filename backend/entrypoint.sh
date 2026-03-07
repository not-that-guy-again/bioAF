#!/bin/sh
set -e

# Run migrations if requested
if [ "${RUN_MIGRATIONS:-false}" = "true" ]; then
    echo "Running database migrations..."
    alembic -c alembic/alembic.ini upgrade head
fi

exec "$@"
