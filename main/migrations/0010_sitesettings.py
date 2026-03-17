from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('main', '0009_add_dpe_extraction_fields'),
    ]

    operations = [
        migrations.RunSQL(
            sql="""
                CREATE TABLE IF NOT EXISTS main_sitesettings (
                    id SERIAL PRIMARY KEY,
                    maintenance_mode BOOLEAN NOT NULL DEFAULT FALSE,
                    maintenance_message TEXT NOT NULL DEFAULT 'Nous effectuons des mises à jour pour améliorer votre expérience. Nous serons de retour très bientôt.',
                    maintenance_title VARCHAR(200) NOT NULL DEFAULT 'Site en maintenance'
                );

                -- Insérer le singleton par défaut (pk=1)
                INSERT INTO main_sitesettings (id, maintenance_mode)
                VALUES (1, FALSE)
                ON CONFLICT (id) DO NOTHING;
            """,
            reverse_sql="DROP TABLE IF EXISTS main_sitesettings;",
        ),
    ]
