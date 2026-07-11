"""Platform-aware prompt engineering for the AI engine.

All rules are based on the real formatting constraints of the target platforms
(Telegram/Bale, LinkedIn, WordPress/website) and are written in English to the
model while the output must remain in Persian.
"""

from typing import Literal


PLATFORM_IDS = Literal["telegram", "bale", "linkedin", "instagram", "website", ""]


def _normalize_platform(platform: str) -> str:
    p = (platform or "").lower().strip()
    if p in ("telegram", "bale", "linkedin", "instagram", "website"):
        return p
    return ""


# ---------------------------------------------------------------------------
# Platform rules used in prompt bodies
# ---------------------------------------------------------------------------

def get_platform_rules(platform: str) -> str:
    """Return a concise block of formatting rules for the requested platform."""
    p = _normalize_platform(platform)

    if p in ("telegram", "bale"):
        return (
            "Platform rules (Telegram/Bale):\n"
            "- Output must be in Persian.\n"
            "- Use ONLY Telegram's limited Markdown: *bold* with a single asterisk, "
            "_italic_ with a single underscore, `monospace` with a single backtick.\n"
            "- NEVER use standard Markdown such as **bold**, # headings, or '- ' list bullets.\n"
            "- Instead of headings, use blank lines between short paragraphs and emojis at the "
            "start of lines (e.g., ✅ 🔹 👇) to separate sections.\n"
            "- Keep paragraphs short (2-4 lines) because most users read on mobile.\n"
            "- If the output will be used as a caption for an image, keep it under 1024 characters. "
            "If it is a standalone message, it may be up to 4096 characters.\n"
            "- Hashtags: 3-5 in a single line at the end.\n"
            "- No extra introduction, no markdown code fences, just the ready-to-publish body."
        )

    if p == "linkedin":
        return (
            "Platform rules (LinkedIn):\n"
            "- Output must be in Persian.\n"
            "- LinkedIn does NOT render Markdown. NEVER output raw **bold**, # headings, or '- ' lists.\n"
            "- For real visual emphasis, use actual Unicode bold/italic characters only for the "
            "opening hook or a single key phrase/number in the text (e.g., 𝗯𝗼𝗹𝗱 from the Mathematical "
            "Bold Unicode range). Do NOT convert whole paragraphs to Unicode bold.\n"
            "- For bullets, use Unicode characters such as • or ▸ at the start of a line.\n"
            "- Hashtags must be plain text (no Unicode styling) so they remain searchable. "
            "Use 3-5 hashtags in a single line at the end.\n"
            "- The first two lines must be independent, compelling, and contain a clear hook "
            "(a surprising statistic, counter-intuitive claim, or direct question).\n"
            "- Avoid an early blank line right after the hook; it can trigger LinkedIn's 'see more' fold.\n"
            "- Target length is 1300-2000 characters as a soft guideline; do not force it if the topic "
            "naturally needs a bit more or less.\n"
            "- No extra introduction, no markdown code fences, just the ready-to-publish body."
        )

    if p == "instagram":
        return (
            "Platform rules (Instagram):\n"
            "- Output must be in Persian.\n"
            "- Keep the caption friendly and visual; avoid heavy Markdown.\n"
            "- Line breaks and emojis are fine for readability.\n"
            "- Hashtags: 3-5 relevant hashtags in a single line at the end.\n"
            "- No extra introduction, just the ready-to-publish caption."
        )

    if p in ("website", "wordpress"):
        return (
            "Platform rules (Website/WordPress article):\n"
            "- Output must be in Persian.\n"
            "- Produce real HTML: <h2> for sections, <h3> for subsections, <p> for paragraphs, "
            "<ul>/<li> for lists. Do NOT use Markdown.\n"
            "- Structure: intro paragraph (no heading) → 2-4 sections with <h2> → conclusion.\n"
            "- Respect the requested word count exactly; do not artificially shorten the article.\n"
            "- No extra introduction, no markdown code fences, just the ready-to-publish HTML."
        )

    # Generic fallback
    return (
        "General rules:\n"
        "- Output must be in Persian.\n"
        "- Avoid raw Markdown formatting such as **bold** or # headings unless explicitly requested.\n"
        "- Keep the output ready to publish with no extra explanation."
    )


