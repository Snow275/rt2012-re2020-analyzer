from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('main', '0005_document_date_debut_analyse'),
    ]

    operations = [
        migrations.RunSQL(
            sql="ALTER TABLE main_document ADD COLUMN IF NOT EXISTS rapport_ia_json TEXT NOT NULL DEFAULT '';",
            reverse_sql="ALTER TABLE main_document DROP COLUMN IF EXISTS rapport_ia_json;",
        ),
    ]
