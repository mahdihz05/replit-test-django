---
name: LLM word-count enforcement
description: How to get LLMs to respect a requested word count in the face of platform-specific character limits.
---

When asking an LLM to produce a specific word count, the model often underwrites because it has been trained to be concise and because earlier platform-specific instructions (e.g., "stay under 4096 characters for Telegram") take precedence in its attention.

**Rule:** Make the word-count requirement the *highest-priority* constraint in the user prompt and explicitly tell the model to ignore conflicting character limits for that request.

**Why:** Models tend to treat the first "HIGHEST PRIORITY CONSTRAINT" as the true ceiling. If that ceiling is a character limit, the word count will be silently overridden.

**How to apply:**
- Put the word-count block near the end of the user prompt (where the model focuses before outputting) and label it as the highest-priority constraint.
- State the exact allowed range, e.g., "Stay within 900–1100 words."
- Add an explicit override: "If this conflicts with the platform rules above, the word-count requirement WINS."
- Compensate for the model's tendency to underwrite by aiming for the upper end of the range (around 1100 for a 1000-word target).
- Add a self-check instruction: "Before finishing, count the words in your response. If outside the range, expand with concrete examples or trim."