# ---------------------------------------------------------------------------
# Capability builders
# ---------------------------------------------------------------------------

def build_text_prompt(goal: str, platform: str, tone: str, keywords: str, language: str, word_count: int, is_caption: bool = False) -> tuple[str, str]:
    """Return (system_prompt, user_prompt) for generate_text."""
    system = (
        "You are an expert Persian content creator for social media and websites. "
        "You write platform-native content that needs no manual editing before publishing. "
        "You always respect the requested length and output exactly the amount of content asked for."
    )
    caption_note = ""
    if is_caption and _normalize_platform(platform) in ("telegram", "bale"):
        caption_note = (
            "IMPORTANT: This text will be used as a caption for an image on Telegram/Bale. "
            "Keep it under 1024 characters. Make it concise and impactful.\n"
        )
    user = (
        f"{get_platform_rules(platform)}\n\n"
        f"Write content with these specifications:\n"
        f"Goal/topic: {goal}\n"
        f"Platform: {platform or 'general'}\n"
        f"Tone: {tone}\n"
        f"Keywords: {keywords}\n"
        f"Language: {'Persian' if language == 'fa' else language}\n"
        f"STRICT LENGTH REQUIREMENT: The final output must be approximately {word_count} words. "
        f"Stay within ±10% of {word_count} words ({int(word_count * 0.9)}–{int(word_count * 1.1)} words). "
        f"Do not make it significantly shorter or longer. If the user asked for a long/detailed article, write the full length without cutting it short.\n"
        f"{caption_note}\n"
        f"Write only the ready-to-publish body. No extra explanation."
    )
    return system, user


def build_rewrite_prompt(text: str, tone: str, platform: str) -> tuple[str, str]:
    system = "You are an expert Persian content rewriter."
    user = (
        f"{get_platform_rules(platform)}\n\n"
        f"Rewrite the following text while preserving its meaning and facts.\n"
        f"Tone: {tone}\n"
        f"Target platform: {platform or 'general'}\n\n"
        f"Text:\n{text}\n\n"
        f"Return only the rewritten body, no extra explanation."
    )
    return system, user


def build_titles_prompt(topic: str, count: int, platform: str) -> tuple[str, str]:
    system = "You are an expert Persian content creator."
    user = (
        f"{get_platform_rules(platform)}\n\n"
        f"Suggest {count} compelling, non-clickbait titles for this topic.\n"
        f"Topic: {topic}\n"
        f"Target platform: {platform or 'general'}\n\n"
        f"Provide a varied mix: curiosity, benefit, question, numeric, urgency.\n"
        f"Return only the titles, one per line."
    )
    return system, user


def build_hashtags_prompt(topic: str, count: int, platform: str) -> tuple[str, str]:
    system = "You are an expert Persian social media specialist."
    user = (
        f"{get_platform_rules(platform)}\n\n"
        f"Suggest {count} relevant hashtags for this topic.\n"
        f"Topic: {topic}\n"
        f"Target platform: {platform or 'general'}\n\n"
        f"Mix popular and niche tags. For LinkedIn, hashtags must be plain Persian text (no Unicode styling).\n"
        f"Return only the hashtags, one per line."
    )
    return system, user


def build_cta_prompt(goal: str, platform: str, count: int) -> tuple[str, str]:
    system = "You are an expert Persian copywriter."
    user = (
        f"{get_platform_rules(platform)}\n\n"
        f"Write {count} strong, action-oriented call-to-action lines for this goal.\n"
        f"Goal: {goal}\n"
        f"Target platform: {platform or 'general'}\n\n"
        f"LinkedIn tone: professional/inviting, not aggressive sales.\n"
        f"Telegram/Bale tone: can be more direct.\n"
        f"Return only the CTAs, one per line."
    )
    return system, user


def build_summary_prompt(text: str, length: str) -> tuple[str, str]:
    system = "You are an expert Persian content summarizer."
    length_fa = "کوتاه و فشرده" if length == "brief" else "جامع و کامل"
    user = (
        f"Summarize the following text in Persian.\n"
        f"Style: {length_fa}\n\n"
        f"Text:\n{text}\n\n"
        f"Return only the summary, no extra explanation."
    )
    return system, user


