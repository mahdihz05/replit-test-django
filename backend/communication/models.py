import json
import uuid

from django.conf import settings
from django.db import models

from channels_app.crypto import decrypt_token, encrypt_token


class WorkspaceOwnedModel(models.Model):
    workspace = models.ForeignKey('workspaces.Workspace', on_delete=models.CASCADE)
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        abstract = True


class CommunicationProvider(WorkspaceOwnedModel):
    TYPE_CHOICES = [('sms', 'SMS'), ('email', 'Email')]
    KEY_CHOICES = [('kavenegar', 'Kavenegar'), ('gmail_smtp', 'Gmail SMTP'), ('custom_smtp', 'Custom SMTP')]
    STATUS_CHOICES = [('active', 'Active'), ('disabled', 'Disabled')]
    TEST_CHOICES = [('not_tested', 'Not Tested'), ('connected', 'Connected'), ('failed', 'Failed')]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    type = models.CharField(max_length=10, choices=TYPE_CHOICES)
    provider_key = models.CharField(max_length=30, choices=KEY_CHOICES)
    name = models.CharField(max_length=255)
    encrypted_credentials = models.TextField(blank=True)
    settings = models.JSONField(default=dict, blank=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='active')
    last_tested_at = models.DateTimeField(null=True, blank=True)
    last_test_status = models.CharField(max_length=20, choices=TEST_CHOICES, default='not_tested')
    last_test_error = models.CharField(max_length=500, blank=True)

    class Meta:
        db_table = 'communication_provider'
        ordering = ['-created_at']

    def set_credentials(self, value):
        self.encrypted_credentials = encrypt_token(json.dumps(value or {}, ensure_ascii=False))

    def get_credentials(self):
        try:
            return json.loads(decrypt_token(self.encrypted_credentials) or '{}')
        except (TypeError, json.JSONDecodeError):
            return {}


class Contact(WorkspaceOwnedModel):
    STATUS_CHOICES = [('active', 'Active'), ('inactive', 'Inactive')]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=255, blank=True)
    phone = models.CharField(max_length=20, blank=True, db_index=True)
    email = models.EmailField(blank=True, db_index=True)
    company = models.CharField(max_length=255, blank=True)
    city = models.CharField(max_length=100, blank=True)
    tags = models.JSONField(default=list, blank=True)
    custom_fields = models.JSONField(default=dict, blank=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='active')

    class Meta:
        db_table = 'communication_contact'
        ordering = ['-created_at']
        indexes = [models.Index(fields=['workspace', 'status'], name='comm_contact_ws_status')]

    def template_context(self):
        data = {
            'name': self.name, 'phone': self.phone, 'email': self.email,
            'company': self.company, 'city': self.city,
        }
        data.update(self.custom_fields or {})
        return data


class ContactGroup(WorkspaceOwnedModel):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    contacts = models.ManyToManyField(Contact, through='ContactGroupMember', related_name='groups')

    class Meta:
        db_table = 'communication_contact_group'
        ordering = ['name']
        constraints = [models.UniqueConstraint(fields=['workspace', 'name'], name='unique_comm_group_name')]


class ContactGroupMember(models.Model):
    group = models.ForeignKey(ContactGroup, on_delete=models.CASCADE, related_name='memberships')
    contact = models.ForeignKey(Contact, on_delete=models.CASCADE, related_name='group_memberships')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'communication_contact_group_member'
        constraints = [models.UniqueConstraint(fields=['group', 'contact'], name='unique_comm_group_member')]


class MessageTemplate(WorkspaceOwnedModel):
    CHANNEL_CHOICES = [('sms', 'SMS'), ('email', 'Email')]
    BODY_CHOICES = [('plain_text', 'Plain text'), ('html', 'HTML')]
    STATUS_CHOICES = [('active', 'Active'), ('inactive', 'Inactive')]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    channel = models.CharField(max_length=10, choices=CHANNEL_CHOICES)
    title = models.CharField(max_length=255)
    category = models.CharField(max_length=100, blank=True)
    subject = models.CharField(max_length=500, blank=True)
    body = models.TextField()
    body_type = models.CharField(max_length=20, choices=BODY_CHOICES, default='plain_text')
    variables = models.JSONField(default=list, blank=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='active')

    class Meta:
        db_table = 'communication_message_template'
        ordering = ['-created_at']


