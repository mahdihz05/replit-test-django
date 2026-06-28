---
name: Django workflow absolute path
description: Django manage.py must be run with an absolute path in artifact.toml because the CWD when the workflow starts is not the workspace root.
---

The artifact.toml `run` command for Django must use the absolute path:

```
run = "python /home/runner/workspace/backend/manage.py runserver 0.0.0.0:8000 --noreload"
```

**Why:** The workflow runner's CWD is not `/home/runner/workspace`, so `cd backend && python manage.py` fails with "No such file or directory". Absolute path always works.

**How to apply:** Any time a Django backend is in a `backend/` subdirectory and runs via artifact.toml, use the full absolute path to manage.py.
