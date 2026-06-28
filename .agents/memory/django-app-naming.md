---
name: Django channels app naming conflict
description: Naming a Django app "channels" conflicts with the django-channels package. Use channels_app instead.
---

**Why:** Django's `django-channels` package registers an app also named `channels`. If you create your own `channels` app, Django raises `AppRegistryNotReady` or import conflicts.

**How to apply:** Always name custom channel management apps `channels_app` (or similar) in INSTALLED_APPS and the directory name. Reference it as `channels_app` throughout models, URLs, and imports.
