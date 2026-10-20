# Contributing to Hoard

Thank you for contributing to Hoard. This guide covers the local environment,
routine checks, release-version workflow, deployment, and architecture.

## Local development

Running `nix-shell` provides Python 3.14, uv, Node.js, npm, Git, and Docker Compose.
Docker Compose is the supported way to run the full stack; the shell is useful for
repository checks and maintenance.

Start the development environment with Daphne, Vite live reload, PostgreSQL, and
Redis:

```sh
docker compose -f compose.dev.yml up --build
```

Open `http://localhost:5173`. Vite proxies HTTP uploads, media, the release manifest,
and WebSockets to Daphne. Django is also available directly at
`http://localhost:8000`.

The application container applies migrations when it starts. Stop the stack without
removing its database or uploaded portraits with:

```sh
docker compose -f compose.dev.yml down
```

Add `--volumes` only when intentionally recreating the unsupported pre-release
database and all local uploads.

## Verification

Run these checks from a second terminal while the development stack is running:

```sh
docker compose -f compose.dev.yml exec app uv run pytest --reuse-db
docker compose -f compose.dev.yml exec app uv run ruff check hoard
docker compose -f compose.dev.yml exec frontend npm test
docker compose -f compose.dev.yml exec frontend npm run build
```

## Release versions

Use the project command to update the frontend and Python version declarations
together:

```sh
npm run version:bump -- patch
```

Replace `patch` with `minor` or `major` as appropriate. The command refuses to run
when existing version declarations do not agree.

## Production deployment

Production runs Daphne, Celery, PostgreSQL, Redis, and Nginx. Nginx serves static
assets and uploaded media directly. Traefik routes application HTTP and WebSocket
traffic straight to Daphne, while sending `/static/` and `/media/` requests to
Nginx.

Create the external network and local production environment file once:

```sh
docker network create web
cp .env.example .env
sudo install -d -o 1000 -g 1000 -m 0755 \
  /data/appdata/hoard/media \
  /data/appdata/hoard/static
```

Set a long random `DJANGO_SECRET_KEY` and a strong `POSTGRES_PASSWORD` in `.env`,
then build and start the deployment for `https://dnd.turnr.net`:

```sh
docker compose up -d --build
```

Compose loads `.env` automatically. Database names and users can be changed with
`POSTGRES_DB` and `POSTGRES_USER`. Persistent production data is stored below
`/data/appdata/hoard`. The application image runs as UID/GID `1000`, so its media
and static directories must be writable by that account before the first start.

To inspect status and logs:

```sh
docker compose ps
docker compose logs -f app worker nginx
```

## Architecture

- Django owns authentication, campaign data, portrait uploads, and the initial SPA
  response. Nginx serves uploaded media directly in production.
- Application queries and commands use authenticated WebSockets. HTTP is limited to
  session/CSRF operations, portrait uploads, static/media delivery, and the release
  manifest.
- Redis carries campaign broadcasts, cache data, and Celery messages.
- PostgreSQL stores the campaign, audit, money, and XP ledgers.
- Vue and PrimeVue provide the browser application; Vite builds its production
  assets into `hoard/dist`.

See [the API guide](docs/api.md) and [the initial release brief](docs/initial-release.md)
for the protocol and release scope.

## AI policy

Listen here, I'm a software dev, have been making Django apps since before you were
even a stain on your parents bedsheets. I'm taking assistance to speed things up,
and I don't care.
