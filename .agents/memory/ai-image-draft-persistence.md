---
name: AI image draft persistence
description: When an AI generation endpoint returns a generated image alongside text, it must persist the image as a Content draft and return the content_id so the frontend can save/publish the image instead of creating a text-only duplicate.
---

When an AI endpoint accepts `generate_image: true` and returns `items` including an image, it must also create a `Content` draft with the image attached and return `content_id`.

**Why:** The frontend "Save" button used to create a brand-new `Content` record with only the text, losing the image that was already generated. If the backend already created a draft with the image, the frontend can reuse it (or update it). If the backend does not create a draft, the image exists only as a `GeneratedItem` and is never visible in the content library or publish flow.

**How to apply:**
- In any generation view that calls `_generate_image_for_batch`, also call `_persist_batch_as_content_draft` when the image succeeds and include `content_id` in the response.
- In the frontend, when `savedContentId` is returned, update the existing draft instead of `POST`ing a new content record.
