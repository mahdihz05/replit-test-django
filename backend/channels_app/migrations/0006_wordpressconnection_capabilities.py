from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ('channels_app', '0005_linkedin_oauth_security'),
    ]

    operations = [
        migrations.AddField(
            model_name='wordpressconnection',
            name='site_name',
            field=models.CharField(blank=True, max_length=255),
        ),
        migrations.AddField(
            model_name='wordpressconnection',
            name='capabilities',
            field=models.JSONField(blank=True, default=dict),
        ),
        migrations.AddField(
            model_name='wordpressconnection',
            name='capabilities_synced_at',
            field=models.DateTimeField(blank=True, null=True),
        ),
    ]
