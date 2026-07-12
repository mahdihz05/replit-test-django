---
name: Telegram bot startup wiring in this Django project
description: How the Telegram bot must be registered and started so channel verification works.
---

The Telegram verification bot lives in `backend/bots/telegram_bot.py`. It is **not** started automatically unless the `bots` app is registered in `INSTALLED_APPS` and the app's `ready()` handler calls `start_bot()`.

**Why:** If the bot is never started, users can send the `VRF-...` token in a Telegram channel forever and the backend will never see it, so `ChannelVerification` stays `pending` and the channel never appears as verified.

**How to apply:**
1. Add `'bots'` (or `'bots.apps.BotsConfig'`) to `INSTALLED_APPS` in `backend/config/settings.py`.
2. In `backend/bots/apps.py` (or the main app `ready()`), call `start_bot()` only in the real serving process (skip the Django autoreloader parent by checking `RUN_MAIN`).
3. Use a module-level flag to prevent double-starting the bot when `ready()` is invoked multiple times.
4. Prefer webhook mode on Replit; fall back to long-polling only when no public domain is available.