def build_scenario_prompt(topic: str, platform: str, goal: str) -> tuple[str, str]:
    system = "You are an expert Persian content strategist and scriptwriter."
    user = (
        f"{get_platform_rules(platform)}\n\n"
        f"Write a complete content scenario with this structure: Hook, Body, Call-to-Action.\n"
        f"Topic: {topic}\n"
        f"Platform: {platform or 'general'}\n"
        f"Goal: {goal}\n\n"
        f"Start directly with the hook; no greeting or preamble.\n"
        f"Return only the ready-to-publish body."
    )
    return system, user


def build_idea_prompt(niche: str, platform: str, count: int) -> tuple[str, str]:
    system = "You are an expert Persian content idea generator."
    user = (
        f"{get_platform_rules(platform)}\n\n"
        f"Suggest {count} genuinely different content ideas for this niche.\n"
        f"Niche: {niche}\n"
        f"Target platform: {platform or 'general'}\n\n"
        f"Each idea must be followed by one sentence explaining why it would be effective.\n"
        f"Return only the ideas, one per line."
    )
    return system, user


def build_bundle_prompt(topic: str, platform: str, tone: str) -> tuple[str, str]:
    system = (
        "You are an expert Persian content creator. "
        "Return only a valid JSON object with no Markdown or extra explanation. "
        "The JSON must contain exactly these keys: full_text, short_text, hashtags, title."
    )
    user = (
        f"{get_platform_rules(platform)}\n\n"
        f"Create a content bundle for this topic:\n"
        f"Topic: {topic}\n"
        f"Target platform: {platform or 'general'}\n"
        f"Tone: {tone}\n\n"
        f"Output must be a JSON object with exactly this structure:\n"
        f'{{\n'
        f'  "full_text": "The main body following the rules of the requested platform (at least 500 chars).",\n'
        f'  "short_text": "A short version always suitable for Telegram/Bale (max 400 chars, no double-asterisk bold, limited Telegram Markdown only).",\n'
        f'  "hashtags": ["tag1", "tag2", "tag3", "tag4", "tag5"],\n'
        f'  "title": "A short, punchy title"\n'
        f'}}\n\n'
        f"Return only the raw JSON, no code fences, no trailing commas."
    )
    return system, user


def build_variants_prompt(capability: str, params: dict, count: int) -> tuple[str, str]:
    system = (
        "You are an expert Persian content creator. "
        "Return only a valid JSON object with no Markdown or extra explanation. "
        "The JSON must contain exactly one key: 'variants' which is an array of strings."
    )

    capability_labels = {
        "text": "تولید متن",
        "rewrite": "بازنویسی",
        "summary": "خلاصه‌سازی",
        "scenario": "سناریو",
        "title": "پیشنهاد عنوان",
        "hashtag": "پیشنهاد هشتگ",
        "cta": "CTA",
        "idea": "ایده محتوا",
    }
    label = capability_labels.get(capability, "تولید محتوا")
    platform = params.get("platform", "")
    topic = params.get("topic", params.get("goal", params.get("niche", params.get("text", ""))))
    tone = params.get("tone", "حرفه‌ای")
    length = params.get("length", "brief")
    word_count = params.get("word_count", 300)

    capability_prompts = {
        "text": (
            f"{get_platform_rules(platform)}\n\n"
            f"Write {count} different full texts for this topic with tone {tone} for platform {platform or 'general'}. "
            f"Each version should be around {word_count} words."
        ),
        "rewrite": (
            f"{get_platform_rules(platform)}\n\n"
            f"Rewrite the following text in {count} different tones/angles. Suggested tone: {tone}."
        ),
        "summary": (
            f"Summarize the following text in {count} different summaries with varied lengths or angles. "
            f"Requested length: {length}."
        ),
        "scenario": (
            f"{get_platform_rules(platform)}\n\n"
            f"Write {count} different content scenarios for topic {topic} on platform {platform or 'general'} "
            f"with goal {params.get('goal', '')}."
        ),
        "title": (
            f"{get_platform_rules(platform)}\n\n"
            f"Suggest {count} different titles for the topic {topic}."
        ),
        "hashtag": (
            f"{get_platform_rules(platform)}\n\n"
            f"Suggest {count} different hashtag sets for topic {topic} on platform {platform or 'general'}."
        ),
        "cta": (
            f"{get_platform_rules(platform)}\n\n"
            f"Write {count} different CTAs for goal {topic} on platform {platform or 'general'}."
        ),
        "idea": (
            f"{get_platform_rules(platform)}\n\n"
            f"Suggest {count} different content ideas for niche {topic} on platform {platform or 'general'}."
        ),
    }

    body_context = f"\n\nInput/content/text:\n{topic}" if topic else ""
    user = (
        f"{capability_prompts.get(capability, f'Create {count} different versions for {label}')}\n\n"
        f"Output must be a JSON object exactly like this:\n"
        f'{{\n  "variants": ["نسخه ۱", "نسخه ۲", "نسخه ۳"]\n}}\n\n'
        f"Each array item must be a complete, independent version. "
        f"Return only the raw JSON, no code fences, no trailing commas.{body_context}"
    )
    return system, user


