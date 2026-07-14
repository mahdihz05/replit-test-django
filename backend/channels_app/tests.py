from unittest.mock import Mock, patch
from urllib.parse import parse_qs, urlparse

from django.test import SimpleTestCase, TestCase, override_settings
from rest_framework.test import APIClient

from .views import _validate_telegram_chat
from .models import LinkedInConnection, LinkedInOAuthState, PublishChannel
from users.models import User
from workspaces.models import Workspace, WorkspaceMember


class TelegramChatValidationTests(SimpleTestCase):
    @patch('publishing.publishers.telegram._call')
    def test_accepts_admin_bot_with_post_permission(self, telegram_call):
        telegram_call.side_effect = [
            ({'id': -100123, 'type': 'channel', 'title': 'News'}, None),
            ({'id': 42, 'username': 'content_bot'}, None),
            ({'status': 'administrator', 'can_post_messages': True}, None),
        ]

        chat, error, code = _validate_telegram_chat('token', '@news', 'channel')

        self.assertEqual(chat['id'], -100123)
        self.assertIsNone(error)
        self.assertIsNone(code)

    @patch('publishing.publishers.telegram._call')
    def test_rejects_bot_that_is_not_admin(self, telegram_call):
        telegram_call.side_effect = [
            ({'id': -100123, 'type': 'channel', 'title': 'News'}, None),
            ({'id': 42, 'username': 'content_bot'}, None),
            ({'status': 'member'}, None),
        ]

        chat, error, code = _validate_telegram_chat('token', '@news', 'channel')

        self.assertIsNone(chat)
        self.assertEqual(code, 'BOT_NOT_ADMIN')
        self.assertTrue(error)

    @patch('publishing.publishers.telegram._call')
    def test_rejects_chat_type_mismatch(self, telegram_call):
        telegram_call.return_value = ({'id': -100123, 'type': 'supergroup'}, None)

        chat, error, code = _validate_telegram_chat('token', '-100123', 'channel')

        self.assertIsNone(chat)
        self.assertEqual(code, 'CHAT_TYPE_MISMATCH')
        self.assertTrue(error)


@override_settings(
    LINKEDIN_CLIENT_ID='test-client',
    LINKEDIN_CLIENT_SECRET='test-secret',
    LINKEDIN_REDIRECT_URI='http://testserver/api/auth/linkedin/callback/',
    LINKEDIN_TOKEN_ENCRYPTION_KEY='MDAwMDAwMDAwMDAwMDAwMDAwMDAwMDAwMDAwMDAwMDA=',
    CORS_ALLOWED_ORIGINS=['http://testserver'],
)
class LinkedInOAuthTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(phone_number='09120000001')
        self.workspace = Workspace.objects.create(name='Test', owner=self.user)
        WorkspaceMember.objects.create(
            workspace=self.workspace, user=self.user, role='admin', added_by=self.user,
        )
        self.client = APIClient()
        self.client.force_authenticate(self.user)

    def _start(self):
        return self.client.post(
            f'/api/workspaces/{self.workspace.id}/linkedin/connect/start/',
            {'platform_target': 'personal', 'origin': 'http://testserver'},
            format='json',
            HTTP_ORIGIN='http://testserver',
        )

    def test_start_persists_only_hashed_one_time_state(self):
        response = self._start()

        self.assertEqual(response.status_code, 200)
        authorization_url = response.json()['data']['authorization_url']
        state = parse_qs(urlparse(authorization_url).query)['state'][0]
        oauth_state = LinkedInOAuthState.objects.get()

        self.assertNotEqual(oauth_state.state_hash, state)
        self.assertEqual(len(oauth_state.state_hash), 64)
        self.assertNotIn('state', response.json()['data'])
        self.assertIn('w_member_social', authorization_url)
        self.assertIn('email', authorization_url)

    @patch('channels_app.views.requests.get')
    @patch('channels_app.views.requests.post')
    def test_callback_consumes_state_and_encrypts_tokens(self, post_request, get_request):
        start_response = self._start()
        authorization_url = start_response.json()['data']['authorization_url']
        state = parse_qs(urlparse(authorization_url).query)['state'][0]

        post_request.return_value = Mock(
            ok=True,
            status_code=200,
            json=lambda: {
                'access_token': 'plain-access-token',
                'refresh_token': 'plain-refresh-token',
                'expires_in': 3600,
                'refresh_token_expires_in': 7200,
                'scope': 'openid profile email w_member_social',
            },
        )
        get_request.return_value = Mock(
            ok=True,
            status_code=200,
            json=lambda: {
                'sub': 'member-123',
                'name': 'Test Member',
                'email': 'member@example.com',
                'picture': 'https://example.com/avatar.jpg',
            },
        )

        response = self.client.get(
            '/api/auth/linkedin/callback/',
            {'code': 'authorization-code', 'state': state},
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response['Content-Type'], 'text/html; charset=utf-8')
        connection = LinkedInConnection.objects.get()
        self.assertNotIn('plain-access-token', connection.access_token)
        self.assertEqual(connection.linkedin_subject_id, 'member-123')
        self.assertEqual(connection.person_urn, 'urn:li:person:member-123')
        self.assertTrue(PublishChannel.objects.filter(platform='linkedin', is_verified=True).exists())
        self.assertIsNotNone(LinkedInOAuthState.objects.get().consumed_at)

        replay = self.client.get(
            '/api/auth/linkedin/callback/',
            {'code': 'authorization-code', 'state': state},
        )
        self.assertContains(replay, 'SESSION_EXPIRED')
        self.assertEqual(post_request.call_count, 1)
