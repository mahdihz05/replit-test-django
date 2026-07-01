from datetime import timedelta

from django.test import TestCase
from django.utils import timezone
from rest_framework.test import APIRequestFactory

from users.models import User
from workspaces.models import Workspace, WorkspaceMember
from content.models import Content
from publishing.models import PublishJob
from channels_app.models import PublishChannel
from wallet.models import Wallet
from .views import dashboard_stats


class DashboardStatsTests(TestCase):
    def setUp(self):
        self.factory = APIRequestFactory()
        self.user = User.objects.create_user(
            phone_number='09120000001',
            full_name='Test Admin'
        )
        self.workspace = Workspace.objects.create(
            name='Test Workspace',
            owner=self.user
        )
        WorkspaceMember.objects.create(
            workspace=self.workspace,
            user=self.user,
            role='admin',
            added_by=self.user
        )
        Wallet.objects.create(workspace=self.workspace, balance=1000)
        self.channel = PublishChannel.objects.create(
            workspace=self.workspace,
            platform='telegram',
            name='Test Channel',
            external_id='-1001234567890',
            is_verified=True,
            is_active=True
        )

    def _make_request(self):
        from rest_framework.test import force_authenticate
        request = self.factory.get(f'/api/workspaces/{self.workspace.id}/dashboard/')
        force_authenticate(request, user=self.user)
        return dashboard_stats(request, self.workspace.id)

    def test_counts_successful_publishes_by_completed_at(self):
        today = timezone.now().date()
        yesterday = today - timedelta(days=1)

        content = Content.objects.create(
            workspace=self.workspace,
            created_by=self.user,
            title='Scheduled Content',
            status='published'
        )

        # Job created today but completed yesterday should not count for today.
        job_completed_yesterday = PublishJob.objects.create(
            content=content,
            channel=self.channel,
            status='success',
            created_at=timezone.now()
        )
        job_completed_yesterday.completed_at = timezone.now() - timedelta(days=1)
        job_completed_yesterday.save()

        # Job created and completed today should count for today.
        PublishJob.objects.create(
            content=content,
            channel=self.channel,
            status='success',
            created_at=timezone.now(),
            completed_at=timezone.now()
        )

        response = self._make_request()
        data = response.data['data']

        today_entry = next(item for item in data['publishes']['by_day'] if item['date'] == today.strftime('%m/%d'))
        yesterday_entry = next(item for item in data['publishes']['by_day'] if item['date'] == yesterday.strftime('%m/%d'))

        self.assertEqual(today_entry['count'], 1)
        self.assertEqual(yesterday_entry['count'], 1)
        self.assertEqual(data['publishes']['total'], 2)

    def test_channel_and_content_counts(self):
        Content.objects.create(
            workspace=self.workspace,
            created_by=self.user,
            title='Draft Content',
            status='draft'
        )
        Content.objects.create(
            workspace=self.workspace,
            created_by=self.user,
            title='Published Content',
            status='published'
        )

        response = self._make_request()
        data = response.data['data']

        self.assertEqual(data['contents']['total'], 2)
        self.assertEqual(data['contents']['by_status']['draft'], 1)
        self.assertEqual(data['contents']['by_status']['published'], 1)
        self.assertEqual(data['channels']['total'], 1)
        self.assertEqual(data['channels']['verified'], 1)
        self.assertEqual(data['channels']['by_platform']['telegram'], 1)
        self.assertEqual(data['wallet']['balance'], 1000.0)
