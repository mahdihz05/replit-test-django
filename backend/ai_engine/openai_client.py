import os
import requests
from django.conf import settings


def get_openai_client():
    try:
        import openai
        client = openai.OpenAI(api_key=settings.OPENAI_API_KEY)
        return client
    except Exception:
        return None


def generate_text(goal, platform='', tone='حرفه‌ای', keywords='', language='fa', word_count=300):
    client = get_openai_client()
    if not client or not settings.OPENAI_API_KEY:
        return None, 'کلید API هوش مصنوعی تنظیم نشده است', 0

    system_prompt = 'You are an expert Persian content creator for social media.'
    user_prompt = f"""محتوا بنویس با این مشخصات:
هدف: {goal}
پلتفرم: {platform}
لحن: {tone}
کلمات کلیدی: {keywords}
زبان: {'فارسی' if language == 'fa' else language}
تعداد کلمات تقریبی: {word_count}

فقط متن محتوا را بنویس بدون توضیحات اضافه."""

    try:
        response = client.chat.completions.create(
            model='gpt-4o',
            messages=[
                {'role': 'system', 'content': system_prompt},
                {'role': 'user', 'content': user_prompt}
            ]
        )
        text = response.choices[0].message.content
        tokens = response.usage.total_tokens
        return text, None, tokens
    except Exception as e:
        return None, str(e), 0


def rewrite_text(text, tone='حرفه‌ای'):
    client = get_openai_client()
    if not client or not settings.OPENAI_API_KEY:
        return None, 'کلید API هوش مصنوعی تنظیم نشده است', 0

    try:
        response = client.chat.completions.create(
            model='gpt-4o',
            messages=[
                {'role': 'system', 'content': 'You are an expert Persian content rewriter.'},
                {'role': 'user', 'content': f'این متن را بازنویسی کن با لحن {tone}:\n\n{text}'}
            ]
        )
        result = response.choices[0].message.content
        tokens = response.usage.total_tokens
        return result, None, tokens
    except Exception as e:
        return None, str(e), 0


def suggest_titles(topic, count=5):
    client = get_openai_client()
    if not client or not settings.OPENAI_API_KEY:
        return None, 'کلید API هوش مصنوعی تنظیم نشده است', 0

    try:
        response = client.chat.completions.create(
            model='gpt-4o',
            messages=[
                {'role': 'system', 'content': 'You are an expert Persian content creator.'},
                {'role': 'user', 'content': f'{count} عنوان جذاب برای این موضوع پیشنهاد بده:\n{topic}\n\nفقط لیست عناوین را بنویس، هر عنوان در یک خط.'}
            ]
        )
        text = response.choices[0].message.content
        titles = [t.strip().lstrip('0123456789.-) ') for t in text.strip().split('\n') if t.strip()][:count]
        tokens = response.usage.total_tokens
        return titles, None, tokens
    except Exception as e:
        return None, str(e), 0


def suggest_hashtags(topic, count=10):
    client = get_openai_client()
    if not client or not settings.OPENAI_API_KEY:
        return None, 'کلید API هوش مصنوعی تنظیم نشده است', 0

    try:
        response = client.chat.completions.create(
            model='gpt-4o',
            messages=[
                {'role': 'system', 'content': 'You are an expert Persian social media specialist.'},
                {'role': 'user', 'content': f'{count} هشتگ مناسب برای این موضوع پیشنهاد بده:\n{topic}\n\nفقط هشتگ‌ها را بنویس، هر کدام در یک خط.'}
            ]
        )
        text = response.choices[0].message.content
        hashtags = [t.strip() for t in text.strip().split('\n') if t.strip()][:count]
        tokens = response.usage.total_tokens
        return hashtags, None, tokens
    except Exception as e:
        return None, str(e), 0


