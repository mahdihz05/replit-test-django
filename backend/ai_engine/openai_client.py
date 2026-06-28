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
