---
name: Telegram media without caption
description: For Telegram, publish media (photos/videos/documents) without a caption and send the full text as a separate message to avoid Telegram caption length limits and keep posts readable.
---

When publishing content that includes both media and text to Telegram, send the media first with no caption, then send the text as a standalone `sendMessage`. Do not put the text into the caption field of `sendPhoto`, `sendVideo`, `sendMediaGroup`, or other media methods.

**Why:** Telegram imposes a caption length limit (currently 1024 characters). Long posts with images used to fail with `MESSAGE_CAPTION_TOO_LONG`. Splitting media and text into separate messages removes this limit entirely and gives a cleaner post layout.

**How to apply:**
- In the Telegram publisher, always send media attachments first (media groups or individual files) with `caption` omitted.
- After media succeeds, send the full body/title as a normal text message.
- If media fails, do not send the text; return the media error so the job can be retried or marked failed as a whole.
