import os
import urllib.parse
import requests
from django.conf import settings

from . import prompts


default_chat_model = 'gpt-4.1-mini'


def get_openai_client():
    try:
        import openai
        client = openai.OpenAI(api_key=settings.OPENAI_API_KEY)
        return client
    except Exception:
        return None


def _call_chat(system_prompt, user_prompt, model=None, response_format=None, max_retries=1):
    """Thin wrapper around chat.completions.create with retry."""
    client = get_openai_client()
    if not client or not settings.OPENAI_API_KEY:
        return None, 'کلید API هوش مصنوعی تنظیم نشده است', 0

    model = model or default_chat_model
    messages = [
        {'role': 'system', 'content': system_prompt},
        {'role': 'user', 'content': user_prompt}
    ]

    last_error = None
    total_tokens = 0
    for attempt in range(max_retries):
        try:
            kwargs = {'model': model, 'messages': messages}
            if response_format:
                kwargs['response_format'] = response_format
            response = client.chat.completions.create(**kwargs)
            text = response.choices[0].message.content
            total_tokens += response.usage.total_tokens or 0
            return text, None, total_tokens
        except Exception as e:
            last_error = str(e)

    return None, last_error or 'تولید محتوا با خطا مواجه شد. لطفاً دوباره تلاش کنید.', total_tokens


def generate_text(goal, platform='', tone='حرفه‌ای', keywords='', language='fa', word_count=300, is_caption=False):
    system_prompt, user_prompt = prompts.build_text_prompt(
        goal=goal, platform=platform, tone=tone, keywords=keywords, language=language, word_count=word_count, is_caption=is_caption
    )
    text, error, tokens = _call_chat(system_prompt, user_prompt)
    return text, error, tokens


def rewrite_text(text, tone='حرفه‌ای', platform=''):
    system_prompt, user_prompt = prompts.build_rewrite_prompt(text, tone, platform)
    result, error, tokens = _call_chat(system_prompt, user_prompt)
    return result, error, tokens


def suggest_titles(topic, count=5, platform=''):
    system_prompt, user_prompt = prompts.build_titles_prompt(topic, count, platform)
    text, error, tokens = _call_chat(system_prompt, user_prompt)
    if error:
        return None, error, tokens
    titles = [t.strip().lstrip('0123456789.-) ') for t in text.strip().split('\n') if t.strip()][:count]
    return titles, None, tokens


def suggest_hashtags(topic, count=10, platform=''):
    system_prompt, user_prompt = prompts.build_hashtags_prompt(topic, count, platform)
    text, error, tokens = _call_chat(system_prompt, user_prompt)
    if error:
        return None, error, tokens
    hashtags = [t.strip() for t in text.strip().split('\n') if t.strip()][:count]
    return hashtags, None, tokens


def generate_cta(goal, platform='', count=3):
    system_prompt, user_prompt = prompts.build_cta_prompt(goal, platform, count)
    text, error, tokens = _call_chat(system_prompt, user_prompt)
    if error:
        return None, error, tokens
    ctas = [t.strip().lstrip('0123456789.-) ') for t in text.strip().split('\n') if t.strip()][:count]
    return ctas, None, tokens


def _save_image_from_url(image_url: str) -> str:
    """Download an image URL and save it to MEDIA_ROOT/content/images, returning the relative path."""
    from django.conf import settings as django_settings
    import uuid

    os.makedirs(os.path.join(django_settings.MEDIA_ROOT, 'content/images'), exist_ok=True)
    filename = f'{uuid.uuid4()}.png'
    filepath = os.path.join(django_settings.MEDIA_ROOT, 'content/images', filename)

    img_response = requests.get(image_url, timeout=60)
    img_response.raise_for_status()
    with open(filepath, 'wb') as f:
        f.write(img_response.content)

    return f'content/images/{filename}'


def _generate_with_pollinations(prompt: str, width: int = 1024, height: int = 1024):
    """Generate an image using Pollinations.ai (no API key required). Returns a public image URL."""
    encoded = urllib.parse.quote(prompt)
    url = f'https://image.pollinations.ai/prompt/{encoded}?width={width}&height={height}&nologo=true&seed=42&enhance=true'
    # Pollinations streams the image; do a quick HEAD/GET to confirm it works.
    test_resp = requests.get(url, timeout=60)
    test_resp.raise_for_status()
    if not test_resp.headers.get('content-type', '').startswith('image'):
        raise Exception('Pollinations response was not an image')
    return url


def generate_image(description, style='', platform=''):
    """Generate an image. Try DALL-E 3 first; fall back to Pollinations.ai if OpenAI image models are unavailable."""
    client = get_openai_client()
    if not client or not settings.OPENAI_API_KEY:
        return None, 'کلید API هوش مصنوعی تنظیم نشده است'

    prompt = prompts.build_image_prompt_enhancement(description, platform)
    if style:
        prompt += f', style: {style}'

    # Try OpenAI DALL-E 3 first.
    openai_error = None
    try:
        response = client.images.generate(
            model='dall-e-3',
            prompt=prompt,
            size='1024x1024',
            quality='standard',
            n=1
        )
        image_url = response.data[0].url
        relative_path = _save_image_from_url(image_url)
        return relative_path, None
    except Exception as e:
        openai_error = str(e)

    # Fallback: Pollinations.ai (free, no API key).
    try:
        image_url = _generate_with_pollinations(prompt, width=1024, height=1024)
        relative_path = _save_image_from_url(image_url)
        return relative_path, None
    except Exception as e:
        return None, f'OpenAI: {openai_error} | Pollinations: {str(e)}'


