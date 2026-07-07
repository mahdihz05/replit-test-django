# VPS Deployment Guide — محتوایار

Target: clean Ubuntu 24.04 VPS. This guide is specific to THIS project, not generic.

---

## 1. Runtime Architecture

```
Browser
   ↓ HTTPS
Nginx (port 80 / 443)
   ├── /  ────────────→  React static files (dist/public)
   ├── /api/  ────────→  Gunicorn → Django (port 8000)
   ├── /admin/  ──────→  Gunicorn → Django (port 8000)
   ├── /static/  ─────→  Nginx file system (backend/staticfiles)
   └── /media/  ──────→  Nginx file system (backend/media)
                              ↓
                        PostgreSQL (port 5432)
```

**What handles what:**
- **Frontend:** SPA React app. All client-side routing. Calls `/api/*` from the browser.
- **Nginx:** reverse-proxies `/api/` and `/admin/` to Django; serves static files and uploaded media directly.
- **Django:** WSGI app on port 8000. Serves API, admin, and media fallback via Django's `static()` helper in development.
- **APScheduler:** runs inside the Django process, handles bot polling and the publish queue.
- **PostgreSQL:** single database for everything.

---

## 2. Production Services

| Name | Required? | Start command | Port | Language | Runs continuously? | systemd service name |
|------|-----------|---------------|------|----------|-------------------|----------------------|
| PostgreSQL | Yes | `sudo systemctl start postgresql` | 5432 | — | Yes | `postgresql` |
| Django API (Gunicorn) | Yes | `cd /var/www/backend && /var/www/backend/venv/bin/gunicorn config.wsgi:application --bind 0.0.0.0:8000 --workers 1 --preload --timeout 120` | 8000 | Python | Yes | `mohtavayar-gunicorn` |
| APScheduler | Yes | Starts automatically inside Django process | — | Python | Yes | N/A (part of Gunicorn) |
| Nginx | Yes | `sudo systemctl start nginx` | 80 / 443 | — | Yes | `nginx` |
| React frontend | Yes (static files) | Build once: `PORT=5173 BASE_PATH=/ pnpm --filter @workspace/frontend run build` | — | Node (build only) | No | N/A |

**NOT needed in production:**
- `artifacts/api-server` — Node.js Express boilerplate; this project uses Django, not Express.
- `artifacts/mockup-sandbox` — Canvas / component preview tool; development only.
- `.replit`, `.replit-artifact/*`, `.local`, `.agents`, `.pythonlibs`, `replit.md` — Replit-only.
- `scripts/post-merge.sh` — Replit post-merge hook.
- `attached_assets`, `screenshots` — attached assets, not runtime code.

---

## 3. Backend

- **WSGI:** `config.wsgi.application`
- **ASGI:** not used; no `asgi.py` exists.
- **Production server:** Gunicorn (WSGI).
- **Recommended workers:** `1` with `--preload`. Because APScheduler starts inside the Django process, using one worker prevents multiple schedulers from starting.
- **Timeout:** 120 seconds (OpenAI/DALL-E and WordPress media uploads can be slow).
- **Working directory:** `/var/www/backend` (or wherever you clone `backend/`).
- **Virtual environment:** `/var/www/backend/venv` (recommended).

**Exact production command:**

```bash
cd /var/www/backend
source venv/bin/activate
gunicorn config.wsgi:application \
  --bind 0.0.0.0:8000 \
  --workers 1 \
  --preload \
  --timeout 120 \
  --access-logfile - \
  --error-logfile -
```

---

## 4. Scheduler

- **File:** `backend/publishing/scheduler.py`
- **Startup:** `backend/config/apps.py` → `ConfigAppConfig.ready()` → `start_scheduler()`.
- **When it starts:** Every time the Django process starts. It uses `_acquire_scheduler_lock()` to write its PID to `/tmp/mohtavayar_scheduler.lock` and only one scheduler runs across the whole machine.
- **Multiple Gunicorn workers:** If you run `--workers 4`, each worker will try to start the scheduler. The lock file prevents most duplicates, but it is fragile and the lock file can become stale if a worker dies.
- **Duplicate jobs:** Possible if the lock file is stale or if you scale across multiple servers. The lock is PID-based and local to one machine.
- **Safest production configuration:** Run **a single Gunicorn worker with `--preload`**. This guarantees exactly one scheduler and one lock holder. For a busy site, use a dedicated scheduler process (separate from Gunicorn) instead of the built-in `ready()` startup, but that requires code changes.

