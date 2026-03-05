from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('main', '0001_rapport_pdf'),
    ]

    operations = [
        migrations.RunSQL(
            sql="""
                ALTER TABLE main_devis 
                ADD COLUMN IF NOT EXISTS document_id bigint NULL 
                REFERENCES main_document(id) ON DELETE SET NULL;
            """,
            reverse_sql="ALTER TABLE main_devis DROP COLUMN IF EXISTS document_id;",
        ),
    ]
