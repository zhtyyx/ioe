#!/bin/sh
# Smoke-test a fresh image in disposable, uniquely named Compose volumes.
set -eu
cd "$(dirname "$0")/.."
export IOE_IMAGE="${1:-ioe:ci}"
export SECRET_KEY="ioe-container-smoke-test-not-for-production"
export ALLOWED_HOSTS="localhost,127.0.0.1"
export IOE_BIND_ADDRESS="127.0.0.1"
export IOE_PORT=0
project="ioe-smoke-$(date +%s)-$$"
compose() { docker compose -p "$project" -f docker-compose.prod.yml "$@"; }
cleanup() {
    status=$?
    if [ "$status" -ne 0 ]; then compose logs --no-color || true; fi
    # Only volumes belonging to this test's unique project are removed.
    compose down --volumes --remove-orphans >/dev/null 2>&1 || true
    exit "$status"
}
trap cleanup EXIT
compose up -d --wait --wait-timeout 180
address=$(compose port nginx 80)
curl --fail --silent --show-error --retry 10 --retry-delay 1 --retry-connrefused "http://$address/accounts/login/" >/dev/null
curl --fail --silent --show-error --retry 10 --retry-delay 1 --retry-connrefused "http://$address/static/inventory/images/logo.svg" | grep -q 'logoGradient'
compose exec -T web python manage.py shell -c "from django.contrib.auth.models import User; from pathlib import Path; User.objects.create_user('container-smoke'); Path('/app/media/container-smoke.txt').write_text('persistent-media'); Path('/app/backups/container-smoke.txt').write_text('persistent-backup')"
curl --fail --silent --show-error --retry 10 --retry-delay 1 --retry-connrefused "http://$address/media/container-smoke.txt" | grep -q 'persistent-media'
# Recreate both services so the proxy resolves the current web container address.
compose up -d --force-recreate --wait --wait-timeout 180
address=$(compose port nginx 80)
compose exec -T web python manage.py shell -c "from django.contrib.auth.models import User; from pathlib import Path; assert User.objects.filter(username='container-smoke').count() == 1; assert Path('/app/media/container-smoke.txt').read_text() == 'persistent-media'; assert Path('/app/backups/container-smoke.txt').read_text() == 'persistent-backup'"
curl --fail --silent --show-error --retry 10 --retry-delay 1 --retry-connrefused "http://$address/accounts/login/" >/dev/null
curl --fail --silent --show-error --retry 10 --retry-delay 1 --retry-connrefused "http://$address/media/container-smoke.txt" | grep -q 'persistent-media'
printf '%s\n' 'Container smoke passed: startup, login, static/media, and persisted data after recreation.'
