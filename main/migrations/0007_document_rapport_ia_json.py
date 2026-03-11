from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('main', '0005_document_date_debut_analyse'),
    ]

    operations = [
        migrations.AddField(
            model_name='document',
            name='rapport_ia_json',
            field=models.TextField(blank=True, default=''),
        ),
    ]
