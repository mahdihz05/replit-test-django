from types import SimpleNamespace
from unittest.mock import patch

from datetime import timedelta

from django.test import SimpleTestCase, TestCase, override_settings
from django.utils import timezone

from channels_app.models import PublishChannel
from content.models import Content
from users.models import User
from workspaces.models import Workspace

from .models import PublishJob
from .scheduler import process_publish_queue

from .publishers import bale, linkedin, telegram, wordpress


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


    @patch('publishing.publishers.linkedin.requests.post')
    @patch('publishing.publishers.linkedin.decrypt_token', return_value='access-token')
    @patch('publishing.publishers.linkedin._get_active_connection')
    def test_linkedin_does_not_leak_internal_prompt_in_commentary(
        self, get_connection, _decrypt, post_request
    ):
        get_connection.return_value = SimpleNamespace(
            access_token='encrypted',
            access_token_expires_at=None,
            platform_target='personal',
            person_urn='urn:li:person:test',
            organization_urn='',
        )
        self.channel.workspace = object()
        self.content.image = None
        post_request.return_value = SimpleNamespace(
            ok=True,
            headers={'x-restli-id': 'urn:li:share:1'},
        )

        ok, error_type, post_id = linkedin.publish(self.channel, self.content)

        self.assertTrue(ok)
        self.assertIsNone(error_type)
        self.assertEqual(post_id, 'urn:li:share:1')
        payload = post_request.call_args.kwargs['json']
        self.assertEqual(payload['commentary'], self.content.body)
        self.assertNotIn(self.content.title, payload['commentary'])


class PublishQueueSchedulingTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(phone_number='09120000001')
        self.workspace = Workspace.objects.create(name='Queue test', owner=self.user)
        self.content = Content.objects.create(
            workspace=self.workspace,
            created_by=self.user,
            title='Internal title',
            body='Publishable body',
        )
        self.channel = PublishChannel.objects.create(
            workspace=self.workspace,
            platform='website',
            channel_type='site',
            name='Test channel',
            external_id='test-channel',
            is_verified=True,
        )

    @patch('publishing.scheduler.attempt_publish', return_value=(True, None, 'message-id'))
    def test_queue_processes_due_retry_but_skips_future_retry(self, attempt_publish):
        now = timezone.now()
        due_job = PublishJob.objects.create(
            content=self.content,
            channel=self.channel,
            scheduled_at=now - timedelta(minutes=5),
            next_retry_at=now - timedelta(seconds=1),
        )
        future_job = PublishJob.objects.create(
            content=self.content,
            channel=self.channel,
            scheduled_at=now - timedelta(minutes=5),
            next_retry_at=now + timedelta(hours=1),
        )

        process_publish_queue()

        due_job.refresh_from_db()
        future_job.refresh_from_db()
        self.assertEqual(due_job.status, 'success')
        self.assertEqual(future_job.status, 'queued')
        attempt_publish.assert_called_once()


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
                'title': 'عنوان اختصاصی وردپرس',
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
        self.assertEqual(request.kwargs['json']['title'], 'عنوان اختصاصی وردپرس')
        self.assertEqual(request.kwargs['json']['project_categories'], [7])
        self.assertEqual(request.kwargs['json']['excerpt'], 'خلاصه')
        self.assertEqual(request.kwargs['json']['slug'], 'sample-project')

    def test_rejects_type_not_present_in_discovered_capabilities(self):
        options, error = wordpress.validate_publish_options(self.connection, {'post_type': 'product'})

        self.assertIsNone(options)
        self.assertTrue(error)

    @patch('publishing.publishers.wordpress.safe_get')
    def test_rest_get_falls_back_and_preserves_query_parameters(self, safe_get):
        safe_get.side_effect = [
            SimpleNamespace(ok=False, status_code=404),
            SimpleNamespace(ok=True, status_code=200),
        ]

        response = wordpress._rest_get(
            self.connection,
            'wp/v2/types',
            params={'context': 'edit'},
            timeout=20,
        )

        self.assertTrue(response.ok)
        fallback = safe_get.call_args_list[1]
        self.assertEqual(fallback.args[0], 'https://example.com/')
        self.assertEqual(fallback.kwargs['params'], {
            'context': 'edit',
            'rest_route': '/wp/v2/types',
        })

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

    @patch('publishing.publishers.wordpress.is_safe_url', return_value=True)
    @patch('publishing.publishers.wordpress.safe_get')
    def test_application_password_check_falls_back_to_rest_route_for_hosting_404(
        self, safe_get, _safe_url,
    ):
        safe_get.side_effect = [
            SimpleNamespace(ok=False, status_code=404),
            SimpleNamespace(
                ok=True,
                status_code=200,
                json=lambda: {'authentication': {'application-passwords': {'endpoints': {}}}},
            ),
        ]

        ok, error = wordpress.check_application_passwords('https://example.com')

        self.assertTrue(ok)
        self.assertIsNone(error)
        fallback = safe_get.call_args_list[1]
        self.assertEqual(fallback.args[0], 'https://example.com/')
        self.assertEqual(fallback.kwargs['params']['rest_route'], '/')
