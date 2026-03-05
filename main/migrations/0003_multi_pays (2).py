from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
    ('contenttypes', '0002_remove_content_type_name'),
    ('auth', '0012_alter_user_first_name_max_length'),
]

    operations = [
        migrations.RunSQL(
            sql="""
                ALTER TABLE main_document
                    ADD COLUMN IF NOT EXISTS rapport_pdf VARCHAR(100) NULL;

                ALTER TABLE main_devis
                    ADD COLUMN IF NOT EXISTS document_id bigint NULL
                    REFERENCES main_document(id) ON DELETE SET NULL;

                ALTER TABLE main_document
                    ADD COLUMN IF NOT EXISTS pays VARCHAR(5) NOT NULL DEFAULT 'FR',
                    ADD COLUMN IF NOT EXISTS norme VARCHAR(10) NOT NULL DEFAULT 'RE2020',
                    ADD COLUMN IF NOT EXISTS peb_espec DOUBLE PRECISION NULL,
                    ADD COLUMN IF NOT EXISTS peb_ew DOUBLE PRECISION NULL,
                    ADD COLUMN IF NOT EXISTS peb_u_mur DOUBLE PRECISION NULL,
                    ADD COLUMN IF NOT EXISTS peb_u_toit DOUBLE PRECISION NULL,
                    ADD COLUMN IF NOT EXISTS peb_u_plancher DOUBLE PRECISION NULL,
                    ADD COLUMN IF NOT EXISTS minergie_qh DOUBLE PRECISION NULL,
                    ADD COLUMN IF NOT EXISTS minergie_qtot DOUBLE PRECISION NULL,
                    ADD COLUMN IF NOT EXISTS minergie_n50 DOUBLE PRECISION NULL,
                    ADD COLUMN IF NOT EXISTS sia380_qh DOUBLE PRECISION NULL,
                    ADD COLUMN IF NOT EXISTS cneb_ei DOUBLE PRECISION NULL,
                    ADD COLUMN IF NOT EXISTS cneb_u_mur DOUBLE PRECISION NULL,
                    ADD COLUMN IF NOT EXISTS cneb_u_toit DOUBLE PRECISION NULL,
                    ADD COLUMN IF NOT EXISTS cneb_u_fenetre DOUBLE PRECISION NULL,
                    ADD COLUMN IF NOT EXISTS cneb_infiltration DOUBLE PRECISION NULL,
                    ADD COLUMN IF NOT EXISTS lenoz_ep DOUBLE PRECISION NULL,
                    ADD COLUMN IF NOT EXISTS lenoz_ew DOUBLE PRECISION NULL,
                    ADD COLUMN IF NOT EXISTS lenoz_u_mur DOUBLE PRECISION NULL,
                    ADD COLUMN IF NOT EXISTS lenoz_u_toit DOUBLE PRECISION NULL;
            """,
            reverse_sql="""
                ALTER TABLE main_document
                    DROP COLUMN IF EXISTS rapport_pdf,
                    DROP COLUMN IF EXISTS pays,
                    DROP COLUMN IF EXISTS norme,
                    DROP COLUMN IF EXISTS peb_espec,
                    DROP COLUMN IF EXISTS peb_ew,
                    DROP COLUMN IF EXISTS peb_u_mur,
                    DROP COLUMN IF EXISTS peb_u_toit,
                    DROP COLUMN IF EXISTS peb_u_plancher,
                    DROP COLUMN IF EXISTS minergie_qh,
                    DROP COLUMN IF EXISTS minergie_qtot,
                    DROP COLUMN IF EXISTS minergie_n50,
                    DROP COLUMN IF EXISTS sia380_qh,
                    DROP COLUMN IF EXISTS cneb_ei,
                    DROP COLUMN IF EXISTS cneb_u_mur,
                    DROP COLUMN IF EXISTS cneb_u_toit,
                    DROP COLUMN IF EXISTS cneb_u_fenetre,
                    DROP COLUMN IF EXISTS cneb_infiltration,
                    DROP COLUMN IF EXISTS lenoz_ep,
                    DROP COLUMN IF EXISTS lenoz_ew,
                    DROP COLUMN IF EXISTS lenoz_u_mur,
                    DROP COLUMN IF EXISTS lenoz_u_toit;

                ALTER TABLE main_devis
                    DROP COLUMN IF EXISTS document_id;
            """,
        ),
    ]
