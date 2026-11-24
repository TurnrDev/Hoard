# Nix builds

The flake builds Hoard and its frontend for x86_64-linux and aarch64-linux.
Python dependencies come from `uv.lock`; frontend dependencies come from
`package-lock.json`. The development shell supplies Python, uv and Node;
existing development commands remain unchanged.

```sh
nix build .#hoard -o /tmp/hoard-native
nix build .#checks.x86_64-linux.runtime -o /tmp/hoard-runtime-check
```

The package provides:

- `hoard-server`: Daphne; pass bind/port options and `hoard.asgi:application`.
- `hoard-manage`: Django management commands, such as `migrate --noinput`.
- `hoard-worker`: Celery worker; accepts the normal worker options.
- `hoard-beat`: Celery scheduler; set a writable `--schedule` path.
- `hoard-python`: Python with Hoard and its locked production dependencies.

Run migrations and `collectstatic` before starting the server. Supply secrets
and database/Redis settings at runtime; never put them in a Nix expression.
The deployment owns accounts, service dependencies and persistent directories.
`DJANGO_SECRET_KEY_FILE` and `POSTGRES_PASSWORD_FILE` can point to runtime secret
files (for example systemd credentials). When set, a file takes precedence over
the corresponding environment value. Existing environment-only setups still work.

Set `HOARD_STATIC_ROOT` to a writable absolute path for production. Its default
remains `staticfiles` beneath the project root for development and Docker.
BlackNoise serves collected static files through the existing ASGI process;
no separate nginx service is needed. Hashed Vite assets get immutable caching;
stable filenames get a short cache lifetime. WebSockets retain their existing
Channels application. User-uploaded media is no longer served or mounted.
The packaged frontend and application code stay read-only in the Nix store.

After changing `package-lock.json`, update `npmDepsHash` in `nix/package.nix`:

```sh
nix run nixpkgs#prefetch-npm-deps -- package-lock.json
```

Update Python dependencies with the normal uv workflow. Commit the application
locks and `flake.lock` alongside packaging changes. Production infrastructure
should consume a pinned revision of this flake.
