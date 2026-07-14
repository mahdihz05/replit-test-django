import re


VARIABLE_PATTERN = re.compile(r'{{\s*([\w.-]+)\s*}}')
DEFAULT_VARIABLES = ['name', 'phone', 'email', 'company', 'city']
UNSAFE_BLOCK_PATTERN = re.compile(r'<\s*(script|iframe|object|embed)[^>]*>.*?<\s*/\s*\1\s*>', re.IGNORECASE | re.DOTALL)
UNSAFE_EVENT_PATTERN = re.compile(r'\s+on[a-z]+\s*=\s*(["\']).*?\1', re.IGNORECASE | re.DOTALL)
JAVASCRIPT_URL_PATTERN = re.compile(r'javascript\s*:', re.IGNORECASE)


def extract_variables(*values):
    variables = set()
    for value in values:
        variables.update(VARIABLE_PATTERN.findall(value or ''))
    return sorted(variables)


def render_template(value, contact=None, extra=None):
    context = contact.template_context() if contact else {}
    context.update(extra or {})

    def replace(match):
        key = match.group(1)
        current = context
        for part in key.split('.'):
            current = current.get(part, '') if isinstance(current, dict) else ''
        return str(current if current is not None else '')

    return VARIABLE_PATTERN.sub(replace, value or '')


def sanitize_email_html(value):
    value = UNSAFE_BLOCK_PATTERN.sub('', value or '')
    value = UNSAFE_EVENT_PATTERN.sub('', value)
    return JAVASCRIPT_URL_PATTERN.sub('', value)
