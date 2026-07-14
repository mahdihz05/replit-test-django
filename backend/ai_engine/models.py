import uuid
from copy import deepcopy
from django.db import models
from django.conf import settings

from config.ai import (
    AI_MODELS,
    ESTIMATED_TOKEN_USAGE,
    IMAGE_GENERATION_DEFAULTS,
    IMAGE_WALLET_COSTS,
    MODEL_PRICING_USD,
    WALLET_COSTS,
)


def default_ai_models():
    return deepcopy(AI_MODELS)


def default_model_pricing():
    return deepcopy(MODEL_PRICING_USD)


def default_token_usage():
    return deepcopy(ESTIMATED_TOKEN_USAGE)


def default_wallet_costs():
    return deepcopy(WALLET_COSTS)


def default_image_defaults():
    return deepcopy(IMAGE_GENERATION_DEFAULTS)


def default_image_wallet_costs():
    return deepcopy(IMAGE_WALLET_COSTS)


class AIConfiguration(models.Model):
    """Singleton, admin-managed overrides for all AI and wallet settings."""

    usd_to_irt = models.PositiveIntegerField(default=180_000, verbose_name="نرخ دلار به تومان")
    profit_multiplier = models.DecimalField(
        max_digits=5, decimal_places=2, default=1.6, verbose_name="ضریب سود و اطمینان"
    )
    minimum_operation_cost = models.PositiveIntegerField(
        default=25, verbose_name="حداقل هزینه هر عملیات (تومان)"
    )
    ai_models = models.JSONField(default=default_ai_models, verbose_name="مدل‌ها")
    model_pricing_usd = models.JSONField(default=default_model_pricing, verbose_name="قیمت خام مدل‌ها (دلار)")
    estimated_token_usage = models.JSONField(default=default_token_usage, verbose_name="مصرف تخمینی توکن")
    wallet_costs = models.JSONField(default=default_wallet_costs, verbose_name="هزینه‌های کیف پول (تومان)")
    image_defaults = models.JSONField(default=default_image_defaults, verbose_name="تنظیمات پیش‌فرض تصویر")
    image_wallet_costs = models.JSONField(default=default_image_wallet_costs, verbose_name="هزینه کیفیت‌های تصویر")
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "تنظیمات هوش مصنوعی"
        verbose_name_plural = "تنظیمات هوش مصنوعی"

    def save(self, *args, **kwargs):
        self.pk = 1
        super().save(*args, **kwargs)

    def __str__(self):
        return "تنظیمات مرکزی هوش مصنوعی"


class GenerationBatch(models.Model):
    MODE_CHOICES = [
        ('standard', 'استاندارد'),
        ('bundle', 'بازتولید همزمان'),
        ('multi_variant', 'چندگزینه‌ای'),
    ]
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('success', 'Success'),
        ('failed', 'Failed'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    workspace = models.ForeignKey(
        'workspaces.Workspace',
        on_delete=models.CASCADE,
        related_name='ai_generation_batches'
    )
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    mode = models.CharField(max_length=20, choices=MODE_CHOICES)
    capability = models.CharField(max_length=30)
    topic = models.TextField()
    tone = models.CharField(max_length=30, blank=True)
    platform = models.CharField(max_length=30, blank=True)
    variant_count = models.PositiveSmallIntegerField(null=True, blank=True)
    wallet_cost_charged = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    image_status = models.CharField(
        max_length=20,
        choices=[('pending', 'Pending'), ('success', 'Success'), ('failed', 'Failed')],
        blank=True,
        default=''
    )
    created_at = models.DateTimeField(auto_now_add=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        db_table = 'ai_engine_generationbatch'
        ordering = ['-created_at']

    def __str__(self):
        return f'{self.mode} - {self.capability}'


class GeneratedItem(models.Model):
    ITEM_TYPE_CHOICES = [
        ('full_text', 'متن کامل'),
        ('short_text', 'نسخه کوتاه'),
        ('hashtags', 'هشتگ‌ها'),
        ('title', 'عنوان'),
        ('variant', 'نسخه'),
        ('image', 'تصویر'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    batch = models.ForeignKey(GenerationBatch, on_delete=models.CASCADE, related_name='items')
    item_type = models.CharField(max_length=20, choices=ITEM_TYPE_CHOICES)
    order = models.PositiveSmallIntegerField(default=0)
    content = models.TextField(blank=True)
    image = models.ImageField(upload_to='content/images/', null=True, blank=True)
    saved_as_draft = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'ai_engine_generateditem'
        ordering = ['order', 'created_at']

    def __str__(self):
        return f'{self.item_type} - {self.batch.id}'


class AIChatSession(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    workspace = models.ForeignKey(
        'workspaces.Workspace',
        on_delete=models.CASCADE,
        related_name='chat_sessions'
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE
    )
    content = models.ForeignKey(
        'content.Content',
        on_delete=models.SET_NULL,
        null=True,
        blank=True
    )
    title = models.CharField(max_length=255, default='New Chat')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'ai_engine_aichatsession'
        ordering = ['-updated_at']


class AIChatMessage(models.Model):
    ROLE_CHOICES = [('user', 'User'), ('assistant', 'Assistant')]
    TYPE_CHOICES = [('text', 'Text'), ('image', 'Image')]

    session = models.ForeignKey(AIChatSession, on_delete=models.CASCADE, related_name='messages')
    role = models.CharField(max_length=10, choices=ROLE_CHOICES)
    type = models.CharField(max_length=10, choices=TYPE_CHOICES, default='text')
    body = models.TextField(blank=True)
    image_url = models.CharField(max_length=500, blank=True)
    metadata = models.JSONField(null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'ai_engine_aichatmessage'
        ordering = ['created_at']
