# syntax=docker/dockerfile:1

FROM node:24-bookworm-slim AS frontend

WORKDIR /build
COPY package.json package-lock.json ./
RUN npm ci
COPY index.html vite.config.ts tsconfig.json tsconfig.app.json tsconfig.node.json ./
COPY hoard ./hoard
RUN npm run build

FROM ghcr.io/astral-sh/uv:0.8.22 AS uv

FROM python:3.14-slim-bookworm AS application

ENV DJANGO_DEBUG=false \
    PYTHONFAULTHANDLER=1 \
    PYTHONUNBUFFERED=1 \
    UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy \
    PATH=/app/.venv/bin:$PATH

WORKDIR /app
COPY --from=uv /uv /uvx /bin/
COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-dev --no-install-project

COPY . .
COPY --from=frontend /build/hoard/dist ./hoard/dist
RUN test -x hoard/compendium/native/tools/linux-x64/refresh_system_builder \
    && hoard/compendium/native/tools/linux-x64/refresh_system_builder --help >/dev/null \
    && hoard/compendium/native/tools/linux-x64/refresh_system_builder \
        --base=hoard/compendium/systems/default/systems \
        --output=hoard/compendium/systems/compiled \
        --clean \
        --structured-diagnostics \
    && python manage.py collectstatic --noinput \
    && addgroup --system hoard \
    && adduser --system --ingroup hoard --home /app hoard \
    && mkdir -p /app/media \
    && chown -R hoard:hoard /app/media

USER hoard
EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=5s --start-period=20s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/', timeout=3)" || exit 1

ENTRYPOINT ["/bin/sh", "/app/docker/entrypoint.sh"]
CMD ["daphne", "--bind", "0.0.0.0", "--port", "8000", "--websocket-max-message-size", "16777216", "--websocket-max-frame-size", "16777216", "hoard.asgi:application"]