class Campaign(WorkspaceOwnedModel):
    CHANNEL_CHOICES = MessageTemplate.CHANNEL_CHOICES
    STATUS_CHOICES = [
        ('draft', 'Draft'), ('scheduled', 'Scheduled'), ('queued', 'Queued'), ('sending', 'Sending'),
        ('sent', 'Sent'), ('cancelled', 'Cancelled'), ('failed', 'Failed'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    provider = models.ForeignKey(CommunicationProvider, on_delete=models.PROTECT, related_name='campaigns')
    channel = models.CharField(max_length=10, choices=CHANNEL_CHOICES)
    name = models.CharField(max_length=255)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='draft', db_index=True)
    template = models.ForeignKey(MessageTemplate, on_delete=models.SET_NULL, null=True, blank=True)
    subject = models.CharField(max_length=500, blank=True)
    body = models.TextField()
    body_type = models.CharField(max_length=20, choices=MessageTemplate.BODY_CHOICES, default='plain_text')
    selected_contacts = models.ManyToManyField(Contact, blank=True, related_name='selected_campaigns')
    selected_groups = models.ManyToManyField(ContactGroup, blank=True, related_name='campaigns')
    recipients_count = models.PositiveIntegerField(default=0)
    valid_recipients_count = models.PositiveIntegerField(default=0)
    invalid_recipients_count = models.PositiveIntegerField(default=0)
    sent_count = models.PositiveIntegerField(default=0)
    failed_count = models.PositiveIntegerField(default=0)
    delivered_count = models.PositiveIntegerField(default=0)
    skipped_count = models.PositiveIntegerField(default=0)
    started_at = models.DateTimeField(null=True, blank=True)
    scheduled_at = models.DateTimeField(null=True, blank=True, db_index=True)
    finished_at = models.DateTimeField(null=True, blank=True)
    settings = models.JSONField(default=dict, blank=True)

    class Meta:
        db_table = 'communication_campaign'
        ordering = ['-created_at']
        indexes = [models.Index(fields=['workspace', 'status'], name='comm_campaign_ws_status')]


class CampaignMessage(models.Model):
    STATUS_CHOICES = [
        ('pending', 'Pending'), ('queued', 'Queued'), ('sent', 'Sent'),
        ('delivered', 'Delivered'), ('failed', 'Failed'), ('skipped', 'Skipped'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    campaign = models.ForeignKey(Campaign, on_delete=models.CASCADE, related_name='messages')
    contact = models.ForeignKey(Contact, on_delete=models.SET_NULL, null=True, blank=True)
    recipient_name = models.CharField(max_length=255, blank=True)
    recipient_phone = models.CharField(max_length=20, blank=True)
    recipient_email = models.EmailField(blank=True)
    rendered_subject = models.CharField(max_length=500, blank=True)
    rendered_body = models.TextField()
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending', db_index=True)
    provider_message_id = models.CharField(max_length=255, blank=True)
    provider_response = models.JSONField(default=dict, blank=True)
    error_message = models.CharField(max_length=1000, blank=True)
    retry_count = models.PositiveSmallIntegerField(default=0)
    is_test = models.BooleanField(default=False)
    queued_at = models.DateTimeField(null=True, blank=True)
    sent_at = models.DateTimeField(null=True, blank=True)
    delivered_at = models.DateTimeField(null=True, blank=True)
    failed_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'communication_campaign_message'
        ordering = ['-created_at']
        indexes = [models.Index(fields=['campaign', 'status'], name='comm_message_campaign_status')]


class ImportJob(WorkspaceOwnedModel):
    STATUS_CHOICES = [('previewed', 'Previewed'), ('completed', 'Completed'), ('failed', 'Failed')]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    file = models.FileField(upload_to='communication/imports/')
    file_name = models.CharField(max_length=255)
    file_type = models.CharField(max_length=10)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='previewed')
    total_rows = models.PositiveIntegerField(default=0)
    valid_rows = models.PositiveIntegerField(default=0)
    invalid_rows = models.PositiveIntegerField(default=0)
    duplicate_rows = models.PositiveIntegerField(default=0)
    mapping = models.JSONField(default=dict, blank=True)
    errors = models.JSONField(default=list, blank=True)
    preview = models.JSONField(default=list, blank=True)

    class Meta:
        db_table = 'communication_import_job'
        ordering = ['-created_at']