def generate_image_prompt(source_text, max_words=25, platform=''):
    """Ask the mini model to write a short English DALL-E prompt from the given Persian text."""
    system_prompt = (
        'You are an expert image prompt engineer. Based on the text provided, '
        'write a concise, vivid English image generation prompt suitable for DALL-E 3. '
        'Return only the prompt, no extra explanation.'
    )
    user_prompt = prompts.build_image_prompt_from_text(source_text, platform, max_words)
    prompt, error, tokens = _call_chat(system_prompt, user_prompt)
    if prompt:
        prompt = prompt.strip()
    return prompt, error, tokens


def generate_image_from_text(source_text, style='', platform=''):
    """Two-step image generation: create a DALL-E prompt from text, then generate image."""
    prompt, error, _ = generate_image_prompt(source_text, platform=platform)
    if error:
        return None, error
    return generate_image(prompt, style=style, platform=platform)


def generate_summary(text, length='brief', platform=''):
    system_prompt, user_prompt = prompts.build_summary_prompt(text, length)
    if platform:
        # Summaries are usually platform-agnostic, but if the caller provides a platform we can
        # add a light hint that the summary may be used as caption/copy for that platform.
        user_prompt = f"{prompts.get_platform_rules(platform)}\n\n{user_prompt}"
    result, error, tokens = _call_chat(system_prompt, user_prompt)
    return result, error, tokens


def generate_scenario(topic, platform='', goal=''):
    system_prompt, user_prompt = prompts.build_scenario_prompt(topic, platform, goal)
    result, error, tokens = _call_chat(system_prompt, user_prompt)
    return result, error, tokens


def generate_idea(niche, platform='', count=5):
    system_prompt, user_prompt = prompts.build_idea_prompt(niche, platform, count)
    text, error, tokens = _call_chat(system_prompt, user_prompt)
    if error:
        return None, error, tokens
    ideas = [t.strip().lstrip('0123456789.-) ') for t in text.strip().split('\n') if t.strip()][:count]
    return ideas, None, tokens


def chat_completion(messages, platform=''):
    client = get_openai_client()
    if not client or not settings.OPENAI_API_KEY:
        return None, 'کلید API هوش مصنوعی تنظیم نشده است', 0

    # Only inject a platform-aware system prompt if the caller did not already provide one.
    # This preserves any custom system behavior callers rely on.
    has_system = any(m.get('role') == 'system' for m in messages)
    if has_system:
        full_messages = messages
    else:
        full_messages = [{'role': 'system', 'content': prompts.build_chat_system_prompt()}] + messages

    try:
        response = client.chat.completions.create(
            model=default_chat_model,
            messages=full_messages
        )
        text = response.choices[0].message.content
        tokens = response.usage.total_tokens
        return text, None, tokens
    except Exception as e:
        return None, str(e), 0


import json
import re


def _clean_json_response(text):
    """Extract JSON from markdown code fences if present."""
    text = text.strip()
    if text.startswith('```'):
        text = text.strip('`').strip()
        if text.lower().startswith('json'):
            text = text[4:].strip()
    return text


def _parse_json(text):
    text = _clean_json_response(text)
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        return None


def _call_openai_with_retry(system_prompt, user_prompt, response_format=None, max_retries=3, validate=None):
    """Call OpenAI with retry. validate(text) should return parsed object on success or None on failure."""
    client = get_openai_client()
    if not client or not settings.OPENAI_API_KEY:
        return None, 'کلید API هوش مصنوعی تنظیم نشده است', 0

    messages = [
        {'role': 'system', 'content': system_prompt},
        {'role': 'user', 'content': user_prompt}
    ]

    last_error = None
    total_tokens = 0
    for attempt in range(max_retries):
        try:
            kwargs = {'model': default_chat_model, 'messages': messages}
            if response_format:
                kwargs['response_format'] = response_format
            response = client.chat.completions.create(**kwargs)
            text = response.choices[0].message.content
            total_tokens += response.usage.total_tokens or 0

            if validate:
                parsed = validate(text)
                if parsed is not None:
                    return parsed, None, total_tokens
                last_error = 'تولید محتوا با خطا مواجه شد. لطفاً دوباره تلاش کنید.'
                continue
            return text, None, total_tokens
        except Exception as e:
            last_error = str(e)

    return None, last_error or 'تولید محتوا با خطا مواجه شد. لطفاً دوباره تلاش کنید.', total_tokens


def _validate_bundle(text):
    data = _parse_json(text)
    if not data or not all(k in data for k in ('full_text', 'short_text', 'hashtags', 'title')):
        return None
    if not isinstance(data['hashtags'], list):
        data['hashtags'] = [str(data['hashtags'])]
    return data


def generate_bundle(topic, platform='', tone='حرفه‌ای'):
    """Generate full text, short text, hashtags and title in one OpenAI call."""
    system_prompt, user_prompt = prompts.build_bundle_prompt(topic, platform, tone)
    data, error, tokens = _call_openai_with_retry(
        system_prompt, user_prompt, response_format={'type': 'json_object'}, max_retries=3, validate=_validate_bundle
    )
    return data, error, tokens


def _validate_variants(count):
    def validator(text):
        data = _parse_json(text)
        if not data or not isinstance(data.get('variants'), list) or len(data['variants']) < count:
            return None
        return data['variants'][:count]
    return validator


def generate_variants(capability, params, count=2):
    """Generate N variants for a given capability in one OpenAI call."""
    system_prompt, user_prompt = prompts.build_variants_prompt(capability, params, count)

    variants, error, tokens = _call_openai_with_retry(
        system_prompt, user_prompt, response_format={'type': 'json_object'}, max_retries=3, validate=_validate_variants(count)
    )
    return variants, error, tokens
