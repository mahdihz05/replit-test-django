from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    dependencies = [
        ('content', '0002_initial'),
        ('ai_engine', '0006_aiconfiguration'),
    ]

    operations = [
        migrations.AddField(
            model_name='generateditem',
            name='saved_content',
            field=models.OneToOneField(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name='generated_source',
                to='content.content',
            ),
        ),
    ]
