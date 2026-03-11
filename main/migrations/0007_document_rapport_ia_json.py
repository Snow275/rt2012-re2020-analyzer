from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('main', '0003_multi_pays'),
    ]

    operations = [
        migrations.AddField(
            model_name='document',
            name='rapport_ia_json',
            field=models.TextField(blank=True, default=''),
        ),
    ]
