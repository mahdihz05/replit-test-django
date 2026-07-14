from types import SimpleNamespace
from unittest.mock import patch

from django.test import SimpleTestCase, override_settings

from .publishers import bale, telegram


class SocialPublisherBodyTests(SimpleTestCase):
    def setUp(self):
        self.channel = SimpleNamespace(external_id='@test-channel')
        self.content = SimpleNamespace(
            title='درخواست خام کاربر که فقط عنوان داخلی است',
            body='متن نهایی آماده انتشار',
        )

    @override_settings(TELEGRAM_BOT_TOKEN='test-token')
    @patch('publishing.publishers.telegram.send_message')
    def test_telegram_does_not_prepend_internal_title(self, send_message):
        send_message.return_value = ({'message_id': 1}, None)

        ok, error_type, message_id = telegram.publish(self.channel, self.content)

        self.assertTrue(ok)
        self.assertIsNone(error_type)
        self.assertEqual(message_id, 1)
        send_message.assert_called_once_with('test-token', '@test-channel', 'متن نهایی آماده انتشار')

    @override_settings(BALE_BOT_TOKEN='test-token')
    @patch('publishing.publishers.bale.send_message')
    def test_bale_does_not_prepend_internal_title(self, send_message):
        send_message.return_value = ({'message_id': 2}, None)

        ok, error_type, message_id = bale.publish(self.channel, self.content)

        self.assertTrue(ok)
        self.assertIsNone(error_type)
        self.assertEqual(message_id, 2)
        send_message.assert_called_once_with('test-token', '@test-channel', 'متن نهایی آماده انتشار')
