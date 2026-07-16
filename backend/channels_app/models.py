import uuid
import random
import string
from django.db import models
from django.utils import timezone


class PublishChannel(models.Model):
    PLATFORM_CHOICES = [
        ('telegram', 'Telegram'),
        ('bale', 'Bale'),
        ('website', 'Website'),
        ('linkedin', 'LinkedIn'),
        ('wordpress', 'WordPress'),
    ]
    TYPE_CHOICES = [
        ('channel', 'Channel'),
        ('group', 'Group'),
        ('supergroup', 'Supergroup'),
        ('page', 'Page'),
        ('personal', 'Personal Profile'),
        ('organization', 'Company Page'),
        ('site', 'Website'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    workspace = models.ForeignKey('workspaces.Workspace', on_delete=models.CASCADE, related_name='channels')
    platform = models.CharField(max_length=20, choices=PLATFORM_CHOICES)
    channel_type = models.CharField(max_length=20, choices=TYPE_CHOICES, blank=True)
    name = models.CharField(max_length=255)
    external_id = models.CharField(max_length=255)
    username = models.CharField(max_length=255, blank=True)
    extra_data = models.JSONField(null=True, blank=True)
    is_verified = models.BooleanField(default=False)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'channels_publishchannel'
        unique_together = ('workspace', 'platform', 'external_id')

    def __str__(self):
        return f'{self.name} ({self.platform})'


class ChannelVerification(models.Model):
    STATUS_CHOICES = [('pending', 'Pending'), ('verified', 'Verified'), ('expired', 'Expired')]

    workspace = models.ForeignKey('workspaces.Workspace', on_delete=models.CASCADE)
    requested_by = models.ForeignKey('users.User', on_delete=models.CASCADE)
    platform = models.CharField(max_length=20, choices=[('telegram', 'Telegram'), ('bale', 'Bale')])
    name = models.CharField(max_length=255, default='')
    channel_type = models.CharField(max_length=20, choices=PublishChannel.TYPE_CHOICES, default='channel')
    token = models.CharField(max_length=20, unique=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    channel = models.ForeignKey(PublishChannel, on_delete=models.SET_NULL, null=True, blank=True)
    expires_at = models.DateTimeField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'channels_channelverification'

    @staticmethod
    def generate_token():
        chars = string.ascii_uppercase + string.digits
        code = ''.join(random.choices(chars, k=8))
        return f'VRF-{code}'

    def is_valid(self):
        return self.status == 'pending' and self.expires_at > timezone.now()


class LinkedInConnection(models.Model):
    STATUS_CHOICES = [('active', 'Active'), ('needs_reauth', 'Needs Reauth'), ('disconnected', 'Disconnected')]
    TARGET_CHOICES = [('personal', 'Personal'), ('organization', 'Organization')]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    workspace = models.ForeignKey('workspaces.Workspace', on_delete=models.CASCADE, related_name='linkedin_connections')
    user = models.ForeignKey('users.User', on_delete=models.CASCADE, related_name='linkedin_connections')
    platform_target = models.CharField(max_length=20, choices=TARGET_CHOICES, default='personal')
    linkedin_subject_id = models.CharField(max_length=255, blank=True)
    person_urn = models.CharField(max_length=255, blank=True)
    organization_urn = models.CharField(max_length=255, blank=True)
    name = models.CharField(max_length=255, blank=True)
    email = models.EmailField(blank=True)
    avatar_url = models.URLField(max_length=1000, blank=True)
    scopes = models.JSONField(default=list, blank=True)
    access_token = models.TextField()
    refresh_token = models.TextField(blank=True)
    access_token_expires_at = models.DateTimeField(null=True, blank=True)
    refresh_token_expires_at = models.DateTimeField(null=True, blank=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='active')
    connected_at = models.DateTimeField(auto_now_add=True)
    disconnected_at = models.DateTimeField(null=True, blank=True)
    updated_at = models.DateTimeField(auto_now=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        db_table = 'channels_linkedinconnection'
        constraints = [
            models.UniqueConstraint(
                fields=['workspace', 'platform_target'],
                name='unique_linkedin_target_per_workspace',
            ),
        ]
        indexes = [
            models.Index(fields=['workspace', 'status', 'is_active'], name='linkedin_conn_status_idx'),
            models.Index(fields=['linkedin_subject_id'], name='linkedin_subject_idx'),
        ]

    def __str__(self):
        return f'LinkedIn {self.platform_target} for {self.workspace}'


class LinkedInOAuthState(models.Model):
    """Short-lived, one-time OAuth state. Only the SHA-256 digest is persisted."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey('users.User', on_delete=models.CASCADE, related_name='linkedin_oauth_states')
    workspace = models.ForeignKey('workspaces.Workspace', on_delete=models.CASCADE)
    state_hash = models.CharField(max_length=64, unique=True)
    session_key = models.CharField(max_length=64, blank=True)
    platform_target = models.CharField(max_length=20, choices=LinkedInConnection.TARGET_CHOICES, default='personal')
    frontend_origin = models.URLField(max_length=500)
    expires_at = models.DateTimeField()
    consumed_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'channels_linkedinoauthstate'
        indexes = [
            models.Index(fields=['expires_at', 'consumed_at'], name='linkedin_oauth_exp_idx'),
        ]


class WordPressConnection(models.Model):
    STATUS_CHOICES = [('active', 'Active'), ('invalid', 'Invalid'), ('disconnected', 'Disconnected')]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    workspace = models.ForeignKey('workspaces.Workspace', on_delete=models.CASCADE, related_name='wordpress_connections')
    user = models.ForeignKey('users.User', on_delete=models.CASCADE, related_name='wordpress_connections')
    site_url = models.URLField(max_length=500)
    wp_username = models.CharField(max_length=255)
    application_password = models.TextField()
    site_name = models.CharField(max_length=255, blank=True)
    capabilities = models.JSONField(default=dict, blank=True)
    capabilities_synced_at = models.DateTimeField(null=True, blank=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='active')
    connected_at = models.DateTimeField(auto_now_add=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        db_table = 'channels_wordpressconnection'
        unique_together = ('workspace', 'site_url')

    def __str__(self):
        return f'WordPress {self.site_url} for {self.workspace}'
