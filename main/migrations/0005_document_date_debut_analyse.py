from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('main', '0003_multi_pays'),  
    ]

    operations = [
        migrations.AddField(
            model_name='document',
            name='date_debut_analyse',
            field=models.DateField(blank=True, null=True),
        ),
    ]
