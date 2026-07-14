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

def _platform_persona(platform: str) -> str:
    """Return a short role/persona line that activates the right domain expertise."""
    p = _normalize_platform(platform)
    personas = {
        "telegram": "You are an experienced Telegram/Bale channel writer who explains useful ideas in a "
                    "warm, conversational voice — think 'a sharp friend explaining something useful', not "
                    "a news anchor or a textbook.",
        "bale": "You are an experienced Telegram/Bale channel writer who explains useful ideas in a "
                "warm, conversational voice — think 'a sharp friend explaining something useful', not "
                "a news anchor or a textbook.",
        "linkedin": "You are a senior B2B copywriter who ghostwrites for founders and industry experts on "
                    "LinkedIn. You are known for posts that open with a real hook and deliver one specific, "
                    "non-obvious insight — never generic career-advice filler.",
        "instagram": "You are a social media caption writer who specializes in short, visual-first captions "
                     "that make people stop scrolling in the first line.",
        "website": "You are an experienced Persian content writer and SEO editor who writes articles that "
                   "directly and thoroughly answer the reader's question, in the style of a trusted "
                   "publication, not a content farm.",
    }
    return personas.get(p, "You are an expert Persian content writer.")


def get_platform_rules(platform: str) -> str:
    """Return formatting AND content-quality rules for the requested platform, with a short good/bad example."""
    p = _normalize_platform(platform)

    if p in ("telegram", "bale"):
        return (
            "Platform rules (Telegram/Bale, verified 2026):\n"
            "- Output must be in Persian.\n"
            "- HIGHEST PRIORITY CONSTRAINT: if this is an image caption, stay under 1024 characters; "
            "otherwise stay under 4096 characters.\n"
            "- Use ONLY Telegram's limited Markdown: *bold* with a single asterisk, _italic_ with a single "
            "underscore, `monospace` with a single backtick. NEVER use **bold**, # headings, or '- ' bullets.\n"
            "- Use blank lines between short paragraphs and emojis at the start of lines (e.g., ✅ 🔹 👇) "
            "instead of headings. Keep paragraphs to 2-4 lines for mobile readability.\n"
            "- Hashtags: 3-5 in a single line at the end.\n"
            "- CONTENT STANDARD ('edutainment'): every post must teach something or solve a problem, "
            "delivered informally — like a knowledgeable friend explaining it, not a lecture. The requested "
            "tone changes the DELIVERY, not whether there's real substance:\n"
            "  * specialist/professional tone -> simple language, still ONE solid actionable insight, no dense jargon\n"
            "  * casual/fun tone -> more jokes/emojis, looser structure, but still ends with one real takeaway\n"
            "- GOOD example opening: 'یه اشتباه که ۹۰٪ آدما توی بودجه‌بندی ماهانه می‌کنن؟ فکر می‌کنن پس‌انداز "
            "یعنی چیزی که ته ماه می‌مونه 👇' (concrete claim, curiosity, promise of value)\n"
            "- BAD opening to avoid: 'سلام دوستان عزیز، امروز می‌خوایم راجع به یه موضوع مهم صحبت کنیم' "
            "(generic throat-clearing with zero information)\n"
            "- No extra introduction, no markdown code fences, just the ready-to-publish body."
        )

    if p == "linkedin":
        return (
            "Platform rules (LinkedIn, verified 2026 data):\n"
            "- Output must be in Persian.\n"
            "- HIGHEST PRIORITY CONSTRAINT: LinkedIn truncates posts behind 'see more' after ~140-210 "
            "characters on mobile. The first 1-2 lines MUST work as a fully independent hook (a contrarian "
            "statement, a surprising statistic, or a direct question) — most readers never tap 'see more', "
            "so nothing essential can depend on later text.\n"
            "- Do not put a blank line immediately after the hook; it can cut the visible snippet shorter.\n"
            "- LinkedIn does NOT render Markdown. NEVER output **bold**, # headings, or '- ' lists. For "
            "emphasis, use real Unicode bold (𝗹𝗶𝗸𝗲 𝘁𝗵𝗶𝘀) only on the hook or one key number — never a "
            "whole paragraph. For bullets use • or ▸.\n"
            "- Hashtags: plain text only, 3-5 max at the end; more than 5 hurts reach.\n"
            "- Target 1300-2500 characters (soft target); posts under ~400 characters underperform. Hard "
            "ceiling is 3000 characters.\n"
            "- Structure: hook -> concrete context (one problem, one moment, one example, ideally with a "
            "specific number) -> the lesson/framework/insight -> a soft closing question inviting comments, "
            "not a hard sales pitch.\n"
            "- CONTENT STANDARD: the requested tone must be pushed further here than on any other platform:\n"
            "  * specialist/professional tone -> go DEEPER than elsewhere: a named framework, a specific "
            "number, a real before/after result. Generic advice ('consistency matters', 'communication is "
            "key') is a failure state on this platform.\n"
            "  * casual/personal tone -> still resolve into a professional lesson by the end (story -> "
            "takeaway relevant to work), not just entertainment.\n"
            "- GOOD hook example: '۳ سال پیش یه مشتری رو به خاطر یه ایمیل از دست دادیم. الان می‌دونم مشکل "
            "چی بود.' (specific, creates a real curiosity gap)\n"
            "- BAD hook example: 'در دنیای امروز، ارتباط مؤثر یکی از مهم‌ترین مهارت‌هاست.' (generic "
            "truism, no hook, no reason to keep reading)\n"
            "- No extra introduction, no markdown code fences, just the ready-to-publish body."
        )

    if p == "instagram":
        return (
            "Platform rules (Instagram, verified 2026 data):\n"
            "- Output must be in Persian.\n"
            "- HIGHEST PRIORITY CONSTRAINT: Instagram truncates behind 'more' after ~125 characters. The "
            "hook/question/key message must be in the very first line.\n"
            "- No Markdown or bold/italic is rendered; rely only on line breaks and emojis for structure. "
            "Use generous line breaks between short thoughts — walls of text get scrolled past.\n"
            "- End with a light call to action (a question, 'ذخیره کن', 'نظرت رو بگو') to drive saves/"
            "comments, which the algorithm weighs heavily.\n"
            "- Hashtags: 3-5 highly relevant ones on their own line at the end; 10+ can trigger silent "
            "reach suppression.\n"
            "- CONTENT STANDARD: visual-first and emotionally engaging, supporting an image rather than "
            "replacing one.\n"
            "  * specialist/professional tone -> short, punchy, highly scannable tips, never a lecture\n"
            "  * casual/fun tone -> storytelling and personality can lead more openly\n"
            "- No extra introduction, just the ready-to-publish caption."
        )

    if p in ("website", "wordpress"):
        return (
            "Platform rules (Website/WordPress article, verified 2026 SEO/GEO practice):\n"
            "- Output must be in Persian.\n"
            "- Produce real HTML: <h2> sections, <h3> subsections, <p> paragraphs, <ul>/<li> lists. No Markdown.\n"
            "- HIGHEST PRIORITY CONSTRAINT: the first 2-3 sentences must directly state the core answer/value "
            "and include the main topic within the first ~100 words — both human readers and AI search "
            "engines (ChatGPT, Google AI Overviews, Perplexity) extract answers from the top of the page.\n"
            "- 3-5 <h2> sections phrased as natural questions/statements a reader would search for, each able "
            "to stand alone as a direct answer. Close with a short practical takeaway.\n"
            "- Target ~1500-2000 words for a standard article (600-900 for a narrow how-to, 2500+ for a "
            "pillar guide). Preserve this structure even with a shorter requested word_count — compress "
            "sections, don't drop them.\n"
            "- CONTENT STANDARD: judged on depth and trustworthiness, not personality. Regardless of tone, "
            "prioritize accuracy, concrete examples, and directly answering the reader's question over filler.\n"
            "  * specialist/professional tone -> precise terminology, real mechanisms/steps/data\n"
            "  * casual/accessible tone -> simpler language but SAME depth of information, not less content\n"
            "- BAD pattern to avoid: a paragraph that just restates the heading in different words without "
            "adding new information ('در این بخش به بررسی اهمیت X می‌پردازیم' with no actual content after it).\n"
            "- No extra introduction, no markdown code fences, just the ready-to-publish HTML."
        )

    return (
        "General rules:\n"
        "- Output must be in Persian.\n"
        "- Avoid raw Markdown formatting such as **bold** or # headings unless explicitly requested.\n"
        "- Prioritize concrete, specific, useful content over generic filler, regardless of tone.\n"
        "- Keep the output ready to publish with no extra explanation."
    )


