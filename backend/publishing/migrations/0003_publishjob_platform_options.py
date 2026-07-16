from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ('publishing', '0002_alter_publishlog_error_type_publishattachment_and_more'),
    ]

    operations = [
        migrations.AddField(
            model_name='publishjob',
            name='platform_options',
            field=models.JSONField(blank=True, default=dict),
        ),
    ]
