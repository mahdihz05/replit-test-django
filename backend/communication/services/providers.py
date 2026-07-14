import smtplib
import ssl
from abc import ABC, abstractmethod
from email.message import EmailMessage

import requests


class ProviderError(Exception):
    pass


class BaseProvider(ABC):
    def __init__(self, provider):
        self.provider = provider
        self.credentials = provider.get_credentials()
        self.settings = provider.settings or {}

    @abstractmethod
    def test_connection(self): ...

    @abstractmethod
    def send_single(self, **kwargs): ...

    def send_batch(self, messages):
        results = []
        for message in messages:
            try:
                results.append({'ok': True, **self.send_single(**message)})
            except Exception as exc:
                results.append({'ok': False, 'error': str(exc)})
        return results


class KavenegarSmsProvider(BaseProvider):
    API_ROOT = 'https://api.kavenegar.com/v1/{api_key}'

    def _call(self, scope, method, payload=None):
        api_key = self.credentials.get('api_key', '')
        if not api_key:
            raise ProviderError('API Key کاوه‌نگار تنظیم نشده است')
        url = f"{self.API_ROOT.format(api_key=api_key)}/{scope}/{method}.json"
        session = requests.Session()
        session.trust_env = False
        try:
            response = session.post(url, data=payload or {}, timeout=20)
            data = response.json()
        except (requests.RequestException, ValueError) as exc:
            raise ProviderError(f'خطا در اتصال به کاوه‌نگار: {exc}') from exc
        finally:
            session.close()
        result = data.get('return', {})
        if response.status_code >= 400 or result.get('status') != 200:
            raise ProviderError(result.get('message') or 'پاسخ نامعتبر از کاوه‌نگار')
        return data.get('entries')

    def test_connection(self):
        entries = self._call('account', 'info')
        return {'account': bool(entries)}

    def send_single(self, to, message, **options):
        payload = {'receptor': to, 'message': message}
        sender = options.get('sender') or self.settings.get('sender')
        if sender:
            payload['sender'] = sender
        entries = self._call('sms', 'send', payload)
        entry = entries[0] if isinstance(entries, list) and entries else entries or {}
        return {
            'message_id': str(entry.get('messageid', '')),
            'response': {
                'status': entry.get('status'),
                'status_text': entry.get('statustext'),
                'cost_rial': entry.get('cost'),
            },
        }

    def get_status(self, message_id):
        entries = self._call('sms', 'status', {'messageid': message_id})
        return entries[0] if isinstance(entries, list) and entries else entries


class SmtpEmailProvider(BaseProvider):
    def _connection(self):
        host = self.settings.get('host', 'smtp.gmail.com')
        port = int(self.settings.get('port', 587))
        encryption = self.settings.get('encryption', 'tls')
        timeout = 20
        server = None
        try:
            if encryption == 'ssl':
                server = smtplib.SMTP_SSL(host, port, timeout=timeout, context=ssl.create_default_context())
            else:
                server = smtplib.SMTP(host, port, timeout=timeout)
                server.ehlo()
                if encryption == 'tls':
                    server.starttls(context=ssl.create_default_context())
                    server.ehlo()
            username = self.credentials.get('username') or self.settings.get('email')
            password = self.credentials.get('password')
            if username and password:
                server.login(username, password)
            return server
        except smtplib.SMTPAuthenticationError as exc:
            if server:
                try: server.close()
                except Exception: pass
            raise ProviderError(
                'ورود به Gmail ناموفق بود. آدرس Gmail و App Password شانزده‌رقمی را بررسی کنید؛ رمز معمولی Gmail قابل استفاده نیست.'
            ) from exc
        except (smtplib.SMTPException, OSError) as exc:
            if server:
                try: server.close()
                except Exception: pass
            raise ProviderError(f'اتصال به سرویس ایمیل برقرار نشد: {exc}') from exc

    def test_connection(self):
        server = self._connection()
        try:
            code, _ = server.noop()
            return {'smtp_code': code}
        finally:
            server.quit()

    def send_single(self, to, subject, body, body_type='plain_text', **options):
        msg = EmailMessage()
        from_email = self.settings.get('from_email') or self.settings.get('email') or self.credentials.get('username')
        from_name = self.settings.get('from_name', '')
        msg['From'] = f'{from_name} <{from_email}>' if from_name else from_email
        msg['To'] = to
        msg['Subject'] = subject
        if body_type == 'html':
            msg.set_content('برای مشاهده این ایمیل از نمایشگر HTML استفاده کنید.')
            msg.add_alternative(body, subtype='html')
        else:
            msg.set_content(body)
        server = self._connection()
        try:
            refused = server.send_message(msg)
        finally:
            server.quit()
        if refused:
            raise ProviderError('SMTP گیرنده را نپذیرفت')
        return {'message_id': msg.get('Message-ID', ''), 'response': {'accepted': True}}


class ProviderManager:
    PROVIDERS = {
        'kavenegar': KavenegarSmsProvider,
        'gmail_smtp': SmtpEmailProvider,
        'custom_smtp': SmtpEmailProvider,
    }

    @classmethod
    def get(cls, provider):
        provider_class = cls.PROVIDERS.get(provider.provider_key)
        if not provider_class:
            raise ProviderError('Provider پشتیبانی نمی‌شود')
        if provider.status != 'active':
            raise ProviderError('Provider غیرفعال است')
        return provider_class(provider)
