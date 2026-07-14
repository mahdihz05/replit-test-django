from django.db import migrations, models
import ai_engine.models


def create_default_configuration(apps, schema_editor):
    AIConfiguration = apps.get_model('ai_engine', 'AIConfiguration')
    AIConfiguration.objects.get_or_create(pk=1)


class Migration(migrations.Migration):
    dependencies = [
        ('ai_engine', '0005_generateditem_image_generationbatch_image_status_and_more'),
    ]

    operations = [
        migrations.CreateModel(
            name='AIConfiguration',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('usd_to_irt', models.PositiveIntegerField(default=180000, verbose_name='نرخ دلار به تومان')),
                ('profit_multiplier', models.DecimalField(decimal_places=2, default=1.6, max_digits=5, verbose_name='ضریب سود و اطمینان')),
                ('minimum_operation_cost', models.PositiveIntegerField(default=25, verbose_name='حداقل هزینه هر عملیات (تومان)')),
                ('ai_models', models.JSONField(default=ai_engine.models.default_ai_models, verbose_name='مدل‌ها')),
                ('model_pricing_usd', models.JSONField(default=ai_engine.models.default_model_pricing, verbose_name='قیمت خام مدل‌ها (دلار)')),
                ('estimated_token_usage', models.JSONField(default=ai_engine.models.default_token_usage, verbose_name='مصرف تخمینی توکن')),
                ('wallet_costs', models.JSONField(default=ai_engine.models.default_wallet_costs, verbose_name='هزینه‌های کیف پول (تومان)')),
                ('image_defaults', models.JSONField(default=ai_engine.models.default_image_defaults, verbose_name='تنظیمات پیش‌فرض تصویر')),
                ('image_wallet_costs', models.JSONField(default=ai_engine.models.default_image_wallet_costs, verbose_name='هزینه کیفیت‌های تصویر')),
                ('updated_at', models.DateTimeField(auto_now=True)),
            ],
            options={
                'verbose_name': 'تنظیمات هوش مصنوعی',
                'verbose_name_plural': 'تنظیمات هوش مصنوعی',
            },
        ),
        migrations.RunPython(create_default_configuration, migrations.RunPython.noop),
    ]
