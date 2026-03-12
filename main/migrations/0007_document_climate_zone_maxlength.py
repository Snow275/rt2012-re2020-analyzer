from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('main', '0006_document_rapport_ia_json'),
    ]

    operations = [
        migrations.RunSQL(
            sql="ALTER TABLE main_document ALTER COLUMN climate_zone TYPE VARCHAR(6);",
            reverse_sql="ALTER TABLE main_document ALTER COLUMN climate_zone TYPE VARCHAR(5);",
        ),
    ]
