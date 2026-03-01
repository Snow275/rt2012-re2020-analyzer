from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('main', '0002_devis'),
    ]

    operations = [
        # Crée la table main_devis si elle n'existe pas
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
            """,
            reverse_sql="DROP TABLE IF EXISTS main_devis;"
        ),
        # Ajoute admin_notes au modèle Document
        migrations.AddField(
            model_name='document',
            name='admin_notes',
            field=models.TextField(blank=True, default=''),
        ),
    ]
