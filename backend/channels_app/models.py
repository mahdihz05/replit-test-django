import uuid
import random
import string
from django.db import models
from django.utils import timezone


class PublishChannel(models.Model):
    PLATFORM_CHOICES = [('telegram', 'Telegram'), ('bale', 'Bale'), ('website', 'Website')]
    TYPE_CHOICES = [('channel', 'Channel'), ('group', 'Group'), ('supergroup', 'Supergroup'), ('page', 'Page')]

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