def build_chat_system_prompt() -> str:
    return (
        "You are a helpful Persian content strategy assistant. "
        "When the user asks for content meant for a specific platform (Telegram, Bale, LinkedIn, Instagram, Website), "
        "apply the following rules in your output:\n\n"
        f"{get_platform_rules('telegram')}\n\n"
        f"{get_platform_rules('linkedin')}\n\n"
        f"{get_platform_rules('website')}\n\n"
        "Keep responses concise and useful. Ask clarifying questions only when there is genuine ambiguity."
    )


# ---------------------------------------------------------------------------
# Image prompt builders
# ---------------------------------------------------------------------------

def build_image_prompt_from_text(source_text: str, platform: str, max_words: int = 25) -> str:
    """Build an English DALL-E prompt from Persian source text, platform-aware."""
    p = _normalize_platform(platform)

    platform_visual_notes = {
        "telegram": (
            "The image should be clear, simple, and readable on mobile. Avoid dense text overlays. "
            "Use a single focal point and a clean background."
        ),
        "bale": (
            "The image should be clear and friendly, suitable for a Persian chat app. "
            "Avoid dense text and complex collages."
        ),
        "linkedin": (
            "The image should be professional, business-appropriate, and clean. "
            "Use a modern corporate or editorial style. Avoid cartoons and excessive decoration."
        ),
        "instagram": (
            "The image should be visually striking, aesthetic, and square-friendly. "
            "Use high-quality photography or polished illustration with a strong focal point."
        ),
        "website": (
            "The image should be clean, high-quality, and suitable for a blog or landing page header. "
            "Prefer realistic photography or minimal illustration."
        ),
    }

    visual_note = platform_visual_notes.get(p, "The image should be high-quality and suitable for social media or web use.")

    prompt = (
        f"Write a concise, vivid English image generation prompt for DALL-E 3 based on the following Persian text. "
        f"Maximum {max_words} words. Focus on real visual elements. "
        f"Do not ask for typography or text inside the image. {visual_note}\n\n"
        f"Source text:\n{source_text[:2000]}\n\n"
        f"Return only the prompt, no extra explanation."
    )
    return prompt


def build_image_prompt_enhancement(description: str, platform: str) -> str:
    """Enhance a raw image description with platform-aware constraints."""
    p = _normalize_platform(platform)
    platform_notes = {
        "telegram": "mobile-friendly, simple composition, single focal point, no text overlays",
        "bale": "friendly chat-app style, simple composition, no dense text",
        "linkedin": "professional business style, clean editorial, no cartoons, no text overlays",
        "instagram": "aesthetic, visually striking, square-friendly, no text overlays",
        "website": "clean high-quality blog/landing page header, realistic or minimal illustration, no text overlays",
    }
    note = platform_notes.get(p, "high-quality, suitable for social media or web")
    return f"{description}. Style: {note}. No text, no logos, no typography inside the image."
