#!/bin/sh
set -e

# Run migrations if requested (non-fatal — container starts regardless)
if [ "${RUN_MIGRATIONS:-false}" = "true" ]; then
    echo "Running database migrations..."
    if alembic -c alembic/alembic.ini upgrade head; then
        echo "Migrations completed successfully."
    else
        echo "WARNING: Migrations failed. The application will start without migrations."
        echo "Run 'alembic -c alembic/alembic.ini upgrade head' manually to retry."
    fi
fi

exec "$@"
