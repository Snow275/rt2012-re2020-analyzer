from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('main', '0007_document_climate_zone_maxlength'),
    ]

    operations = [
        # 1. Aligne la BDD avec le modèle (null=True, blank=True)
        migrations.RunSQL(
            sql="""
                UPDATE main_document SET rapport_ia_json = '' WHERE rapport_ia_json IS NULL;
                ALTER TABLE main_document ALTER COLUMN rapport_ia_json DROP NOT NULL;
                ALTER TABLE main_document ALTER COLUMN rapport_ia_json SET DEFAULT '';
            """,
            reverse_sql="""
                UPDATE main_document SET rapport_ia_json = '' WHERE rapport_ia_json IS NULL;
                ALTER TABLE main_document ALTER COLUMN rapport_ia_json SET NOT NULL;
            """,
        ),
        # 2. Ajoute les colonnes type_analyse / surface_totale / etc. si manquantes
        migrations.RunSQL(
            sql="""
                ALTER TABLE main_document
                    ADD COLUMN IF NOT EXISTS type_analyse VARCHAR(10) NOT NULL DEFAULT 'energie',
                    ADD COLUMN IF NOT EXISTS surface_totale DOUBLE PRECISION NULL,
                    ADD COLUMN IF NOT EXISTS annee_construction INTEGER NULL,
                    ADD COLUMN IF NOT EXISTS nombre_logements INTEGER NULL;

                CREATE TABLE IF NOT EXISTS main_documentfile (
                    id bigserial PRIMARY KEY,
                    fichier VARCHAR(100) NOT NULL,
                    nom VARCHAR(255) NOT NULL DEFAULT '',
                    taille INTEGER NULL,
                    uploaded_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                    document_id bigint NOT NULL REFERENCES main_document(id) ON DELETE CASCADE
                );
            """,
            reverse_sql="SELECT 1;",
        ),
    ]
