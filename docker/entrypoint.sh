#!/bin/sh
set -eu

case "${1:-app}" in
    app)
        python manage.py migrate --noinput
        python manage.py collectstatic --noinput
        exec daphne \
            --bind 0.0.0.0 \
            --port 8000 \
            --websocket-max-message-size "${DAPHNE_WEBSOCKET_MAX_MESSAGE_SIZE:-16777216}" \
            --websocket-max-frame-size "${DAPHNE_WEBSOCKET_MAX_FRAME_SIZE:-16777216}" \
            hoard.asgi:application
        ;;
    dev)
        python manage.py migrate --noinput
        exec daphne \
            --bind 0.0.0.0 \
            --port 8000 \
            --websocket-max-message-size "${DAPHNE_WEBSOCKET_MAX_MESSAGE_SIZE:-16777216}" \
            --websocket-max-frame-size "${DAPHNE_WEBSOCKET_MAX_FRAME_SIZE:-16777216}" \
            hoard.asgi:application
        ;;
    worker)
        exec celery -A hoard worker --loglevel="${CELERY_LOG_LEVEL:-INFO}"
        ;;
    *)
        exec "$@"
        ;;
esac
