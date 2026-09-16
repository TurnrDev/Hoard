FROM node:22-bookworm-slim AS frontend

WORKDIR /build

COPY package.json package-lock.json ./
RUN npm ci

COPY index.html vite.config.ts tsconfig.json tsconfig.app.json tsconfig.node.json ./
COPY hoard ./hoard
RUN npm run build


FROM ghcr.io/astral-sh/uv:python3.14-bookworm-slim AS runtime

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy \
    UV_PROJECT_ENVIRONMENT=/opt/venv \
    PATH="/opt/venv/bin:$PATH"

WORKDIR /app

COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-dev --no-install-project

COPY . .
COPY --from=frontend /build/hoard/dist ./hoard/dist
COPY --chmod=755 docker/entrypoint.sh /usr/local/bin/hoard-entrypoint

RUN useradd --create-home --uid 1000 hoard \
    && mkdir -p /app/media /app/staticfiles \
    && chown -R hoard:hoard /app/media /app/staticfiles

USER hoard

EXPOSE 8000

ENTRYPOINT ["hoard-entrypoint"]
CMD ["app"]