**Scheduled jobs:**
- `poll_telegram` — every 8 seconds
- `poll_bale` — every 8 seconds
- `process_publish_queue` — every 1 minute
- `process_retries` — every 5 minutes
- `expire_otp_codes` — every 1 hour
- `expire_verifications` — every 1 hour
- `refresh_all_linkedin_tokens` — every 24 hours

---

## 5. Database

- **Engine:** PostgreSQL (via `dj_database_url` + `psycopg2-binary`).
- **Required extensions:** None special; standard PG is enough.
- **Migration command:** `cd /var/www/backend && python manage.py migrate`
- **Seed command:** No dedicated seed command exists. Create a superuser with `python manage.py createsuperuser` if needed.
- **Backup recommendations:** Use `pg_dump` nightly. Example:

```bash
pg_dump "$DATABASE_URL" > /var/backups/mohtavayar_$(date +%Y%m%d).sql
```

---

## 6. Environment Variables

```env
# Django core
SECRET_KEY=change-me-to-a-50-char-random-string
DEBUG=False
ALLOWED_HOSTS=yourdomain.com,www.yourdomain.com
CORS_ALLOWED_ORIGINS=https://yourdomain.com

# Database
DATABASE_URL=postgres://mohtavayar:strongpassword@localhost:5432/mohtavayar

# External APIs
OPENAI_API_KEY=sk-...
TELEGRAM_BOT_TOKEN=...
BALE_BOT_TOKEN=...
SMS_API_KEY=...
SMS_SENDER=...

# Static / Media (optional, defaults are sane)
STATIC_URL=/static/
STATIC_ROOT=/var/www/backend/staticfiles
MEDIA_URL=/media/
MEDIA_ROOT=/var/www/backend/media

# Frontend build (only needed during build, not runtime)
PORT=5173
BASE_PATH=/
```

| Variable | Purpose | Required? | Default | Module |
|----------|---------|-----------|---------|--------|
| `SECRET_KEY` | Django signing/encryption | Required | — | `config.settings` |
| `SESSION_SECRET` | Replit alias for SECRET_KEY | Optional | — | `config.settings` |
| `DEBUG` | Debug mode | Optional | `False` | `config.settings` |
| `ALLOWED_HOSTS` | Allowed host headers | Required in prod | `*` (dev) | `config.settings` |
| `CORS_ALLOWED_ORIGINS` | Allowed CORS origins | Optional | all (dev) | `config.settings` |
| `DATABASE_URL` | PostgreSQL connection | Required | SQLite3 (dev) | `config.settings` |
| `OPENAI_API_KEY` | GPT-4o / DALL-E | Required for AI | — | `ai_engine` |
| `TELEGRAM_BOT_TOKEN` | Telegram Bot API | Required for Telegram | — | `channels_app`, `publishing` |
| `BALE_BOT_TOKEN` | Bale Bot API | Required for Bale | — | `channels_app`, `publishing` |
| `SMS_API_KEY` | OTP SMS provider | Required for real SMS | — | `users` |
| `SMS_SENDER` | SMS sender number | Required for real SMS | — | `users` |
| `MEDIA_ROOT` | Uploaded files path | Optional | `backend/media` | `config.settings` |
| `MEDIA_URL` | URL prefix for uploads | Optional | `/media/` | `config.settings` |
| `PORT` | Vite dev/preview port | Required for build | — | `vite.config.ts` |
| `BASE_PATH` | Frontend base path | Required for build | — | `vite.config.ts` |
| `REPL_ID` | Replit-only plugin flag | Not needed | — | `vite.config.ts` |

---

## 7. Static Files

