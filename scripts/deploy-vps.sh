#!/usr/bin/env bash
set -Eeuo pipefail

APP_DIR="${APP_DIR:-/var/www/mohtavayar}"
VENV_DIR="${VENV_DIR:-$APP_DIR/venv}"

cd "$APP_DIR"

git pull --ff-only
"$VENV_DIR/bin/pip" install .
"$VENV_DIR/bin/pip" install 'gunicorn>=23.0.0'
pnpm install --frozen-lockfile
PORT=5173 BASE_PATH=/ NODE_ENV=production pnpm --filter @workspace/frontend build

"$VENV_DIR/bin/python" backend/manage.py migrate --noinput
"$VENV_DIR/bin/python" backend/manage.py collectstatic --noinput
"$VENV_DIR/bin/python" backend/manage.py check --deploy

sudo systemctl restart mohtavayar
sudo nginx -t
sudo systemctl reload nginx

curl --fail --silent --show-error \
  "https://n8n.abrit.io/api/auth/linkedin/callback/?error=access_denied&error_description=deployment-check" \
  >/dev/null

echo "Deployment completed: https://n8n.abrit.io"
