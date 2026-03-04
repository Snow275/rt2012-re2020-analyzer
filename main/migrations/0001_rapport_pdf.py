from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = []

    operations = [
        migrations.AddField(
            model_name='document',
            name='rapport_pdf',
            field=models.FileField(blank=True, null=True, upload_to='rapports/'),
        ),
    ]
