from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('main', '0003_multi_pays'),
    ]

    operations = [
        migrations.RunSQL(
            sql="ALTER TABLE main_document ADD COLUMN IF NOT EXISTS date_debut_analyse DATE NULL;",
            reverse_sql="ALTER TABLE main_document DROP COLUMN IF EXISTS date_debut_analyse;",
        ),
    ]
