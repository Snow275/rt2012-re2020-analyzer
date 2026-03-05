from django.db import migrations


class Migration(migrations.Migration):

    dependencies = []

    operations = [
        migrations.RunSQL(
            sql="ALTER TABLE main_document ADD COLUMN IF NOT EXISTS rapport_pdf VARCHAR(100) NULL;",
            reverse_sql="ALTER TABLE main_document DROP COLUMN IF EXISTS rapport_pdf;",
        ),
    ]
