#!/usr/bin/env bash
set -Eeuo pipefail

APP_DIR="${APP_DIR:-/var/www/replit-test-django}"
VENV_DIR="${VENV_DIR:-$APP_DIR/venv}"
SERVICE_NAME="${SERVICE_NAME:-replit-test-django.service}"
DOMAIN="${DOMAIN:-n8n.abrit.io}"
BACKUP_ROOT="${BACKUP_ROOT:-/var/backups}"

cd "$APP_DIR"

test -f .env
test -x "$VENV_DIR/bin/python"

timestamp="$(date +%Y%m%d_%H%M%S)"
backup_dir="$BACKUP_ROOT/replit-test-django-$timestamp"
install -d -m 700 "$backup_dir"
install -m 600 .env "$backup_dir/app.env"
git rev-parse HEAD > "$backup_dir/git-commit.txt"

database_url="$(sed -n 's/^DATABASE_URL=//p' .env | tail -n 1)"
if [[ -n "$database_url" ]]; then
  pg_dump "$database_url" --format=custom --file="$backup_dir/database.dump"
  chmod 600 "$backup_dir/database.dump"
fi

git pull --ff-only origin main
"$VENV_DIR/bin/pip" install -r backend/requirements.txt
"$VENV_DIR/bin/pip" check
corepack pnpm install --frozen-lockfile
PORT=5173 BASE_PATH=/ NODE_ENV=production corepack pnpm --filter @workspace/frontend run build

"$VENV_DIR/bin/python" backend/manage.py check
"$VENV_DIR/bin/python" backend/manage.py migrate --noinput
"$VENV_DIR/bin/python" backend/manage.py collectstatic --noinput

media_root="$(sed -n 's/^MEDIA_ROOT=//p' .env | tail -n 1)"
media_root="${media_root:-$APP_DIR/backend/media}"
if [[ "$media_root" != /* ]]; then
  media_root="$APP_DIR/$media_root"
fi
sudo install -d -o www-data -g www-data -m 775 \
  "$media_root" "$media_root/content" "$media_root/content/images"

sudo chown root:www-data .env
sudo chmod 640 .env
sudo nginx -t
sudo systemctl restart "$SERVICE_NAME"
sudo systemctl reload nginx

curl --fail --silent --show-error \
  --retry 8 --retry-delay 2 --retry-all-errors --retry-connrefused \
  "https://$DOMAIN/api/auth/linkedin/callback/?error=access_denied&error_description=deployment-check" \
  >/dev/null

echo "Deployment completed: https://$DOMAIN"
echo "Backup created: $backup_dir"
