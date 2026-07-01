---
name: OpenAI JSON retry with validation
description: When retrying OpenAI structured-output calls, include JSON parsing and schema validation inside the retry loop, not after it.
---

OpenAI can return malformed JSON, Markdown fences, or JSON missing required keys. A retry helper that only retries on transport/exception errors will not catch these cases. The parse-and-validate step must be part of the retry decision so that each attempt has a chance to produce a valid structured response.

**Why:** `response_format={"type": "json_object"}` reduces but does not eliminate invalid shapes. Missing keys or unexpected formatting are common enough that they should not immediately surface as a user-facing error.

**How to apply:** Pass a `validate(text)` callback to the retry helper. The callback returns the parsed object on success or `None` on failure. The helper should loop for `max_retries`, counting both API exceptions and validation failures as retryable attempts. Only after exhausting attempts should it return the Persian error message "تولید محتوا با خطا مواجه شد. لطفاً دوباره تلاش کنید."