# ---------------------------------------------------------------------------
# Capability builders
# ---------------------------------------------------------------------------

def build_text_prompt(goal: str, platform: str, tone: str, keywords: str, language: str, word_count: int, is_caption: bool = False) -> tuple[str, str]:
    """Return (system_prompt, user_prompt) for generate_text, built with a Role-Context-Constraints-Format structure."""
    system = (
        f"{_platform_persona(platform)} "
        "You write platform-native Persian content that needs no manual editing before publishing. "
        "You never pad with generic filler — every sentence must carry real information or move the reader forward. "
        "When a word count is requested, you MUST hit that target within ±10% even if it makes the output longer than a platform's usual recommendation."
    )

    caption_note = ""
    if is_caption and _normalize_platform(platform) in ("telegram", "bale"):
        caption_note = (
            "IMPORTANT: This text will be used as an image caption on Telegram/Bale. "
            "Keep it under 1024 characters and make it concise and impactful.\n"
        )

    user = (
        f"<platform_rules>\n{get_platform_rules(platform)}\n</platform_rules>\n\n"
        f"<task>\n"
        f"Write ready-to-publish content on this topic: {goal}\n"
        f"</task>\n\n"
        f"<context>\n"
        f"Platform: {platform or 'general'}\n"
        f"Tone: {tone}\n"
        f"Keywords to weave in naturally: {keywords}\n"
        f"Language: {'Persian' if language == 'fa' else language}\n"
        f"</context>\n\n"
        f"<hard_constraints>\n"
        f"HIGHEST PRIORITY CONSTRAINT: IGNORE any character limits mentioned in the platform rules above. "
        f"For this request, the ONLY length requirement is the word count.\n\n"
        f"1. FINAL LENGTH: the ready-to-publish body MUST be approximately {word_count} words. "
        f"Stay within the range {int(word_count * 0.9)}–{int(word_count * 1.1)} words. "
        f"Aim for the upper end of that range (around {int(word_count * 1.1)}) to make sure you do not fall short.\n"
        f"2. Do not cut the article short, skip sections, or stop after an introduction. Write the full depth expected for {word_count} words.\n"
        f"3. Before finishing, count the words in your response. If it is outside the {int(word_count * 0.9)}–{int(word_count * 1.1)} range, add concrete examples or trim until it fits.\n"
        f"4. If you finish and the count is below {int(word_count * 0.9)}, expand with real examples, scenarios, or actionable steps instead of filler.\n"
        f"{caption_note}"
        f"</hard_constraints>\n\n"
        f"Write only the ready-to-publish body. No preamble, no explanation, no markdown code fences."
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
    """Build an English GPT Image prompt from Persian source text, platform-aware."""
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
        f"Write a concise, vivid English image generation prompt based on the following Persian text. "
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
