from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('main', '0014_avis'),
    ]

    operations = [
        migrations.AddField(
            model_name='devis',
            name='motif_refus',
            field=models.TextField(blank=True, default='', verbose_name='Motif de refus'),
        ),
    ]