- `STATIC_URL = '/static/'`
- `STATIC_ROOT = BASE_DIR / 'staticfiles'` → `backend/staticfiles`
- Run `cd /var/www/backend && python manage.py collectstatic`
- Nginx serves `/static/` from `/var/www/backend/staticfiles/`

---

## 8. Media Files

- `MEDIA_URL = '/media/'`
- `MEDIA_ROOT` defaults to `BASE_DIR / 'media'` → `backend/media`
- Uploads go to `backend/media/publish_attachments/`
- This directory must be persistent and writable by the Gunicorn user.
- Nginx serves `/media/` directly from `backend/media/`.
- In development, Django also serves media via `config.urls` using `static()`. In production, Nginx should handle it.

---

## 9. Frontend

- **Build command:** `PORT=5173 BASE_PATH=/ pnpm --filter @workspace/frontend run build`
- **Output folder:** `artifacts/frontend/dist/public`
- **Node required after build?** No. Node is only needed to build the SPA.
- **Nginx-served folder:** `artifacts/frontend/dist/public`
- The SPA uses `API_BASE_URL = "/api"`, so all API calls are relative to the same domain.

---

## 10. Replit Dependencies

| Item | Why it exists | Can be removed? | Replacement on Ubuntu |
|------|---------------|-----------------|---------------------|
| `.replit` | Replit workflow/config | Yes | Replace with systemd + nginx configs |
| `.replit-artifact/` | Replit artifact metadata | Yes | Not needed |
| `.local/` | Replit agent skills | Yes | Not needed |
| `.agents/` | Agent memory | Yes | Not needed |
| `.pythonlibs/` | Replit-managed Python packages | Yes | Use your own venv |
| `replit.md` | Replit project notes | Yes | Keep as README if useful, otherwise delete |
| `artifacts/api-server/` | Replit template Node API | Yes | Not used; Django is the real API |
| `artifacts/mockup-sandbox/` | Canvas component preview | Yes | Development-only tool |
| `scripts/post-merge.sh` | Replit post-merge hook | Yes | Not needed on VPS |
| `pnpm-workspace.yaml` | Monorepo workspace config | **Keep** | Needed by pnpm to resolve `@workspace/*` packages |
| `attached_assets/` | Uploaded assets | Yes | Download anything you need, then remove |
| `screenshots/` | Screenshots | Yes | Not needed |

---

## 11. Folder Structure

**Required on production server:**
- `backend/` — Django code
- `artifacts/frontend/` — only for building the SPA
- `lib/` — workspace packages needed for the frontend build (`@workspace/*`)
- `pnpm-workspace.yaml` — pnpm monorepo definition
- `pnpm-lock.yaml` — reproducible Node install
- `pyproject.toml` — Python dependencies (source of truth, newer than `requirements.txt`)
- `package.json` — root workspace package

**Can be deleted on production:**
- `artifacts/api-server/`
- `artifacts/mockup-sandbox/`
- `.replit`, `.replit-artifact/`, `.local/`, `.agents/`, `.pythonlibs/`, `replit.md`
- `scripts/post-merge.sh` (or keep `scripts/` if pnpm workspace still references it, but script is not needed)
- `attached_assets/`, `screenshots/`

**Note:** `requirements.txt` exists but is older than `pyproject.toml`. Use `pyproject.toml` for Python dependency installation.

---

## 12. Reverse Proxy (Nginx)

```nginx
server {
    listen 80;
    server_name yourdomain.com www.yourdomain.com;

    # React SPA
    location / {
        root /var/www/artifacts/frontend/dist/public;
        try_files $uri $uri/ /index.html;
    }

    # Django API
    location /api/ {
        proxy_pass http://localhost:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_read_timeout 120s;
    }

    # Django Admin
    location /admin/ {
        proxy_pass http://localhost:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }

    # Static files
    location /static/ {
        alias /var/www/backend/staticfiles/;
        expires 30d;
    }

    # Media uploads
    location /media/ {
        alias /var/www/backend/media/;
        expires 30d;
    }
}
```

After SSL: use Certbot (`certbot --nginx`).

---

## 13. Security

