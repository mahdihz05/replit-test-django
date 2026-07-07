# Final VPS Production Artifacts — محتوایار

## 1. Verify Previous Assumptions

| Statement | Verdict | Notes |
|---|---|---|
| Django backend is the only backend. | ✅ Correct | All API routes are in `backend/config/urls.py` and workspace sub-urls. |
| `artifacts/api-server` is unused. | ✅ Correct | It is a Replit Node/Express template. The real API is Django. |
| React frontend builds to `artifacts/frontend/dist/public`. | ✅ Correct | `vite.config.ts` line 58: `outDir: path.resolve(..., "dist/public")`. |
| Node.js is only required for building the frontend. | ✅ Correct | Runtime is static files served by nginx. |
| PostgreSQL is the only database. | ✅ Correct | `settings.py` line 75 uses `dj_database_url`; fallback is SQLite for dev only. |
| Gunicorn should be used (not Daphne/Uvicorn). | ✅ Correct | Only `config/wsgi.py` exists. No `asgi.py`. |
| APScheduler runs inside Django. | ✅ Correct | `backend/config/apps.py` `ready()` calls `start_scheduler()`. |
| Gunicorn must use one worker. | ✅ Correct for safety | More than one worker requires `--preload` to avoid duplicate schedulers. |
| `--preload` is required. | ⚠️ Strongly recommended | With `--preload` one scheduler starts; without it, the PID lock file is the only guard and is fragile. |
| Redis is not used. | ✅ Correct | No Redis client or config anywhere. |
| Celery is not used. | ✅ Correct | No Celery imports or config anywhere. |
| No background worker is required. | ✅ Correct | Scheduler is in-process; publishers are synchronous. |
| Nginx serves frontend/static/media. | ✅ Correct | Required for production. |

---

## 2. Environment Variables

### Backend

| Variable | Required? | Default | Used in | Purpose |
|---|---|---|---|---|
| `SECRET_KEY` | Yes* | — | `backend/config/settings.py:8` | Django signing, sessions, tokens. |
| `SESSION_SECRET` | Yes* | — | `backend/config/settings.py:8` | Replit alias for `SECRET_KEY`. Either works. |
| `DEBUG` | No | `False` | `backend/config/settings.py:13` | Debug mode. |
| `ALLOWED_HOSTS` | Yes in prod | `*` | `backend/config/settings.py:15` | Allowed HTTP Host headers. |
| `DATABASE_URL` | Yes | SQLite3 | `backend/config/settings.py:75` | PostgreSQL connection string. |
| `CORS_ALLOWED_ORIGINS` | Yes in prod | `''` (dev fallback: all) | `backend/config/settings.py:126` | Allowed CORS origins. |
| `OPENAI_API_KEY` | Yes (for AI) | `''` | `backend/config/settings.py:135` | GPT-4o / DALL-E 3. |
| `TELEGRAM_BOT_TOKEN` | Yes (for Telegram) | `''` | `backend/config/settings.py:136` | Telegram Bot API. |
| `BALE_BOT_TOKEN` | Yes (for Bale) | `''` | `backend/config/settings.py:137` | Bale Bot API. |
| `SMS_API_KEY` | Yes (for real SMS) | `''` | `backend/config/settings.py:138` | OTP SMS provider. |
| `SMS_SENDER` | Yes (for real SMS) | `''` | `backend/config/settings.py:139` | SMS sender number. |
| `MEDIA_ROOT` | No | `backend/media` | `backend/config/settings.py:101` | Filesystem path for uploaded media. |
| `SHARED_TOKEN_ENCRYPTION_KEY` | No | derives from `SECRET_KEY` | `backend/channels_app/crypto.py:17` | Fernet key for LinkedIn token encryption. |
| `LINKEDIN_TOKEN_ENCRYPTION_KEY` | No | fallback to `SHARED_TOKEN_ENCRYPTION_KEY` | `backend/channels_app/crypto.py:18` | Alias for LinkedIn encryption key. |
| `RUN_MAIN` | No | not set | `backend/config/apps.py:14` | Internal Django dev autoreloader signal. Do not set manually. |
| `DJANGO_SETTINGS_MODULE` | No | `config.settings` | `backend/config/wsgi.py:4`, `backend/manage.py:7` | Set automatically in WSGI/systemd. |

