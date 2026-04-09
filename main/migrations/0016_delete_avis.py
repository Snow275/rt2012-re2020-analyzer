from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('main', '0015_devis_motif_refus'),
    ]

    operations = [
        migrations.DeleteModel(
            name='Avis',
        ),
    ]
