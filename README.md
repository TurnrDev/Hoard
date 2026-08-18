# Hoard

A D&D 5e tool for our campaign with specific tools for our homebrew rules. You won't be interested.

## Project layout

- `hoard/` contains the Django project configuration and application packages.
- `hoard/campaigns/` contains the campaign application, imported as `hoard.campaigns`.
- `frontend/` is the Vue/Vite frontend. Django serves its production build.

Run Django management commands from the repository root:

```sh
docker compose up -d db
uv run python manage.py migrate
uv run python manage.py runserver
```

In a second terminal, run the frontend development server:

```sh
cd frontend
npm install
npm run dev
```

Open the application at `http://localhost:8000`: `django-vite` renders the SPA
HTML, while Vite supplies development modules and hot reload from port 5173. For a
production build, run `npm run build` in `frontend/`, then `uv run python manage.py
collectstatic --noinput`. Run Django with `DJANGO_DEBUG=false` to make django-vite
load the compiled manifest rather than the development server.

If the tools are not installed locally, enter the repository's declarative
development environment once with `nix-shell`. It provides Python, `uv`, Node,
npm, Git, and Docker Compose; the commands above remain the normal workflow.

The Compose database is available at `localhost:5432` with the development
database name, user, and password all set to `hoard`. Override the
`POSTGRES_DB`, `POSTGRES_USER`, `POSTGRES_PASSWORD`, `POSTGRES_HOST`, and
`POSTGRES_PORT` environment variables as needed.

## Campaign API and items

The session-authenticated JSON API is rooted at `/api/campaigns/<campaign_id>/`.
Campaign game masters can post ledger actions; campaign members can create
shared custom item definitions. See [the API guide](docs/api.md) and [the item
catalogue guide](docs/items.md). Initialise the pinned source catalogue with:

```sh
git submodule update --init --recursive
uv run python manage.py import_rpg_companion_items
```

The frontend login uses the same Django session as the API. Its additional API
endpoints and role-scoped ledger history are documented in [the API guide](docs/api.md).

## AI Policy

Listen here, I'm a software dev, have been making Django apps since before you were even a stain on your parents bedsheets. I'm taking assistance to speed things up, and I don't care.
