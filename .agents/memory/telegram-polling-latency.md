---
name: Telegram polling latency and conflicts on Replit
description: Why polling from Replit conflicts and how webhook mode is the reliable choice for Telegram bots.
---

Direct HTTP calls from the Replit environment to `api.telegram.org` can take 0.9–5+ seconds. Running `python-telegram-bot` with `IntervalTrigger(seconds=1)` and short-polling `getUpdates` causes each request to overlap with the next one, so APScheduler logs `skipped: maximum number of running instances reached (1)` and the effective polling rate drops unpredictably.

**Why:** The interval is shorter than the request duration, so jobs pile up and get skipped.

**How to apply:** For a production-like setup on Replit, use webhook mode (`setWebhook`) pointed at the Replit dev domain (`https://<REPLIT_DEV_DOMAIN>/api/webhooks/telegram/`) instead of polling. This avoids the latency overlap, the stale-connection conflict after restarts, and gives near-instant delivery. When polling is required, use long-polling (`timeout=3-5` in `getUpdates` params) and set the interval slightly longer than the HTTP timeout (e.g., interval=8s, HTTP timeout=8s). This avoids overlapping instances while still responding quickly when a new message arrives, because Telegram returns immediately on new messages.

**Replit restart conflict:** `getUpdates` long-poll connections can outlive a Django process restart. When the new process starts polling before the previous connection times out, Telegram returns `409 Conflict: terminated by other getUpdates request`. The bot then fails to poll. Webhook mode is the clean fix: set the webhook on startup and let Telegram push updates to the app.