def generate_cta(goal, platform='', count=3):
    client = get_openai_client()
    if not client or not settings.OPENAI_API_KEY:
        return None, 'کلید API هوش مصنوعی تنظیم نشده است', 0

    try:
        response = client.chat.completions.create(
            model='gpt-4o',
            messages=[
                {'role': 'system', 'content': 'You are an expert Persian copywriter.'},
                {'role': 'user', 'content': f'{count} call-to-action قوی برای این هدف بنویس:\nهدف: {goal}\nپلتفرم: {platform}\n\nفقط لیست CTAها را بنویس.'}
            ]
        )
        text = response.choices[0].message.content
        ctas = [t.strip().lstrip('0123456789.-) ') for t in text.strip().split('\n') if t.strip()][:count]
        tokens = response.usage.total_tokens
        return ctas, None, tokens
    except Exception as e:
        return None, str(e), 0


def generate_image(description, style=''):
    client = get_openai_client()
    if not client or not settings.OPENAI_API_KEY:
        return None, 'کلید API هوش مصنوعی تنظیم نشده است'

    prompt = description
    if style:
        prompt += f', style: {style}'

    try:
        response = client.images.generate(
            model='dall-e-3',
            prompt=prompt,
            size='1024x1024',
            quality='standard',
            n=1
        )
        image_url = response.data[0].url

        import os
        import uuid
        from django.conf import settings as django_settings

        os.makedirs(os.path.join(django_settings.MEDIA_ROOT, 'content/images'), exist_ok=True)
        filename = f'{uuid.uuid4()}.png'
        filepath = os.path.join(django_settings.MEDIA_ROOT, 'content/images', filename)

        img_response = requests.get(image_url, timeout=30)
        with open(filepath, 'wb') as f:
            f.write(img_response.content)

        relative_path = f'content/images/{filename}'
        return relative_path, None
    except Exception as e:
        return None, str(e)


def generate_summary(text, length='brief'):
    client = get_openai_client()
    if not client or not settings.OPENAI_API_KEY:
        return None, 'کلید API هوش مصنوعی تنظیم نشده است', 0
    length_fa = 'کوتاه و فشرده' if length == 'brief' else 'جامع و کامل'
    try:
        response = client.chat.completions.create(
            model='gpt-4o',
            messages=[
                {'role': 'system', 'content': 'You are an expert Persian content summarizer.'},
                {'role': 'user', 'content': f'این متن را به صورت {length_fa} خلاصه کن:\n\n{text}'}
            ]
        )
        result = response.choices[0].message.content
        tokens = response.usage.total_tokens
        return result, None, tokens
    except Exception as e:
        return None, str(e), 0


def generate_scenario(topic, platform='', goal=''):
    client = get_openai_client()
    if not client or not settings.OPENAI_API_KEY:
        return None, 'کلید API هوش مصنوعی تنظیم نشده است', 0
    try:
        response = client.chat.completions.create(
            model='gpt-4o',
            messages=[
                {'role': 'system', 'content': 'You are an expert Persian content strategist and scriptwriter.'},
                {'role': 'user', 'content': f'یک سناریوی محتوایی کامل بنویس:\nموضوع: {topic}\nپلتفرم: {platform}\nهدف: {goal}\n\nشامل: هوک ابتدایی، بدنه اصلی، و call-to-action باشد.'}
            ]
        )
        result = response.choices[0].message.content
        tokens = response.usage.total_tokens
        return result, None, tokens
    except Exception as e:
        return None, str(e), 0


def generate_idea(niche, platform='', count=5):
    client = get_openai_client()
    if not client or not settings.OPENAI_API_KEY:
        return None, 'کلید API هوش مصنوعی تنظیم نشده است', 0
    try:
        response = client.chat.completions.create(
            model='gpt-4o',
            messages=[
                {'role': 'system', 'content': 'You are an expert Persian content idea generator.'},
                {'role': 'user', 'content': f'{count} ایده خلاقانه برای تولید محتوا پیشنهاد بده:\nحوزه: {niche}\nپلتفرم: {platform}\n\nهر ایده را با یک جمله توضیح بده.'}
            ]
        )
        text = response.choices[0].message.content
        ideas = [t.strip().lstrip('0123456789.-) ') for t in text.strip().split('\n') if t.strip()][:count]
        tokens = response.usage.total_tokens
        return ideas, None, tokens
    except Exception as e:
        return None, str(e), 0