*At least one of `SECRET_KEY` or `SESSION_SECRET` is required.

### Frontend / Build

| Variable | Required? | Default | Used in | Purpose |
|---|---|---|---|---|
| `PORT` | Yes (build) | — | `artifacts/frontend/vite.config.ts:7` | Vite server/preview port. Required at config load time even for static build. |
| `BASE_PATH` | Yes (build) | — | `artifacts/frontend/vite.config.ts:21` | Frontend base URL. Use `/` in production. |
| `NODE_ENV` | No | — | `artifacts/frontend/vite.config.ts:35` | Controls Replit-only plugins. |
| `REPL_ID` | No | — | `artifacts/frontend/vite.config.ts:36` | Replit-only plugin flag. Ignored on VPS. |

### Unused Node Drizzle (api-server / lib/db)

| Variable | Required? | Used in | Purpose |
|---|---|---|---|
| `DATABASE_URL` | Yes for unused Node stack | `lib/db/src/index.ts:7`, `lib/db/drizzle.config.ts:4` | Used by the unused Express api-server. Not needed for Django production. |

---

## 3. Python Dependencies

Use **`pyproject.toml`** in production.

Why:
- `pyproject.toml` pins newer versions: Django 5.2.15, DRF 3.17.1, OpenAI 2.44.0, etc.
- `backend/requirements.txt` is older: Django 4.2, DRF 3.14, OpenAI 1.0.
- They are **not synchronized**.

Can `requirements.txt` be deleted? **Yes**, after confirming `pyproject.toml` covers everything. For safety, keep it until production is verified, then remove it to avoid confusion.

Command to use:

```bash
cd /var/www/mohtavayar/backend
source ../venv/bin/activate
pip install -e .
```

Or without editable mode:

```bash
pip install .
```

---

## 4. Production Folder Layout

```
/var/www/mohtavayar/
├── backend/                  # Django project (from repo)
│   ├── config/
│   ├── media/                # persistent uploads (create + chown)
│   ├── staticfiles/          # collectstatic output
│   └── venv/                 # Python virtualenv (optional: can be at /var/www/venv)
├── artifacts/frontend/       # from repo (only needed for build)
│   └── dist/public/          # built SPA files
├── lib/                      # from repo (workspace packages needed for build)
├── pnpm-workspace.yaml       # from repo
├── pnpm-lock.yaml            # from repo
├── pyproject.toml            # from repo
├── package.json              # from repo
├── .env                      # production environment variables
├── logs/                     # gunicorn/nginx logs (optional)
└── venv/                     # Python virtualenv
```

### Ownership

| Path | Owner | Group | Reason |
|---|---|---|---|
| `/var/www/mohtavayar` | `deploy` | `www-data` | Deploy user owns code; nginx group can read. |
| `/var/www/mohtavayar/backend/media` | `deploy` | `www-data` | Gunicorn (running as `www-data`) needs write access. |
| `/var/www/mohtavayar/backend/staticfiles` | `deploy` | `www-data` | Nginx reads static files. |
| `/var/www/mohtavayar/artifacts/frontend/dist/public` | `deploy` | `www-data` | Nginx reads SPA. |
| `/var/www/mohtavayar/venv` | `deploy` | `deploy` | Python environment. |

---

## 5. Systemd Service

File: `/etc/systemd/system/mohtavayar.service`