- `DEBUG=False` — mandatory. `DEBUG=True` exposes stack traces and the secret key.
- `ALLOWED_HOSTS` — must be set to your real domain(s). Current dev default is `['*']`, which is unsafe in production.
- `SECRET_KEY` — must be a long random string, kept secret. The project also accepts `SESSION_SECRET` for Replit compatibility.
- `CORS_ALLOWED_ORIGINS` — set to your frontend domain(s). In dev it falls back to `CORS_ALLOW_ALL_ORIGINS=True`, which is unsafe in production.
- `CSRF_TRUSTED_ORIGINS` — **not currently configured** in `settings.py`. If you use the Django admin over HTTPS, add this setting (e.g. `CSRF_TRUSTED_ORIGINS = ['https://yourdomain.com']`).
- The Telegram bot token is currently hardcoded in `.replit` under `[userenv.shared]`. Move it to environment variables immediately and rotate the token.

---

## 14. Startup Order

1. Install Ubuntu packages: `sudo apt update && sudo apt install -y python3.11 python3.11-venv python3-pip nodejs npm postgresql nginx certbot python3-certbot-nginx`
2. Clone the repository to `/var/www/`
3. Create Python virtualenv: `python3.11 -m venv /var/www/backend/venv`
4. Install Python dependencies: `cd /var/www/backend && pip install .` (uses `pyproject.toml`)
5. Install pnpm and Node dependencies: `npm install -g pnpm && cd /var/www && pnpm install --frozen-lockfile`
6. Create `/var/www/.env` and set all required variables
7. Create PostgreSQL database and user
8. Run migrations: `cd /var/www/backend && python manage.py migrate`
9. Create superuser: `python manage.py createsuperuser`
10. Run collectstatic: `python manage.py collectstatic --noinput`
11. Build frontend: `cd /var/www && PORT=5173 BASE_PATH=/ pnpm --filter @workspace/frontend run build`
12. Ensure `/var/www/backend/media/` is writable by the Gunicorn user
13. Create systemd service for Gunicorn
14. Configure nginx
15. Enable SSL with Certbot
16. Start Gunicorn and nginx: `sudo systemctl start mohtavayar-gunicorn && sudo systemctl start nginx`

---

## 15. Deployment Pitfalls Specific to This Project

1. **Wrong backend:** Do not start the Node `artifacts/api-server`. The real API is the Django project in `backend/`.
2. **Scheduler duplicates:** APScheduler starts inside Django. Use `--workers 1 --preload` or a dedicated scheduler. Multiple workers without `--preload` can create scheduler race conditions despite the lock file.
3. **Vite build env vars:** The build command `pnpm run build` will fail without `PORT` and `BASE_PATH` because `vite.config.ts` reads them at config load time. Set them even though the output is static.
4. **Hardcoded Telegram token:** `.replit` contains `TELEGRAM_BOT_TOKEN`. Remove it from the file and rotate it before moving to VPS.
5. **Media permissions:** `backend/media/` must be writable by the Gunicorn process user, or uploads will fail.
6. **Static/media paths:** Nginx must serve `/static/` and `/media/`; do not let Django serve them in production. The `static()` helper in `config.urls` is for development.
7. **ALLOWED_HOSTS default:** `settings.py` defaults to `['*']` if `ALLOWED_HOSTS` is not set. This is insecure for production.
8. **CORS default:** Without `CORS_ALLOWED_ORIGINS`, the app allows all origins and disables credentials. Set it in production.
9. **Missing CSRF_TRUSTED_ORIGINS:** Admin login may fail over HTTPS until you add this setting.
10. **requirements.txt vs pyproject.toml:** `requirements.txt` is older. Use `pyproject.toml` for the production Python install.
11. **pnpm minimumReleaseAge:** `pnpm-workspace.yaml` has `minimumReleaseAge: 1440`. Do not disable it; it is a supply-chain defense. Use the existing `pnpm-lock.yaml` for reproducible installs.
12. **No ASGI:** There is no `asgi.py`, so use Gunicorn with WSGI, not Daphne.
13. **Time zone:** `TIME_ZONE = 'Asia/Tehran'` and `USE_TZ = True`. Ensure the VPS clock is correct (usually UTC, Django handles conversion).
