import uuid
from django.db import models
from django.conf import settings


class Content(models.Model):
    STATUS_CHOICES = [
        ('draft', 'Draft'),
        ('ready', 'Ready'),
        ('scheduled', 'Scheduled'),
        ('publishing', 'Publishing'),
        ('published', 'Published'),
        ('failed', 'Failed'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    workspace = models.ForeignKey(
        'workspaces.Workspace',
        on_delete=models.CASCADE,
        related_name='contents'
    )
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name='created_contents'
    )
    title = models.CharField(max_length=300, default='untitled')
    body = models.TextField(blank=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='draft')
    language = models.CharField(max_length=10, default='fa')
    goal = models.CharField(max_length=300, blank=True)
    tags = models.JSONField(default=list)
    image = models.ImageField(upload_to='content/images/', null=True, blank=True)
    scheduled_at = models.DateTimeField(null=True, blank=True)
    published_at = models.DateTimeField(null=True, blank=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'content_content'
        ordering = ['-created_at']

    def __str__(self):
        return self.title


class ContentVersion(models.Model):
    SOURCE_CHOICES = [('user', 'User'), ('ai', 'AI')]

    content = models.ForeignKey(Content, on_delete=models.CASCADE, related_name='versions')
    body = models.TextField()
    version_number = models.IntegerField()
    source = models.CharField(max_length=10, choices=SOURCE_CHOICES)
    ai_model = models.CharField(max_length=100, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'content_contentversion'
        ordering = ['-version_number']

    def __str__(self):
        return f'{self.content.title} - v{self.version_number}'