```ini
[Unit]
Description=Mohtavayar Django Gunicorn
After=network.target postgresql.service

[Service]
Type=notify
User=www-data
Group=www-data
WorkingDirectory=/var/www/mohtavayar/backend
EnvironmentFile=/var/www/mohtavayar/.env
Environment="DJANGO_SETTINGS_MODULE=config.settings"
Environment="PATH=/var/www/mohtavayar/venv/bin:/usr/local/bin:/usr/bin"
ExecStart=/var/www/mohtavayar/venv/bin/gunicorn \
    config.wsgi:application \
    --bind unix:/run/mohtavayar/gunicorn.sock \
    --workers 1 \
    --preload \
    --timeout 120 \
    --access-logfile - \
    --error-logfile - \
    --capture-output \
    --enable-stdio-inheritance
ExecReload=/bin/kill -s HUP $MAINPID
Restart=on-failure
RestartSec=5
KillMode=mixed

[Install]
WantedBy=multi-user.target
```

Socket directory creation:

```bash
sudo mkdir -p /run/mohtavayar
sudo chown www-data:www-data /run/mohtavayar
```

Use a tmpfiles.d rule to recreate on boot:

File: `/etc/tmpfiles.d/mohtavayar.conf`

```
D /run/mohtavayar 0755 www-data www-data -
```

---

## 6. Nginx Configuration

File: `/etc/nginx/sites-available/mohtavayar`

```nginx
upstream mohtavayar_app {
    server unix:/run/mohtavayar/gunicorn.sock fail_timeout=0;
}

server {
    listen 80;
    server_name yourdomain.com www.yourdomain.com;
    return 301 https://$server_name$request_uri;
}

server {
    listen 443 ssl http2;
    server_name yourdomain.com www.yourdomain.com;

    ssl_certificate /etc/letsencrypt/live/yourdomain.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/yourdomain.com/privkey.pem;
    ssl_trusted_certificate /etc/letsencrypt/live/yourdomain.com/chain.pem;

    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_ciphers HIGH:!aNULL:!MD5;
    ssl_prefer_server_ciphers on;
    ssl_session_cache shared:SSL:10m;
    ssl_session_timeout 10m;

    root /var/www/mohtavayar/artifacts/frontend/dist/public;
    index index.html;

    client_max_body_size 100M;

    gzip on;
    gzip_vary on;
    gzip_proxied any;
    gzip_comp_level 6;
    gzip_types text/plain text/css text/xml application/json application/javascript application/rss+xml application/atom+xml image/svg+xml;

    add_header X-Frame-Options "DENY" always;
    add_header X-Content-Type-Options "nosniff" always;
    add_header Referrer-Policy "strict-origin-when-cross-origin" always;
    add_header Permissions-Policy "geolocation=(), microphone=(), camera=()" always;

    location / {
        try_files $uri $uri/ /index.html;
        add_header Cache-Control "no-cache";
    }

    location /api/ {
        proxy_pass http://mohtavayar_app;
        proxy_set_header Host $http_host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_set_header X-Forwarded-Host $http_host;
        proxy_redirect off;
        proxy_read_timeout 120s;
        proxy_connect_timeout 120s;
        proxy_send_timeout 120s;
    }

    location /admin/ {
        proxy_pass http://mohtavayar_app;
        proxy_set_header Host $http_host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_set_header X-Forwarded-Host $http_host;
        proxy_read_timeout 120s;
    }

    location /static/ {
        alias /var/www/mohtavayar/backend/staticfiles/;
        expires 30d;
        add_header Cache-Control "public, immutable";
        access_log off;
    }

    location /media/ {
        alias /var/www/mohtavayar/backend/media/;
        expires 30d;
        add_header Cache-Control "public, immutable";
        access_log off;
    }
}
```

---

## 7. APScheduler

**Exact startup path:**

```
backend/config/apps.py:8
    └── backend/config/apps.py:18
        └── backend/publishing/scheduler.py:340
            └── backend/publishing/scheduler.py:369
```

**Code path:**

```python
# backend/config/apps.py
class ConfigAppConfig(AppConfig):
    def ready(self):
        import os
        run_main = os.environ.get('RUN_MAIN')
        if run_main is not None and run_main != 'true':
            return
        try:
            from publishing.scheduler import start_scheduler
            start_scheduler()
        except Exception as e:
            print(f'[Scheduler] Could not start: {e}')
```

