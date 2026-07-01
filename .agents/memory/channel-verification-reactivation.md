---
name: Channel verification reactivation
description: Why a verified Telegram/Bale channel may not appear in the list if it was previously deleted, and how to fix it.
---

PublishChannel has a unique_together constraint on `(workspace, platform, external_id)`. When a channel is "deleted", the app only sets `is_active=False`; it is not removed from the database. If the user later tries to verify the same channel again, `get_or_create` returns the existing inactive record. Without explicitly setting `is_active=True`, the channel remains hidden from `channel_list` even though the verification status shows as verified.

**Why:** Soft-delete + re-verification looks like a success but the list filters by `is_active=True`, so the inactive record is excluded.

**How to apply:** In the scheduler/bot verification handler, after matching a code to a pending verification, always reactivate the channel record:

```python
channel, created = PublishChannel.objects.get_or_create(...)
if not created:
    channel.is_active = True
    channel.is_verified = True
    channel.save()
```

Also store the user-provided name on the `ChannelVerification` so the reactivated channel can be renamed from the generic `Telegram <chat_id>` default to the name the user actually entered.
