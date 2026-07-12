---
name: Telegram channel posts vs messages
description: Telegram sends channel updates as `channel_post` (not `message`), so verification bots must handle both.
---

Telegram distinguishes between regular chats/groups and channels in its update payload.

- **Private chats and groups:** messages arrive as `message`.
- **Channels:** messages arrive as `channel_post` (and edits as `edited_channel_post`).

A bot that only inspects `update.message` or `body.get('message')` will silently ignore every message sent in a Telegram channel, even if the bot is an admin with full rights. This is why a verification code sent in a channel appeared to never be seen by the bot, while the same code sent in a private chat or group worked.

**How to apply:**
1. In webhook handlers, check `body.get('message') or body.get('channel_post')` (and optionally `edited_message` / `edited_channel_post`).
2. In `python-telegram-bot`, add handlers for `filters.UpdateType.CHANNEL_POST` in addition to `filters.UpdateType.MESSAGE`.
3. Extract the verification token with `re.search(r'VRF-[A-Z0-9]{8}', text)` rather than `re.match`, so users can include the code in a longer message or caption.
