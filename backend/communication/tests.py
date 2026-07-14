import io
import json
import smtplib
import zipfile
from datetime import timedelta
from unittest.mock import patch

from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase, override_settings
from django.utils import timezone
from rest_framework.test import APIClient

from users.models import User
from wallet.models import Wallet
from workspaces.models import Workspace, WorkspaceMember

from .models import Campaign, CommunicationProvider, Contact, ContactGroup, MessageTemplate
from .services.campaigns import queue_campaign
from .services.dispatch import process_communication_queue
from .services.imports import read_import_file
from .services.templates import extract_variables, render_template


@override_settings(SHARED_TOKEN_ENCRYPTION_KEY='MDAwMDAwMDAwMDAwMDAwMDAwMDAwMDAwMDAwMDAwMDA=')
class CommunicationTestCase(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(phone_number='09120000001')
        self.other_user = User.objects.create_user(phone_number='09120000002')
        self.workspace = Workspace.objects.create(name='اصلی', owner=self.user)
        WorkspaceMember.objects.create(workspace=self.workspace, user=self.user, role='admin', added_by=self.user)
        self.other_workspace = Workspace.objects.create(name='دیگر', owner=self.other_user)
        WorkspaceMember.objects.create(workspace=self.other_workspace, user=self.other_user, role='admin', added_by=self.other_user)
        self.wallet = Wallet.objects.create(workspace=self.workspace, balance=10000)
        self.client = APIClient()
        self.client.force_authenticate(self.user)
        self.base = f'/api/workspaces/{self.workspace.id}/communication'

    def create_provider(self, provider_key='kavenegar', provider_type='sms'):
        provider = CommunicationProvider(
            workspace=self.workspace, created_by=self.user, provider_key=provider_key,
            type=provider_type, name='Provider', settings={'sender': '1000'},
        )
        provider.set_credentials({'api_key': 'secret-key'} if provider_type == 'sms' else {'username': 'a@example.com', 'password': 'secret'})
        provider.save()
        return provider


class ProviderApiTests(CommunicationTestCase):
    @patch('communication.services.providers.smtplib.SMTP')
    def test_gmail_auth_error_is_actionable(self, smtp):
        smtp.return_value.login.side_effect = smtplib.SMTPAuthenticationError(535, b'bad credentials')
        provider = self.create_provider('gmail_smtp', 'email')
        response = self.client.post(f'{self.base}/providers/{provider.id}/test/')
        self.assertEqual(response.status_code, 400)
        self.assertIn('App Password', response.json()['error'])

    def test_credentials_are_encrypted_and_never_returned(self):
        response = self.client.post(f'{self.base}/providers/', {
            'type': 'sms', 'provider_key': 'kavenegar', 'name': 'کاوه نگار',
            'credentials': {'api_key': 'plain-secret'}, 'settings': {'sender': '1000'},
        }, format='json')
        self.assertEqual(response.status_code, 201)
        body = response.json()['data']
        self.assertNotIn('credentials', body)
        provider = CommunicationProvider.objects.get(id=body['id'])
        self.assertNotIn('plain-secret', provider.encrypted_credentials)
        self.assertEqual(provider.get_credentials()['api_key'], 'plain-secret')

    @patch('communication.services.providers.KavenegarSmsProvider.test_connection', return_value={'account': True})
    def test_provider_connection(self, mocked_test):
        provider = self.create_provider()
        response = self.client.post(f'{self.base}/providers/{provider.id}/test/')
        self.assertEqual(response.status_code, 200)
        provider.refresh_from_db()
        self.assertEqual(provider.last_test_status, 'connected')

    def test_workspace_isolation(self):
        foreign = CommunicationProvider(workspace=self.other_workspace, created_by=self.other_user, type='sms', provider_key='kavenegar', name='private')
        foreign.set_credentials({'api_key': 'private'}); foreign.save()
        response = self.client.get(f'{self.base}/providers/')
        self.assertEqual(response.json()['data'], [])

    @patch('communication.services.providers.SmtpEmailProvider.test_connection', return_value={'smtp_code': 250})
    def test_gmail_smtp_save_and_connection(self, mocked_test):
        response = self.client.post(f'{self.base}/providers/', {
            'type': 'email', 'provider_key': 'gmail_smtp', 'name': 'Gmail',
            'credentials': {'username': 'owner@example.com', 'password': 'app-password'},
            'settings': {'host': 'smtp.gmail.com', 'port': 587, 'encryption': 'tls', 'email': 'owner@example.com'},
        }, format='json')
        self.assertEqual(response.status_code, 201)
        provider_id = response.json()['data']['id']
        tested = self.client.post(f'{self.base}/providers/{provider_id}/test/')
        self.assertEqual(tested.status_code, 200)
        self.assertNotIn('app-password', json.dumps(tested.json()))


class ContactAndTemplateTests(CommunicationTestCase):
    def test_contact_validation_and_duplicate_detection(self):
        first = self.client.post(f'{self.base}/contacts/', {'name': 'علی', 'phone': '09121234567'}, format='json')
        self.assertEqual(first.status_code, 201)
        self.assertEqual(first.json()['data']['phone'], '+989121234567')
        duplicate = self.client.post(f'{self.base}/contacts/', {'name': 'تکراری', 'phone': '09121234567'}, format='json')
        self.assertEqual(duplicate.status_code, 400)

    def test_groups_and_template_render(self):
        contact = Contact.objects.create(workspace=self.workspace, created_by=self.user, name='علی', phone='+989121234567', company='ابر', custom_fields={'code': 'OFF30'})
        group = ContactGroup.objects.create(workspace=self.workspace, created_by=self.user, name='VIP')
        group.contacts.add(contact)
        rendered = render_template('سلام {{name}}، کد {{code}} برای {{company}}', contact)
        self.assertEqual(rendered, 'سلام علی، کد OFF30 برای ابر')
        self.assertEqual(extract_variables('سلام {{ name }} {{code}}'), ['code', 'name'])


class ImportTests(CommunicationTestCase):
    def test_csv_preview_and_confirm(self):
        csv_file = SimpleUploadedFile('contacts.csv', 'name,phone,email\nعلی,09121234567,a@example.com\nبد,,bad\n'.encode('utf-8'), content_type='text/csv')
        response = self.client.post(f'{self.base}/contacts/import/preview/', {'file': csv_file}, format='multipart')
        self.assertEqual(response.status_code, 201)
        data = response.json()['data']
        self.assertEqual(data['total_rows'], 2)
        remapped = self.client.post(
            f"{self.base}/contacts/import/{data['id']}/preview/",
            {'mapping': {'name': 'name', 'phone': 'phone', 'email': 'email'}}, format='json',
        )
        self.assertEqual(remapped.status_code, 200)
        confirmed = self.client.post(f"{self.base}/contacts/import/{data['id']}/confirm/", {}, format='json')
        self.assertEqual(confirmed.status_code, 200)
        self.assertEqual(confirmed.json()['data']['created'], 1)

    def test_xlsx_standard_library_parser(self):
        sheet = '''<?xml version="1.0" encoding="UTF-8"?><worksheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main"><sheetData>
        <row r="1"><c r="A1" t="inlineStr"><is><t>name</t></is></c><c r="B1" t="inlineStr"><is><t>phone</t></is></c></row>
        <row r="2"><c r="A2" t="inlineStr"><is><t>سارا</t></is></c><c r="B2" t="inlineStr"><is><t>09121111111</t></is></c></row>
        </sheetData></worksheet>'''
        stream = io.BytesIO()
        with zipfile.ZipFile(stream, 'w') as archive:
            archive.writestr('xl/worksheets/sheet1.xml', sheet)
        stream.seek(0)
        rows = read_import_file(stream, 'xlsx')
        self.assertEqual(rows, [{'name': 'سارا', 'phone': '09121111111'}])


class CampaignTests(CommunicationTestCase):
    @patch('communication.services.providers.KavenegarSmsProvider.send_single')
    def test_scheduled_campaign_is_queued_when_due(self, send):
        send.return_value = {'message_id': 'scheduled-1', 'response': {}}
        provider = self.create_provider()
        contact = Contact.objects.create(
            workspace=self.workspace, created_by=self.user, name='سارا', phone='+989121234567',
        )
        campaign = Campaign.objects.create(
            workspace=self.workspace, created_by=self.user, provider=provider,
            channel='sms', name='زمان‌بندی', body='سلام {{name}}',
        )
        campaign.selected_contacts.add(contact)
        scheduled = timezone.now() + timedelta(hours=1)
        response = self.client.post(
            f'{self.base}/campaigns/{campaign.id}/schedule/',
            {'scheduled_at': scheduled.isoformat()}, format='json',
        )
        self.assertEqual(response.status_code, 200)
        campaign.refresh_from_db()
        self.assertEqual(campaign.status, 'scheduled')
        campaign.scheduled_at = timezone.now() - timedelta(seconds=1)
        campaign.save(update_fields=['scheduled_at'])
        process_communication_queue()
        campaign.refresh_from_db()
        self.assertEqual(campaign.status, 'sent')

    @patch('communication.services.providers.KavenegarSmsProvider.send_single')
    def test_campaign_queue_logs_and_no_wallet_deduction(self, send):
        send.return_value = {'message_id': '123', 'response': {'status': 1}}
        provider = self.create_provider()
        contact = Contact.objects.create(workspace=self.workspace, created_by=self.user, name='علی', phone='+989121234567')
        campaign = Campaign.objects.create(workspace=self.workspace, created_by=self.user, provider=provider, channel='sms', name='فروش', body='سلام {{name}}')
        campaign.selected_contacts.add(contact)
        balance = self.wallet.balance
        self.assertEqual(queue_campaign(campaign), 1)
        process_communication_queue()
        campaign.refresh_from_db(); self.wallet.refresh_from_db()
        self.assertEqual(campaign.status, 'sent')
        self.assertEqual(campaign.messages.get().rendered_body, 'سلام علی')
        self.assertEqual(self.wallet.balance, balance)

    def test_invalid_contact_does_not_stop_campaign_creation(self):
        provider = self.create_provider()
        valid = Contact.objects.create(workspace=self.workspace, created_by=self.user, name='Valid', phone='+989121234567')
        invalid = Contact.objects.create(workspace=self.workspace, created_by=self.user, name='No phone', email='x@example.com')
        campaign = Campaign.objects.create(workspace=self.workspace, created_by=self.user, provider=provider, channel='sms', name='Test', body='Hi')
        campaign.selected_contacts.add(valid, invalid)
        queue_campaign(campaign); campaign.refresh_from_db()
        self.assertEqual(campaign.valid_recipients_count, 1)
        self.assertEqual(campaign.invalid_recipients_count, 1)

    @patch('communication.services.providers.SmtpEmailProvider.send_single')
    def test_email_test_send_is_logged_without_wallet_charge(self, send):
        send.return_value = {'message_id': 'email-1', 'response': {'accepted': True}}
        provider = self.create_provider('gmail_smtp', 'email')
        campaign = Campaign.objects.create(
            workspace=self.workspace, created_by=self.user, provider=provider, channel='email',
            name='Email', subject='سلام {{name}}', body='متن',
        )
        before = self.wallet.balance
        response = self.client.post(f'{self.base}/campaigns/{campaign.id}/send-test/', {'recipient': 'test@example.com'}, format='json')
        self.assertEqual(response.status_code, 200)
        self.wallet.refresh_from_db()
        self.assertEqual(self.wallet.balance, before)
        self.assertTrue(campaign.messages.get().is_test)


class CommunicationAiTests(CommunicationTestCase):
    @patch('communication.views.openai_client._call_chat')
    def test_ai_generation_is_the_only_wallet_charged_action(self, call):
        call.return_value = ('{"variants":[{"title":"کوتاه","body":"سلام"}]}', None, 42)
        before = self.wallet.balance
        response = self.client.post(f'{self.base}/ai/sms-generate/', {'prompt': 'پیام تخفیف'}, format='json')
        self.assertEqual(response.status_code, 200)
        self.wallet.refresh_from_db()
        self.assertEqual(before - self.wallet.balance, response.json()['data']['cost'])
        self.assertEqual(self.wallet.transactions.filter(type='deduct').count(), 1)
