# محتوایار — AI Content Automation Platform

یک پلتفرم SaaS چند فضای‌کاری برای مدیریت و انتشار محتوای هوش مصنوعی.

## Run & Operate

- `python /home/runner/workspace/backend/manage.py runserver 0.0.0.0:8000` — Django API (port 8000)
- `pnpm --filter @workspace/frontend run dev` — React Vite frontend (port 18130)
- `cd backend && python manage.py makemigrations` — create migrations
- `cd backend && python manage.py migrate` — apply migrations

## Stack

- **Backend:** Django 5 + DRF + PostgreSQL + JWT (djangorestframework-simplejwt) + APScheduler
- **Frontend:** React + Vite + Tailwind + shadcn/ui — Persian RTL (Vazirmatn font)
- **AI:** OpenAI GPT-4o (text + DALL-E 3 images)
- **Publishing:** Telegram Bot API + Bale Messenger API + Webhooks
- **DB:** PostgreSQL (managed by Replit)

## Where things live

- `backend/` — Django project root
- `backend/config/` — settings, urls, wsgi, exception handler
- `backend/users/` — OTP auth, JWT, user model
- `backend/workspaces/` — multi-tenant workspace + members
- `backend/content/` — content CRUD + versioning
- `backend/ai_engine/` — OpenAI integration (generate, rewrite, chat, titles, hashtags)
- `backend/channels_app/` — Telegram/Bale/Website channel management
- `backend/publishing/` — PublishJob queue + scheduler + retry logic
- `backend/wallet/` — credit wallet per workspace
- `backend/reports/` — aggregated analytics endpoints
- `artifacts/frontend/src/` — React pages (all RTL Persian)
- `artifacts/frontend/src/lib/api.ts` — fetch-based API client with JWT
- `artifacts/frontend/src/lib/auth.tsx` — auth context + workspace state

## Architecture decisions

- Django backend serves `/api/*` and `/media/*` via proxy; React frontend serves `/`
- JWT stored in `localStorage` as `access_token`; selected workspace in `selected_workspace_id`
- APScheduler runs in-process with Django (started in `config/apps.py ready()`)
- OTP codes are printed to console; SMS_API_KEY env var needed for real SMS
- Publishing retries: max 3 attempts, 5-min exponential backoff between retries
- Wallet costs configurable in `settings.WALLET_COSTS`

## Required env vars

| Variable | Purpose |
|---|---|
| `DATABASE_URL` | PostgreSQL connection (already set) |
| `OPENAI_API_KEY` | GPT-4o + DALL-E 3 |
| `TELEGRAM_BOT_TOKEN` | Telegram channel publishing |
| `BALE_BOT_TOKEN` | Bale messenger publishing |
| `SMS_API_KEY` | OTP SMS delivery |
| `SESSION_SECRET` | Django SECRET_KEY (already set) |

## Product

- **Authentication:** OTP phone login (no password)
- **Workspaces:** Multi-tenant, role-based (admin/manager)
- **Content:** Create, edit, version history, AI generation, schedule, publish
- **AI Engine:** Text generation, image generation, rewrite, title/hashtag suggestions, CTA, chat
- **Channels:** Connect Telegram/Bale channels via verification token flow
- **Publishing:** Async job queue with retry, per-channel status tracking
- **Wallet:** Per-workspace credit balance, transaction log, AI cost deduction
- **Reports:** Content stats, publish success rate, AI usage, error analysis

## User preferences

- UI must be Persian (Farsi) and RTL
- React frontend (not vanilla JS)
- All API responses use `{ success: true/false, data/error, code }` format

## Gotchas

- Workflow command uses absolute path: `python /home/runner/workspace/backend/manage.py`
- `channels` app renamed to `channels_app` to avoid conflict with Django Channels package
- Google Font (Vazirmatn) loaded in both `index.html` and `index.css` — must be first import
- APScheduler starts on Django startup; if it fails, publishing queue won't process automatically