```python
# backend/publishing/scheduler.py:340
def start_scheduler():
    if not _acquire_scheduler_lock():  # line 344
        return None
    # ... builds BackgroundScheduler and adds jobs
    scheduler.start()
```

**Lock mechanism:**

```python
# backend/publishing/scheduler.py:318-337
LOCK_FILE_PATH = '/tmp/mohtavayar_scheduler.lock'

def _acquire_scheduler_lock():
    try:
        if os.path.exists(LOCK_FILE_PATH):
            try:
                with open(LOCK_FILE_PATH, 'r') as f:
                    old_pid = int(f.read().strip())
                os.kill(old_pid, 0)  # check if PID is alive
                return False
            except (ValueError, ProcessLookupError, FileNotFoundError):
                pass  # stale lock
            except PermissionError:
                return False
        with open(LOCK_FILE_PATH, 'w') as f:
            f.write(str(os.getpid()))
        return True
    except Exception:
        return False
```

Only one scheduler instance exists because the lock file stores the PID of the running scheduler. If the file exists and the PID is alive, no new scheduler starts. With `--preload` and `--workers 1`, there is only one master process, so the lock is redundant but still active.

**Is one Gunicorn worker mandatory?** Not strictly mandatory, but it is the **safest** configuration. Without `--preload`, each worker tries to start its own scheduler; only the PID lock prevents duplicates, and that lock can fail across machines or after unclean shutdowns.

---

## 8. Security

Add these to `backend/config/settings.py` (or read them from env) for production:

```python
DEBUG = False
ALLOWED_HOSTS = ["yourdomain.com", "www.yourdomain.com"]
CSRF_TRUSTED_ORIGINS = ["https://yourdomain.com"]
CORS_ALLOWED_ORIGINS = ["https://yourdomain.com"]

SESSION_COOKIE_SECURE = True
CSRF_COOKIE_SECURE = True
SECURE_SSL_REDIRECT = True
SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")

SECURE_HSTS_SECONDS = 31536000
SECURE_HSTS_INCLUDE_SUBDOMAINS = True
SECURE_HSTS_PRELOAD = True
SECURE_CONTENT_TYPE_NOSNIFF = True
SECURE_BROWSER_XSS_FILTER = True
X_FRAME_OPTIONS = "DENY"
```

Current project lacks:
- `CSRF_TRUSTED_ORIGINS`
- `SESSION_COOKIE_SECURE`
- `CSRF_COOKIE_SECURE`
- `SECURE_SSL_REDIRECT`
- `SECURE_PROXY_SSL_HEADER`
- `SECURE_HSTS_*`

You should add them before production.

---

## 9. Deploy Commands

Run on a clean Ubuntu 24.04 VPS as `root` (or use `sudo`):

