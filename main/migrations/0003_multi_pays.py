from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('contenttypes', '0002_remove_content_type_name'),
        ('auth', '0012_alter_user_first_name_max_length'),
    ]

    operations = [
        migrations.RunSQL(
            sql="""
                CREATE TABLE IF NOT EXISTS main_standard (
                    id bigserial PRIMARY KEY,
                    name VARCHAR(100) NOT NULL,
                    type VARCHAR(10) NOT NULL,
                    energy_efficiency DOUBLE PRECISION NOT NULL,
                    thermal_comfort DOUBLE PRECISION NOT NULL,
                    carbon_emissions DOUBLE PRECISION NOT NULL,
                    water_management DOUBLE PRECISION NOT NULL,
                    indoor_air_quality DOUBLE PRECISION NOT NULL
                );

                CREATE TABLE IF NOT EXISTS main_document (
                    id bigserial PRIMARY KEY,
                    name VARCHAR(255) NOT NULL,
                    client_name VARCHAR(255) NOT NULL DEFAULT '',
                    client_email VARCHAR(254) NOT NULL DEFAULT '',
                    admin_notes TEXT NOT NULL DEFAULT '',
                    building_type VARCHAR(20) NOT NULL DEFAULT 'maison',
                    climate_zone VARCHAR(5) NOT NULL DEFAULT 'H2',
                    upload VARCHAR(100) NOT NULL,
                    upload_date TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                    is_active BOOLEAN NOT NULL DEFAULT TRUE,
                    status VARCHAR(20) NOT NULL DEFAULT 'recu',
                    tracking_token VARCHAR(64) NOT NULL UNIQUE DEFAULT '',
                    rapport_pdf VARCHAR(100) NULL,
                    pays VARCHAR(5) NOT NULL DEFAULT 'FR',
                    norme VARCHAR(10) NOT NULL DEFAULT 'RE2020',
                    re2020_energy_efficiency DOUBLE PRECISION NULL,
                    re2020_thermal_comfort DOUBLE PRECISION NULL,
                    re2020_carbon_emissions DOUBLE PRECISION NULL,
                    re2020_water_management DOUBLE PRECISION NULL,
                    re2020_indoor_air_quality DOUBLE PRECISION NULL,
                    rt2012_bbio DOUBLE PRECISION NULL,
                    rt2012_cep DOUBLE PRECISION NULL,
                    rt2012_tic DOUBLE PRECISION NULL,
                    rt2012_airtightness DOUBLE PRECISION NULL,
                    rt2012_enr DOUBLE PRECISION NULL,
                    peb_espec DOUBLE PRECISION NULL,
                    peb_ew DOUBLE PRECISION NULL,
                    peb_u_mur DOUBLE PRECISION NULL,
                    peb_u_toit DOUBLE PRECISION NULL,
                    peb_u_plancher DOUBLE PRECISION NULL,
                    minergie_qh DOUBLE PRECISION NULL,
                    minergie_qtot DOUBLE PRECISION NULL,
                    minergie_n50 DOUBLE PRECISION NULL,
                    sia380_qh DOUBLE PRECISION NULL,
                    cneb_ei DOUBLE PRECISION NULL,
                    cneb_u_mur DOUBLE PRECISION NULL,
                    cneb_u_toit DOUBLE PRECISION NULL,
                    cneb_u_fenetre DOUBLE PRECISION NULL,
                    cneb_infiltration DOUBLE PRECISION NULL,
                    lenoz_ep DOUBLE PRECISION NULL,
                    lenoz_ew DOUBLE PRECISION NULL,
                    lenoz_u_mur DOUBLE PRECISION NULL,
                    lenoz_u_toit DOUBLE PRECISION NULL
                );

                CREATE TABLE IF NOT EXISTS main_analysis (
                    id bigserial PRIMARY KEY,
                    criteria VARCHAR(255) NOT NULL,
                    value DOUBLE PRECISION NOT NULL,
                    requirement DOUBLE PRECISION NOT NULL,
                    compliance BOOLEAN NOT NULL,
                    document_id bigint NOT NULL REFERENCES main_document(id) ON DELETE CASCADE,
                    standard_id bigint NULL REFERENCES main_standard(id) ON DELETE CASCADE
                );

                CREATE TABLE IF NOT EXISTS main_devis (
                    id bigserial PRIMARY KEY,
                    client_nom VARCHAR(255) NOT NULL,
                    client_email VARCHAR(254) NOT NULL,
                    client_phone VARCHAR(30) NOT NULL DEFAULT '',
                    projet_nom VARCHAR(255) NOT NULL DEFAULT '',
                    type_batiment VARCHAR(20) NOT NULL DEFAULT 'maison',
                    norme VARCHAR(20) NOT NULL DEFAULT 'RE2020',
                    montant NUMERIC(8,2) NULL,
                    statut VARCHAR(20) NOT NULL DEFAULT 'en_attente',
                    notes TEXT NOT NULL DEFAULT '',
                    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                    document_id bigint NULL REFERENCES main_document(id) ON DELETE SET NULL
                );

                -- Ajout colonnes manquantes si tables existaient déjà
                ALTER TABLE main_document
                    ADD COLUMN IF NOT EXISTS rapport_pdf VARCHAR(100) NULL,
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

                ALTER TABLE main_devis
                    ADD COLUMN IF NOT EXISTS document_id bigint NULL REFERENCES main_document(id) ON DELETE SET NULL;
            """,
            reverse_sql="SELECT 1;",
        ),
    ]
