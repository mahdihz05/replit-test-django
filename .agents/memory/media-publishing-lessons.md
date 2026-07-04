---
name: Media publishing path handling and workspace scoping
description: Lessons learned while implementing AI image generation and multi-media publishing (Telegram/Bale/LinkedIn/WordPress) in this Django/React app.
---

## Workspace scoping for attachments

When validating or attaching `PublishAttachment` records, always pass `workspace_id` explicitly into the validation helper and filter by `workspace_id` in the ORM query. Do not rely on closure variables or implicit request context; it is easy to reference an undefined variable and silently break authorization.

**Why:** During implementation the first `_validate_attachments` version referenced `workspace_id` without accepting it as a parameter, which would have caused a runtime crash and prevented tenant isolation from running.

**How to apply:** Any helper that loads workspace-owned records by ID must take `workspace_id` as a parameter and the caller (view) must pass it.

## Media path resolution

Use a single canonical resolver for media file paths. Prefer passing the model field name (e.g. `content.image.name`) to the resolver instead of concatenating `MEDIA_URL` with the field, which can double-prefix paths or produce invalid filesystem paths when `MEDIA_URL` has its own path prefix.

**Why:** LinkedIn and WordPress fallback image uploads initially built paths via `f'{settings.MEDIA_URL}{content.image}'`, which resolves incorrectly when `MEDIA_URL` is `/media/` and the resolver then prepends `MEDIA_ROOT`.

**How to apply:** For local files, use `content.image.name` or a dedicated `_resolve_media_path(path_or_url)` helper that handles both relative paths and absolute URLs exactly once.

## Telegram media-group limits

Telegram's `sendMediaGroup` accepts at most 10 items. When publishing more than 10 image/video attachments, chunk them into groups of 10 and send each group. Do not silently truncate or drop extras.

**Why:** The first implementation capped at `attachments[:10]`, which would drop additional media without any user-visible signal.

**How to apply:** Use `[attachments[i:i + 10] for i in range(0, len(attachments), 10)]` and call `_send_media_group` per chunk. Only the first chunk should carry the caption.

## Non-retriable publisher errors

Mark platform-unsupported media (`unsupported_media`) as a non-retriable error in the scheduler so failed jobs do not waste retry attempts.

**Why:** Retrying an unsupported media type is futile and delays feedback to the user.

**How to apply:** In the scheduler, set `job.status = 'failed'` immediately when `error_type == 'unsupported_media'`, bypassing the retry/backoff logic.