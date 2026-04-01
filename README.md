txsftp
======

A virtualized SFTP server backed by PostgreSQL, built on the [Twisted](https://twisted.org/) networking library.

Users are configured entirely via database — no system accounts required. Each user is restricted to their own home directory and authenticated via password or SSH public key.

Features
--------

- Password and SSH public-key authentication
- Per-user chroot to a configured home directory (auto-created on first login)
- Pluggable server class via `server-class` config key
- Runs as an unprivileged service

Requirements
------------

- Python 3.13+
- PostgreSQL
- [uv](https://github.com/astral-sh/uv) (for local development)

Quick start (Docker)
--------------------

```bash
docker compose up
```

The default compose file starts a PostgreSQL database and the SFTP server on port 8888. Add users with the script described below before connecting.

Configuration
-------------

Configuration is loaded from `/etc/txsftp.json`. When running via Docker, the entrypoint generates this file from environment variables:

| Variable | Default | Description |
|---|---|---|
| `SFTP_PORT` | `8888` | Port to listen on |
| `SERVER_CLASS` | `txsftp.handler.GPGFileTransferServer` | SFTP server implementation class |
| `ACCESS_LOG` | `/dev/null` | Access log path |
| `ERROR_LOG` | _(stdout)_ | Error log path |
| `DB_HOST` | `db` | PostgreSQL host |
| `DB_PORT` | `5432` | PostgreSQL port |
| `DB_NAME` | `txsftp` | Database name |
| `DB_USER` | `txsftp` | Database user |
| `DB_PASSWORD` | _(required)_ | Database password |

SSH host keys are generated at build time and stored in `/etc/txsftp/`. Mount a named volume over `/etc/txsftp` to persist keys across image rebuilds.

Adding users
------------

Use the provided script (run inside the container or with DB env vars set):

```bash
# Inside the container (home defaults to /data/sftp/<username>)
docker compose run txsftp python scripts/upsert_user.py <username> <password>

# Or via psql directly
docker compose exec db psql -U txsftp -d txsftp
```

The `password` column stores a DES crypt hash. Generate one with:

```bash
python3 -c "from passlib.hash import des_crypt; print(des_crypt.hash('yourpassword'))"
```

Local development
-----------------

```bash
uv sync
uv run pytest tests/
uv run twistd -n txsftp  # requires a running PostgreSQL and /etc/txsftp.json
```

Schema
------

See [`docker/init.sql`](docker/init.sql) for the full schema. The core table is `sftp_user`:

| Column | Type | Description |
|---|---|---|
| `username` | varchar | Login name (unique) |
| `password` | varchar | DES crypt hash (nullable — disables password auth) |
| `ssh_public_key` | text | OpenSSH public key string (nullable) |
| `home_directory` | varchar | Absolute path, auto-created on first login |
| `last_login` | timestamp | Set to `NOW()` on each successful authentication |
| `last_logout` | timestamp | Set to `NOW()` when the session is closed |
