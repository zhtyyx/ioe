# Docker deployment guide

[简体中文](README.docker_zh.md) · [Back to project guide](README.md)

The repository provides `docker-compose.yml` and `docker-compose.prod.yml`. Both run the same Django container with SQLite. The `prod` file mainly changes the default `DEBUG` value to `False`; it is an example, not a complete production deployment.

## Prepare

Install Docker and the Docker Compose plugin (`docker compose`). From the repository root:

```bash
git clone https://github.com/zhtyyx/ioe.git
cd ioe
cp .env.template .env
python3 -c 'import secrets; print(secrets.token_urlsafe(50))'
```

Put the generated random value in `.env` as `SECRET_KEY`. Replace the template placeholder and keep `.env` out of version control. Set `ALLOWED_HOSTS` to the hostnames or addresses you will use, separated by commas. Set `DEBUG=True` for local debugging if needed; keep it `False` for a public deployment.

Compose currently passes only `DEBUG`, `SECRET_KEY`, and `ALLOWED_HOSTS` to Django. The database remains SQLite. Other entries in `.env` do not automatically configure a different database or email backend.

## Start

For local use:

```bash
docker compose up -d --build
docker compose exec web python manage.py migrate
docker compose exec web python manage.py collectstatic --noinput
docker compose exec web python manage.py createsuperuser
```

Open <http://localhost:8000/> and sign in. Run `createsuperuser` only when setting up a new environment. Run `migrate` again after code updates or when attaching a fresh data volume. The Dockerfile runs migrations and collects static files while building the image, but the running container uses mounted volumes for the database and static files; the runtime commands above are still needed.

To use the production example, replace `docker compose` in the commands above with `docker compose -f docker-compose.prod.yml`. Before starting, set `DEBUG=False`, a suitable `ALLOWED_HOSTS`, and a random `SECRET_KEY` in `.env`. This configuration still exposes port 8000 directly and bind-mounts the checkout. It does not include an HTTPS reverse proxy or other production hardening.

## Data and operations

| Location | Contents |
| --- | --- |
| `db_volume` | SQLite database at `/app/db` in the container |
| `media_volume` | Uploaded images at `/app/media` |
| `static_volume` | Collected static files at `/app/staticfiles` |
| `logs/` in the checkout | Application logs, bind-mounted to the host |

Useful commands:

```bash
docker compose logs -f web
docker compose exec web python manage.py check
docker compose down
```

`docker compose down` retains the named volumes. Avoid `down -v` when data must be kept. Back up both the database and media volumes. Add `-f docker-compose.prod.yml` to these commands when using the production example.

The Dockerfile configures Tsinghua mirrors for apt and pip during image builds. These mirrors only affect dependency downloads inside the build.
