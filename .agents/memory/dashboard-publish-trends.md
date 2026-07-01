---
name: Dashboard publish trends aggregation
description: Aggregate successful publishes by their completion date, not by creation date, so scheduled and retried jobs are counted accurately.
---

Dashboard charts that show "publishes per day" must count a job on the day it actually finished, not the day it was created or queued. A job created today might be scheduled for tomorrow or retried multiple times before succeeding. Using `created_at__date` shifts all successful publishes to the queueing day, which misleads users about when content actually went live.

**Why:** `PublishJob.created_at` is the queue time; `completed_at` is the success/failure time.

**How to apply:** For successful publishes, filter by `completed_at__date` (or `attempted_at` from a successful `PublishLog`) when building the daily trend chart and the "published today" stat card.
