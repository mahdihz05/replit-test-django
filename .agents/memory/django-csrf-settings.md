---
name: Django CSRF settings for admin panel and Replit
description: Configure CSRF_TRUSTED_ORIGINS and cookie settings so the Django admin panel works behind Replit and custom domains.
---

The Django admin panel uses session-based form authentication and CSRF protection. On Replit (or any proxy/reverse-proxy setup), the admin login can fail with "CSRF verification failed" if the request origin is not in `CSRF_TRUSTED_ORIGINS` or if the cookie settings are wrong for the deployment scheme.

**How to apply:**
1. Set `CSRF_TRUSTED_ORIGINS` to the actual HTTPS origin(s) serving the app. In `settings.py`, fall back to `https://<REPLIT_DEV_DOMAIN>` in dev and read from a `CSRF_TRUSTED_ORIGINS` env var in production.
2. Keep `CSRF_COOKIE_SAMESITE = 'Lax'` for same-origin admin access; use `'None'` with `CSRF_COOKIE_SECURE = True` only if you must share cookies across origins.
3. Set `CSRF_COOKIE_SECURE = not DEBUG` so the cookie is only sent over HTTPS in production.
4. Set `CSRF_COOKIE_HTTPONLY = False` so client-side code can read the cookie if it ever needs to send a CSRF header.
5. The API endpoints (DRF) are CSRF-exempt because they use JWT authentication only, so the frontend SPA does not need a CSRF token.
