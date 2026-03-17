from django.db import migrations, models


class Migration(migrations.Migration):
    """
    Corrige le champ id de SiteSettings : AutoField → BigAutoField
    pour être cohérent avec DEFAULT_AUTO_FIELD = BigAutoField dans settings.py
    """

    dependencies = [
        ('main', '0010_sitesettings'),
    ]

    operations = [
        migrations.AlterField(
            model_name='sitesettings',
            name='id',
            field=models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID'),
        ),
    ]
