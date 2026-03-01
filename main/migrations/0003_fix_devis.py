from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('main', '0002_devis'),
    ]

    operations = [
        migrations.RunSQL(
            sql="""
            CREATE TABLE IF NOT EXISTS main_devis (
                id bigserial PRIMARY KEY,
                client_nom varchar(255) NOT NULL,
                client_email varchar(254) NOT NULL,
                client_phone varchar(30) NOT NULL DEFAULT '',
                projet_nom varchar(255) NOT NULL DEFAULT '',
                type_batiment varchar(20) NOT NULL DEFAULT 'maison',
                norme varchar(20) NOT NULL DEFAULT 'RE2020',
                montant numeric(8,2) NULL,
                statut varchar(20) NOT NULL DEFAULT 'en_attente',
                notes text NOT NULL DEFAULT '',
                created_at timestamp with time zone NOT NULL DEFAULT now(),
                updated_at timestamp with time zone NOT NULL DEFAULT now()
            );
            ALTER TABLE main_document ADD COLUMN IF NOT EXISTS admin_notes text NOT NULL DEFAULT '';
            ALTER TABLE main_document ADD COLUMN IF NOT EXISTS client_email varchar(254) NOT NULL DEFAULT '';
            """,
            reverse_sql="DROP TABLE IF EXISTS main_devis;"
        ),
    ]
