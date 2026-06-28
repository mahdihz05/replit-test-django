import uuid
from django.db import models


class PublishJob(models.Model):
    STATUS_CHOICES = [
        ('queued', 'Queued'),
        ('processing', 'Processing'),
        ('success', 'Success'),
        ('failed', 'Failed'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    content = models.ForeignKey('content.Content', on_delete=models.CASCADE, related_name='publish_jobs')
    channel = models.ForeignKey('channels_app.PublishChannel', on_delete=models.CASCADE)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='queued')
    scheduled_at = models.DateTimeField(null=True, blank=True)
    started_at = models.DateTimeField(null=True, blank=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    attempt_count = models.IntegerField(default=0)
    max_attempts = models.IntegerField(default=3)
    next_retry_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'publishing_publishjob'
        ordering = ['-created_at']


class PublishLog(models.Model):
    ERROR_TYPE_CHOICES = [
        ('connection_error', 'Connection Error'),
        ('auth_error', 'Auth Error'),
        ('bot_removed', 'Bot Removed'),
        ('rate_limit', 'Rate Limit'),
        ('unknown', 'Unknown'),
    ]

    USER_MESSAGES = {
        'connection_error': 'خطا در اتصال به پلتفرم. لطفاً اتصال اینترنت سرور را بررسی کنید.',
        'auth_error': 'ربات دسترسی لازم را ندارد. مطمئن شوید ربات هنوز ادمین کانال است.',
        'bot_removed': 'ربات از کانال حذف شده است. لطفاً دوباره ربات را اضافه کنید.',
        'rate_limit': 'محدودیت ارسال از طرف پلتفرم. دوباره تلاش خواهد شد.',
        'unknown': 'خطای ناشناخته رخ داد. جزئیات فنی در لاگ‌ها ثبت شده است.',
    }

    job = models.ForeignKey(PublishJob, on_delete=models.CASCADE, related_name='logs')
    attempt_number = models.IntegerField()
    success = models.BooleanField()
    error_type = models.CharField(max_length=30, choices=ERROR_TYPE_CHOICES, blank=True)
    error_message = models.TextField(blank=True)
    user_message = models.TextField(blank=True)
    api_response = models.JSONField(null=True)
    attempted_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'publishing_publishlog'
        ordering = ['-attempted_at']
