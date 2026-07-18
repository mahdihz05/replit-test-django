from types import SimpleNamespace
from unittest.mock import patch

from django.test import SimpleTestCase, override_settings

from .publishers import bale, telegram, wordpress


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


class WordPressPublisherOptionsTests(SimpleTestCase):
    def setUp(self):
        self.connection = SimpleNamespace(
            site_url='https://example.com',
            wp_username='editor',
            application_password='encrypted',
            capabilities={
                'post_types': [{
                    'slug': 'portfolio',
                    'name': 'Portfolio',
                    'rest_base': 'portfolio',
                    'supports': {'title': True, 'editor': True, 'excerpt': True, 'thumbnail': True},
                    'taxonomies': ['project_category'],
                }],
                'taxonomies': {
                    'project_category': {'rest_base': 'project_categories'},
                },
            },
        )
        self.channel = SimpleNamespace(workspace=object(), external_id='https://example.com')
        self.content = SimpleNamespace(title='نمونه پروژه', body='متن پروژه', image=None, tags=[])

    @patch('publishing.publishers.wordpress.decrypt_token', return_value='application-password')
    @patch('publishing.publishers.wordpress.safe_post')
    @patch('publishing.publishers.wordpress._get_active_connection')
    def test_custom_type_uses_discovered_endpoint_and_defaults_to_draft(self, get_connection, safe_post, _decrypt):
        get_connection.return_value = self.connection
        safe_post.return_value = SimpleNamespace(
            ok=True,
            json=lambda: {'id': 42, 'link': 'https://example.com/portfolio/42', 'status': 'draft'},
        )

        ok, error_type, result = wordpress.publish(
            self.channel,
            self.content,
            options={
                'post_type': 'portfolio',
                'excerpt': 'خلاصه',
                'slug': 'sample-project',
                'taxonomy_terms': {'project_category': [7]},
            },
        )

        self.assertTrue(ok)
        self.assertIsNone(error_type)
        self.assertEqual(result['post_id'], 42)
        request = safe_post.call_args
        self.assertEqual(request.args[0], 'https://example.com/wp-json/wp/v2/portfolio')
        self.assertEqual(request.kwargs['json']['status'], 'draft')
        self.assertEqual(request.kwargs['json']['project_categories'], [7])
        self.assertEqual(request.kwargs['json']['excerpt'], 'خلاصه')
        self.assertEqual(request.kwargs['json']['slug'], 'sample-project')

    def test_rejects_type_not_present_in_discovered_capabilities(self):
        options, error = wordpress.validate_publish_options(self.connection, {'post_type': 'product'})

        self.assertIsNone(options)
        self.assertTrue(error)

    @patch('publishing.publishers.wordpress.decrypt_token', return_value='application-password')
    @patch('publishing.publishers.wordpress.safe_get')
    def test_credential_validation_falls_back_to_rest_route_for_hosting_403(self, safe_get, _decrypt):
        safe_get.side_effect = [
            SimpleNamespace(ok=False, status_code=403, headers={'Content-Type': 'text/html'}),
            SimpleNamespace(ok=True, status_code=200, headers={'Content-Type': 'application/json'}),
        ]

        valid = wordpress.validate_credentials(self.connection)

        self.assertTrue(valid)
        self.assertEqual(safe_get.call_count, 2)
        fallback = safe_get.call_args_list[1]
        self.assertEqual(fallback.args[0], 'https://example.com/')
        self.assertEqual(fallback.kwargs['params']['rest_route'], '/wp/v2/users/me')