def chat_completion(messages):
    client = get_openai_client()
    if not client or not settings.OPENAI_API_KEY:
        return None, 'کلید API هوش مصنوعی تنظیم نشده است', 0

    try:
        response = client.chat.completions.create(
            model='gpt-4o',
            messages=messages
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
            kwargs = {'model': 'gpt-4o', 'messages': messages}
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
    system_prompt = (
        'You are an expert Persian content creator. '
        'Return only a valid JSON object with no Markdown or extra explanation. '
        'The JSON must contain exactly these keys: full_text, short_text, hashtags, title.'
    )
    user_prompt = f"""محتوای جامع برای این موضوع بساز:
موضوع: {topic}
پلتفرم: {platform}
لحن: {tone}

خروجی باید JSON باشد با این ساختار:
{{
  "full_text": "متن کامل و نسبتاً بلند (حداقل ۵۰۰ کاراکتر)",
  "short_text": "نسخه خلاصه و کوتاه مناسب تلگرام/بله، حداکثر ۴۰۰ کاراکتر",
  "hashtags": ["هشتگ۱", "هشتگ۲", "هشتگ۳", "هشتگ۴", "هشتگ۵"],
  "title": "یک عنوان جذاب و کوتاه"
}}

فقط JSON خالص بدون توضیح اضافه برگردان."""

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
    system_prompt = (
        'You are an expert Persian content creator. '
        'Return only a valid JSON object with no Markdown or extra explanation. '
        'The JSON must contain exactly one key: "variants" which is an array of strings.'
    )

    capability_labels = {
        'text': 'تولید متن',
        'rewrite': 'بازنویسی',
        'summary': 'خلاصه‌سازی',
        'scenario': 'سناریو',
        'title': 'پیشنهاد عنوان',
        'hashtag': 'پیشنهاد هشتگ',
        'cta': 'CTA',
        'idea': 'ایده محتوا',
    }
    label = capability_labels.get(capability, 'تولید محتوا')

    topic = params.get('topic', params.get('goal', params.get('niche', params.get('text', ''))))
    tone = params.get('tone', 'حرفه‌ای')
    platform = params.get('platform', '')
    length = params.get('length', 'brief')
    word_count = params.get('word_count', 300)

    capability_prompts = {
        'text': f'با لحن {tone} و برای پلتفرم {platform}، {count} متن متفاوت برای موضوع زیر بنویس. هر نسخه حدود {word_count} کلمه داشته باشد.',
        'rewrite': f'متن زیر را با {count} لحن/زاویه متفاوت بازنویسی کن. لحن پیشنهادی: {tone}.',
        'summary': f'متن زیر را در {count} خلاصه با طول یا زاویه متفاوت خلاصه کن. طول مورد نظر: {length}.',
        'scenario': f'برای موضوع {topic} و پلتفرم {platform} با هدف {params.get("goal", "")}، {count} سناریوی محتوایی متفاوت بنویس.',
        'title': f'{count} عنوان متفاوت برای موضوع {topic} پیشنهاد بده.',
        'hashtag': f'{count} هشتگ متفاوت برای موضوع {topic} و پلتفرم {platform} پیشنهاد بده.',
        'cta': f'{count} CTA متفاوت برای هدف {topic} و پلتفرم {platform} بنویس.',
        'idea': f'{count} ایده متفاوت برای حوزه {topic} و پلتفرم {platform} پیشنهاد بده.',
    }

    body_context = f"\n\nمحتوا/متن/ورودی:\n{topic}" if topic else ''
    user_prompt = f"""{capability_prompts.get(capability, f'{count} نسخه متفاوت برای {label} تولید کن')}

خروجی باید JSON باشد:
{{
  "variants": ["نسخه ۱", "نسخه ۲", "نسخه ۳"]
}}

هر آیتم آرایه یک نسخه کامل و مستقل باشد. فقط JSON خالص بدون توضیح اضافه برگردان.{body_context}"""

    variants, error, tokens = _call_openai_with_retry(
        system_prompt, user_prompt, response_format={'type': 'json_object'}, max_retries=3, validate=_validate_variants(count)
    )
    return variants, error, tokens
