# Deploy with a Docker image

[简体中文](README.docker_zh.md) · [Project guide](README.md) · [Build status](https://github.com/zhtyyx/ioe/actions/workflows/publish-image.yml)

Use `ghcr.io/zhtyyx/ioe:latest` without cloning the source or building on your server. Images support Linux AMD64 and ARM64. Install Docker and **Docker Compose 2.23.1 or newer**.

## 1. Download the deployment configuration

Start in a new deployment directory:

```bash
mkdir -p ioe
cd ioe
curl -fsSL https://raw.githubusercontent.com/zhtyyx/ioe/main/docker-compose.prod.yml -o compose.yaml
curl -fsSL https://raw.githubusercontent.com/zhtyyx/ioe/main/.env.template -o .env
openssl rand -hex 32
```

Set `SECRET_KEY` in `.env` to the generated value. Set `ALLOWED_HOSTS` to your server IP or domain names, separated by commas without schemes or ports. Keep `localhost,127.0.0.1` if you also need local access. Keep `.env` private and do not overwrite it during updates.

Example:

```dotenv
SECRET_KEY=replace-with-the-generated-random-value
ALLOWED_HOSTS=localhost,127.0.0.1,your-server-ip
IOE_PORT=8000
```

## 2. Pull and start

```bash
docker compose pull
docker compose up -d --wait
docker compose exec web python manage.py createsuperuser
```

Open `http://your-server-ip:8000/` and sign in. A new deployment starts with an empty database. The container runs database migrations and collects static files at startup. Create the administrator account once, using the command above.

The deployment runs two services: `web` hosts Django / Gunicorn, while `nginx` serves the application, static assets, and uploaded images. This configuration fixes `DEBUG=False` and does not bind-mount source code. Configure a domain and HTTPS at the entry point before exposing the service publicly.

To change the port, set `IOE_PORT=8080` in `.env`. Set `IOE_BIND_ADDRESS=127.0.0.1` if only a reverse proxy on the same host should reach the service.

## 3. Update

Back up the database and uploaded files first:

```bash
docker compose pull
docker compose up -d --force-recreate --wait
docker compose logs --tail=100 web
```

Updates reuse the data volumes and run any new database migrations. Keep the deployment directory and Compose project name unchanged so the same volumes are used. `--force-recreate` refreshes both the application and proxy containers.

### Image tags

| Tag | Meaning |
| --- | --- |
| `latest` | The most recent tested and published build from `main` |
| `sha-<full commit SHA>` | A build tied to a specific source commit |
| `1.2.3` / `1.2` | Created when a version tag such as `v1.2.3` is pushed; only published tags are available |

Set `IOE_IMAGE=ghcr.io/zhtyyx/ioe:sha-<full commit SHA>` in `.env` to pin a version. You can also pin an image digest with `@sha256:...`. An older image may not support an upgraded database; a rollback may require the matching database backup.

## Persistent data

| Named volume | Container path and contents |
| --- | --- |
| `db_volume` | `/app/db`: SQLite database |
| `media_volume` | `/app/media`: uploaded images |
| `backups_volume` | `/app/backups`: backups created within IOE |
| `logs_volume` | `/app/logs`: application logs |
| `static_volume` | `/app/staticfiles`: static assets collected at startup |

```bash
docker compose logs -f web
docker compose exec web python manage.py check
docker compose down
```

`down` retains named volumes. `down -v` deletes them and their data; do not use it to update the application.

When moving an existing source deployment to the image, back it up and confirm its Compose project and volume names first. This configuration retains the logical names `db_volume`, `media_volume`, and `static_volume`. Existing host directories such as `logs/` and `backups/` are not automatically copied into the new volumes. Test migration on a copy before using the live database.

## GitHub Actions publishing

[Publish container image](.github/workflows/publish-image.yml) runs on pushes to `main`, pushes of `v*` tags, and manual dispatch:

1. Build a test image and run the Django tests.
2. Verify fresh startup, login, static assets, uploads, and persistence after container recreation.
3. Publish AMD64 / ARM64 images to GHCR using the repository's `GITHUB_TOKEN`.

Pull requests only build and test; they do not log in to GHCR or publish. No Docker Hub account or personal access token is needed for the workflow.

**First publication:** new GHCR packages are private by default. The maintainer must set the package to Public in [IOE package settings](https://github.com/users/zhtyyx/packages/container/ioe/settings) before anonymous pulls work. Confirm a successful Actions run before using an image. For `denied`, check visibility; for `manifest unknown`, check that the tag has been published. [GitHub documentation](https://docs.github.com/en/packages/working-with-a-github-packages-registry/working-with-the-container-registry)

## Build from source for development

When editing source code, build an image locally and use the same deployment configuration:

```bash
git clone https://github.com/zhtyyx/ioe.git
cd ioe
cp .env.template .env
# Set SECRET_KEY and ALLOWED_HOSTS as described above, then run:
docker build -t ioe:local .
IOE_IMAGE=ioe:local docker compose -f docker-compose.prod.yml up -d --wait
docker compose -f docker-compose.prod.yml exec web python manage.py createsuperuser
```

This packages your changes in the image without bind-mounting the checkout. To test the image deployment locally:

```bash
docker build -t ioe:local .
sh scripts/test-container.sh ioe:local
```

The smoke script uses a unique temporary project and volumes, and cleans up only the containers and volumes it created.
