from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('main', '0007_document_climate_zone_maxlength'),
    ]

    operations = [
        migrations.RunSQL(
            sql="""
                CREATE TABLE IF NOT EXISTS main_factureenergie (
                    id bigserial PRIMARY KEY,
                    document_id bigint NOT NULL REFERENCES main_document(id) ON DELETE CASCADE,
                    fichier VARCHAR(200) NOT NULL,
                    nom VARCHAR(255) NOT NULL DEFAULT '',
                    type_energie VARCHAR(20) NOT NULL DEFAULT 'electricite',
                    uploaded_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                    analyse_json JSONB NULL,
                    analyse_ok BOOLEAN NOT NULL DEFAULT FALSE,
                    analyse_error TEXT NOT NULL DEFAULT ''
                );

                ALTER TABLE main_document
                    ADD COLUMN IF NOT EXISTS surface_totale DOUBLE PRECISION NULL,
                    ADD COLUMN IF NOT EXISTS annee_construction INTEGER NULL,
                    ADD COLUMN IF NOT EXISTS nombre_logements INTEGER NULL,
                    ADD COLUMN IF NOT EXISTS type_analyse VARCHAR(10) NOT NULL DEFAULT 'energie';

                ALTER TABLE main_documentfile
                    ADD COLUMN IF NOT EXISTS taille INTEGER NULL;
            """,
            reverse_sql="""
                DROP TABLE IF EXISTS main_factureenergie;
                ALTER TABLE main_document
                    DROP COLUMN IF EXISTS surface_totale,
                    DROP COLUMN IF EXISTS annee_construction,
                    DROP COLUMN IF EXISTS nombre_logements,
                    DROP COLUMN IF EXISTS type_analyse;
            """,
        ),
    ]