```bash
# 1. Update and install system packages
apt update && apt upgrade -y
apt install -y \
    python3.11 python3.11-venv python3-pip python3.11-dev \
    postgresql postgresql-contrib \
    nginx certbot python3-certbot-nginx \
    git curl ca-certificates

# 2. Install Node.js 20 and pnpm
curl -fsSL https://deb.nodesource.com/setup_20.x | bash -
apt install -y nodejs
corepack enable
corepack prepare pnpm@latest --activate

# 3. Create project directory and deploy user
mkdir -p /var/www
useradd -r -m -d /var/www/mohtavayar -s /bin/bash deploy || true
usermod -aG www-data deploy

# 4. Clone repository (replace with your actual repo)
cd /var/www
git clone https://github.com/yourusername/yourrepo.git mohtavayar
chown -R deploy:www-data /var/www/mohtavayar

# 5. Create Python virtualenv
su - deploy -c "python3.11 -m venv /var/www/mohtavayar/venv"

# 6. Install Python dependencies
su - deploy -c "cd /var/www/mohtavayar/backend && source /var/www/mohtavayar/venv/bin/activate && pip install -e ."

# 7. Install Node dependencies
su - deploy -c "cd /var/www/mohtavayar && pnpm install --frozen-lockfile"

# 8. Create PostgreSQL database and user
su - postgres -c "psql -c \"CREATE USER mohtavayar WITH PASSWORD 'strongpassword';\""
su - postgres -c "psql -c \"CREATE DATABASE mohtavayar OWNER mohtavayar;\""
su - postgres -c "psql -c \"GRANT ALL PRIVILEGES ON DATABASE mohtavayar TO mohtavayar;\""

# 9. Create environment file
nano /var/www/mohtavayar/.env
# (Paste the .env content from section 6, set DATABASE_URL, SECRET_KEY, etc.)
chown deploy:www-data /var/www/mohtavayar/.env
chmod 640 /var/www/mohtavayar/.env

# 10. Run migrations and create superuser
su - deploy -c "cd /var/www/mohtavayar/backend && source /var/www/mohtavayar/venv/bin/activate && \
    export $(cat /var/www/mohtavayar/.env | xargs) && \
    python manage.py migrate && \
    python manage.py collectstatic --noinput && \
    python manage.py createsuperuser"

# 11. Build frontend
su - deploy -c "cd /var/www/mohtavayar && \
    export PORT=5173 BASE_PATH=/ && \
    pnpm --filter @workspace/frontend run build"

# 12. Ensure media directory exists and is writable
mkdir -p /var/www/mohtavayar/backend/media
chown -R deploy:www-data /var/www/mohtavayar/backend/media
chmod 775 /var/www/mohtavayar/backend/media

# 13. Create systemd socket directory and tmpfiles rule
mkdir -p /run/mohtavayar
chown www-data:www-data /run/mohtavayar
echo 'D /run/mohtavayar 0755 www-data www-data -' > /etc/tmpfiles.d/mohtavayar.conf

# 14. Create systemd service
cp /var/www/mohtavayar/VPS-DEPLOYMENT-ARTIFACTS.md /etc/systemd/system/mohtavayar.service
# ^ Replace with the service file from section 5.
nano /etc/systemd/system/mohtavayar.service

systemctl daemon-reload
systemctl enable mohtavayar.service

# 15. Configure nginx
cp /var/www/mohtavayar/VPS-DEPLOYMENT-ARTIFACTS.md /etc/nginx/sites-available/mohtavayar
# ^ Replace with the nginx config from section 6.
nano /etc/nginx/sites-available/mohtavayar

rm -f /etc/nginx/sites-enabled/default
ln -s /etc/nginx/sites-available/mohtavayar /etc/nginx/sites-enabled/mohtavayar
nginx -t
systemctl restart nginx

# 16. Obtain SSL certificate
certbot --nginx -d yourdomain.com -d www.yourdomain.com --non-interactive --agree-tos --email your-email@example.com

# 17. Start the application
systemctl start mohtavayar.service

# 18. Verify
systemctl status mohtavayar.service
curl -s https://yourdomain.com/api/auth/me/ | head -c 200
```

---

## 10. Verification Checklist

| Step | Command | Expected Output |
|---|---|---|
| PostgreSQL running | `sudo systemctl status postgresql` | `active (running)` |
| Database exists | `sudo -u postgres psql -l \| grep mohtavayar` | `mohtavayar` |
| Migrations applied | `cd /var/www/mohtavayar/backend && venv/bin/python manage.py showmigrations` | All `[X]` |
| Static files collected | `ls -la /var/www/mohtavayar/backend/staticfiles/admin/` | Files exist |
| Media directory writable | `sudo -u www-data touch /var/www/mohtavayar/backend/media/test` | No permission error |
| Frontend build exists | `ls /var/www/mohtavayar/artifacts/frontend/dist/public/index.html` | File exists |
| Gunicorn socket | `ls -la /run/mohtavayar/gunicorn.sock` | `www-data www-data` |
| Gunicorn running | `sudo systemctl status mohtavayar` | `active (running)` |
| API reachable | `curl -s https://yourdomain.com/api/auth/me/` | `401 Unauthorized` or login JSON |
| Admin reachable | `curl -s https://yourdomain.com/admin/login/` | HTML login page |
| Static served by nginx | `curl -s https://yourdomain.com/static/admin/css/base.css` | CSS content |
| HTTPS valid | `curl -I https://yourdomain.com` | HTTP/2 200, valid cert |

