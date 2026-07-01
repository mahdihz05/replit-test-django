---
name: AI form field consistency
description: When refactoring AI generation forms, ensure frontend input fields match the exact API parameter names used by existing endpoints.
---

When extending a form that calls existing backend endpoints, reusing a different state field for the same conceptual input can silently break an existing flow. For example, the CTA endpoint expected `goal`, but a refactored form bound the input to `topic`; the API call then sent an empty `goal`, causing the standard CTA path to fail without an obvious UI error.

**Why:** Existing endpoints are strict about their parameter names and do not fall back to other fields. A mismatch looks like a backend bug but is actually a frontend contract regression.

**How to apply:** When adding new modes (bundle, multi-variant) to `/ai-generate`, keep each capability's input field name identical to the parameter name sent by the existing standard endpoint. If a capability's standard endpoint uses `goal`, the new form must also write to `goal` for that capability, even if the label changes.
