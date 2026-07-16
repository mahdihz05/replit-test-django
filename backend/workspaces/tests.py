from django.test import TestCase, override_settings
from rest_framework.test import APIClient

from users.models import User
from .models import Workspace, WorkspaceMember


@override_settings(SECURE_SSL_REDIRECT=False)
class WorkspaceMemberApiTests(TestCase):
    def setUp(self):
        self.owner = User.objects.create_user('09111111111', full_name='مالک')
        self.manager = User.objects.create_user('09222222222', full_name='مدیر محتوا')
        self.candidate = User.objects.create_user('09333333333', full_name='عضو جدید')
        self.outsider = User.objects.create_user('09444444444')
        self.workspace = Workspace.objects.create(name='تیم اصلی', owner=self.owner)
        self.owner_membership = WorkspaceMember.objects.create(
            workspace=self.workspace,
            user=self.owner,
            role='admin',
            added_by=self.owner,
        )
        self.manager_membership = WorkspaceMember.objects.create(
            workspace=self.workspace,
            user=self.manager,
            role='manager',
            added_by=self.owner,
        )
        self.client = APIClient()
        self.client.force_authenticate(self.owner)
        self.list_url = f'/api/workspaces/{self.workspace.id}/members/'

    def test_workspace_member_can_list_real_members(self):
        self.client.force_authenticate(self.manager)

        response = self.client.get(self.list_url)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data['data']), 2)
        self.assertEqual(response.data['data'][0]['user_phone'], self.owner.phone_number)

    def test_admin_can_add_existing_active_user(self):
        response = self.client.post(
            self.list_url,
            {'phone_number': self.candidate.phone_number, 'role': 'manager'},
            format='json',
        )

        self.assertEqual(response.status_code, 201)
        membership = WorkspaceMember.objects.get(workspace=self.workspace, user=self.candidate)
        self.assertEqual(membership.role, 'manager')
        self.assertEqual(membership.added_by, self.owner)
        self.assertEqual(response.data['data']['user_name'], self.candidate.full_name)

    def test_add_rejects_invalid_unknown_and_duplicate_users(self):
        invalid = self.client.post(self.list_url, {'phone_number': '123', 'role': 'manager'}, format='json')
        unknown = self.client.post(self.list_url, {'phone_number': '09555555555', 'role': 'manager'}, format='json')
        duplicate = self.client.post(
            self.list_url,
            {'phone_number': self.manager.phone_number, 'role': 'admin'},
            format='json',
        )

        self.assertEqual(invalid.status_code, 400)
        self.assertEqual(invalid.data['code'], 'VALIDATION_ERROR')
        self.assertEqual(unknown.status_code, 404)
        self.assertEqual(unknown.data['code'], 'USER_NOT_FOUND')
        self.assertEqual(duplicate.status_code, 400)
        self.assertEqual(duplicate.data['code'], 'ALREADY_MEMBER')

    def test_admin_can_change_member_role(self):
        url = f'{self.list_url}{self.manager_membership.id}/'

        response = self.client.patch(url, {'role': 'admin'}, format='json')

        self.assertEqual(response.status_code, 200)
        self.manager_membership.refresh_from_db()
        self.assertEqual(self.manager_membership.role, 'admin')

    def test_admin_can_delete_member(self):
        url = f'{self.list_url}{self.manager_membership.id}/'

        response = self.client.delete(url)

        self.assertEqual(response.status_code, 200)
        self.assertFalse(WorkspaceMember.objects.filter(id=self.manager_membership.id).exists())

    def test_manager_cannot_add_update_or_delete_members(self):
        self.client.force_authenticate(self.manager)
        detail_url = f'{self.list_url}{self.owner_membership.id}/'

        add_response = self.client.post(
            self.list_url,
            {'phone_number': self.candidate.phone_number, 'role': 'manager'},
            format='json',
        )
        update_response = self.client.patch(detail_url, {'role': 'manager'}, format='json')
        delete_response = self.client.delete(detail_url)

        self.assertEqual(add_response.status_code, 403)
        self.assertEqual(update_response.status_code, 403)
        self.assertEqual(delete_response.status_code, 403)

    def test_owner_membership_is_protected(self):
        url = f'{self.list_url}{self.owner_membership.id}/'

        update_response = self.client.patch(url, {'role': 'manager'}, format='json')
        delete_response = self.client.delete(url)

        self.assertEqual(update_response.status_code, 400)
        self.assertEqual(update_response.data['code'], 'OWNER_MEMBERSHIP_PROTECTED')
        self.assertEqual(delete_response.status_code, 400)
        self.assertTrue(WorkspaceMember.objects.filter(id=self.owner_membership.id).exists())

    def test_member_id_from_another_workspace_cannot_be_modified(self):
        other_workspace = Workspace.objects.create(name='تیم دیگر', owner=self.outsider)
        other_membership = WorkspaceMember.objects.create(
            workspace=other_workspace,
            user=self.outsider,
            role='admin',
            added_by=self.outsider,
        )
        url = f'{self.list_url}{other_membership.id}/'

        response = self.client.patch(url, {'role': 'manager'}, format='json')

        self.assertEqual(response.status_code, 404)
        other_membership.refresh_from_db()
        self.assertEqual(other_membership.role, 'admin')