---

## 11. Hidden Production Issues

1. **Hardcoded Telegram bot token** in `.replit` (`TELEGRAM_BOT_TOKEN = ...`). Remove and rotate immediately.
2. **Outdated `requirements.txt`**. Use `pyproject.toml` instead.
3. **APScheduler lock file is in `/tmp`**. Volatile but PID-aware; with `--preload` it is safe.
4. **Vite build requires `PORT` and `BASE_PATH`** even though the output is static. Missing them causes build failure.
5. **`ALLOWED_HOSTS` defaults to `['*']`** if unset — insecure for production.
6. **`CORS_ALLOWED_ORIGINS` defaults to allow all origins** if unset — insecure for production.
7. **`CSRF_TRUSTED_ORIGINS` is missing** in `settings.py`. Needed for Django admin over HTTPS.
8. **Cookie security settings missing** (`SESSION_COOKIE_SECURE`, `CSRF_COOKIE_SECURE`, etc.).
9. **Unused Node packages installed**. `artifacts/api-server`, `lib/db`, `scripts` are part of the pnpm workspace and will be installed, increasing build time and surface area.
10. **`scripts/post-merge.sh` runs `pnpm --filter db push`**, which is for the unused Node drizzle stack. This hook is irrelevant on VPS.
11. **No separate health-check endpoint**. The only verification is hitting `/api/auth/me/` and checking for 401.
12. **`config/urls.py` uses `static()` for media**. This is fine for development but must be served by nginx in production.
13. **No explicit cleanup of `/tmp/mohtavayar_scheduler.lock` on shutdown**. On unclean shutdown the lock may become stale but is recovered by the PID check.
14. **LinkedIn token encryption derives from `SECRET_KEY` if no env var is set**. This works but is less secure than a dedicated `SHARED_TOKEN_ENCRYPTION_KEY`.
15. **Django development server warning**. The workflow uses `runserver`; production must use Gunicorn.

---

## 12. Final Confidence Report

| Item | Confidence | Reason |
|---|---|---|
| Backend | 100% | Verified Django WSGI, no ASGI, exact Gunicorn command known. |
| Frontend | 100% | Verified Vite build output, static SPA, Node not needed at runtime. |
| Database | 100% | PostgreSQL via `dj_database_url`; no exotic extensions. |
| Scheduler | 95% | Lock file in `/tmp` is slightly fragile, but `--preload --workers 1` eliminates the risk. |
| Static | 100% | `STATIC_ROOT` and `collectstatic` are standard. |
| Media | 100% | `MEDIA_ROOT` configurable; nginx can serve. |
| Nginx | 100% | Standard reverse proxy + static/media config. |
| Gunicorn | 100% | Exact command, worker count, and timeout known. |
| Systemd | 100% | Service file includes all requested fields. |
| Environment Variables | 100% | All `os.environ` and `process.env` references found. |
| Security | 90% | Current `settings.py` lacks some production security settings; they must be added. |
| Deployment Procedure | 95% | Commands are copy-paste ready; domain and repo placeholders must be replaced. |

The only items below 95% are:
- **Security**: because `settings.py` does not currently contain `CSRF_TRUSTED_ORIGINS`, cookie security, HSTS, etc. They must be added.
- **Deployment Procedure**: placeholders (`yourdomain.com`, git repo URL) must be filled in.
- **Scheduler**: 95% because the lock file mechanism relies on `/tmp` and process PID, but `--preload` makes it effectively 100% safe.
