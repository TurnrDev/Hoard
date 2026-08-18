# Hoard

A D&D 5e tool for our campaign with specific tools for our homebrew rules. You won't be interested.

## Project layout

- `hoard/` contains the Django project configuration and application packages.
- `hoard/campaigns/` contains the campaign application, imported as `hoard.campaigns`.
- `frontend/` is reserved for a future Vite frontend. Its built assets will be served by Django when that frontend is added.

Run Django management commands from the repository root:

```sh
uv run python manage.py runserver
```

## AI Policy

Listen here, I'm a software dev, have been making Django apps since before you were even a stain on your parents bedsheets. I'm taking assistance to speed things up, and I don't care.
