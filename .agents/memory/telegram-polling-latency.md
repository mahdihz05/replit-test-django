---
name: Telegram polling latency from Replit
description: Network latency from the Replit environment to Telegram can make short-polling unreliable; long-polling is more stable.
---

Direct HTTP calls from the Replit environment to `api.telegram.org` can take 0.9–5+ seconds. Running APScheduler with `IntervalTrigger(seconds=1)` and short-polling `getUpdates` causes each request to overlap with the next one, so APScheduler logs `skipped: maximum number of running instances reached (1)` and the effective polling rate drops unpredictably.

**Why:** The interval is shorter than the request duration, so jobs pile up and get skipped.

**How to apply:** Use long-polling (`timeout=3-5` in the Telegram `getUpdates` params) and set the APScheduler interval slightly longer than the HTTP timeout (e.g., interval=8s, HTTP timeout=8s). This avoids overlapping instances while still responding quickly when a new message arrives, because Telegram returns immediately on new messages. For truly instant verification, a webhook is required; polling is only as fast as network latency allows.
