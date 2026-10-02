# Mohtavayar: exploratory content automation application

A Django API and Persian RTL React frontend for workspace-based content creation, AI assistance and publishing experiments. This public repository is an exploratory implementation, not a production-ready SaaS claim. It includes Replit scaffolding and deployment notes; neither proves a completed deployment.

## Architecture and code entry points

- [backend/manage.py](backend/manage.py) and `backend/config/`: configuration, URL routing and application startup.
- `backend/users/`, `backend/workspaces/` and `backend/content/`: authentication, workspace membership and content/version records.
- `backend/ai_engine/`, `backend/channels_app/` and `backend/publishing/`: AI calls, channel connections, queued publishing and platform adapters.
- `backend/communication/`, `backend/wallet/` and `backend/reports/`: dispatch, credit records and reporting endpoints.
- `artifacts/frontend/src/`: React/Vite interface. [vite.config.ts](artifacts/frontend/vite.config.ts) proxies API, media, admin and static requests to Django.
- `lib/` and `artifacts/`: additional workspace clients, schemas and scaffolding. The root [main.py](main.py) only prints a greeting; it is not the application server.

[replit.md](replit.md) retains the original project notes. This English entry point avoids relying on Replit-specific absolute paths.

## Safe local prerequisites

Use Python 3.11 or newer, PostgreSQL, a Node runtime compatible with the committed Vite toolchain, and pnpm 10.34.5 as declared in [package.json](package.json). A pnpm workspace/lockfile and `uv.lock` are present. Backend requirements have broader lower bounds than `pyproject.toml`; their installation paths have not been proven equivalent.

Configure a disposable `DATABASE_URL`, a newly generated local `SECRET_KEY` and local host/CORS settings through environment variables. Leave AI, SMS, messaging and publishing credentials unset. Do not copy a real database, contact import, embedding payload, channel credentials or customer media. Use invented workspace/content records and block outbound provider traffic.

After reviewing install hooks and environment configuration, an isolated local starting sequence is:

```sh
python -m pip install -r backend/requirements.txt
cd backend
python manage.py check
python manage.py migrate
python manage.py test
python manage.py runserver 127.0.0.1:8000
```

In a separate terminal at the repository root:

```sh
pnpm install --frozen-lockfile
pnpm --filter @workspace/frontend run dev
```

These commands were not executed for this README change. Database commands write to the configured database, and startup can activate background work. Review the scheduler caveat below before even management commands. Vite binds to all interfaces by default; restrict access to the local machine. Workspace dependency overrides target Replit/Linux and may prevent a clean native Windows/macOS installation; no cross-platform setup is certified.

## Scheduler and provider caveats

[backend/config/apps.py](backend/config/apps.py) starts APScheduler from Django startup outside the test guard. [backend/bots/apps.py](backend/bots/apps.py) can start provider polling; disabling Telegram polling alone does not disable every background task. Do not connect a production database while inspecting commands.

[publishing/scheduler.py](backend/publishing/scheduler.py) uses an in-process scheduler and host-local PID-file check. It conditionally claims queued database jobs and records attempts. These mechanisms do not prove race-free startup, distributed singleton execution, crash recovery or exactly-once delivery. Polling offsets are in memory and reset on restart. Failed startup can leave work unprocessed; multiple hosts need a separate operational review. The implemented ordinary retry delay is five minutes multiplied by attempt count, not the exponential-backoff claim in older notes.

## Evidence and remaining work

Static Django test files and frontend typecheck/build scripts exist. No hosted Actions application runs were observed, and this documentation change ran no tests, build, provider calls or deployment. Tenant isolation, auth, wallet accounting, real publishing and concurrent scheduler behavior remain unverified here.

Existing [screenshots](screenshots/) and deployment guides remain historical material. Screenshots are not current runtime proof and were not reviewed for visual quality or data safety in this change. Deployment/merge scripts are not setup requirements; do not invoke them during a portfolio review. No new software license or asset reuse permission is asserted.
