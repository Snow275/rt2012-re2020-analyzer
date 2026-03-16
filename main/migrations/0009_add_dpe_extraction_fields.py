from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('main', '0008_factureenergie'),
    ]

    operations = [
        migrations.RunSQL(
            sql="""
                -- ── Détection rapport ─────────────────────────────────────────
                ALTER TABLE main_document
                    ADD COLUMN IF NOT EXISTS type_rapport VARCHAR(30) NOT NULL DEFAULT 'inconnu',
                    ADD COLUMN IF NOT EXISTS extraction_ok BOOLEAN NOT NULL DEFAULT FALSE,
                    ADD COLUMN IF NOT EXISTS extraction_json JSONB NULL,
                    ADD COLUMN IF NOT EXISTS extraction_alertes JSONB NULL,
                    ADD COLUMN IF NOT EXISTS logiciel_detecte VARCHAR(100) NOT NULL DEFAULT '',
                    ADD COLUMN IF NOT EXISTS version_norme_detectee VARCHAR(50) NOT NULL DEFAULT '';

                -- ── Champs DPE ─────────────────────────────────────────────────
                ALTER TABLE main_document
                    ADD COLUMN IF NOT EXISTS dpe_classe_energie VARCHAR(1) NOT NULL DEFAULT '',
                    ADD COLUMN IF NOT EXISTS dpe_classe_ges VARCHAR(1) NOT NULL DEFAULT '',
                    ADD COLUMN IF NOT EXISTS dpe_conso_ep DOUBLE PRECISION NULL,
                    ADD COLUMN IF NOT EXISTS dpe_emission_ges DOUBLE PRECISION NULL,
                    ADD COLUMN IF NOT EXISTS dpe_surface_ref DOUBLE PRECISION NULL,
                    ADD COLUMN IF NOT EXISTS dpe_date_visite VARCHAR(20) NOT NULL DEFAULT '',
                    ADD COLUMN IF NOT EXISTS dpe_diagnostiqueur VARCHAR(255) NOT NULL DEFAULT '';

                -- ── Observations expert (PCA) ──────────────────────────────────
                ALTER TABLE main_document
                    ADD COLUMN IF NOT EXISTS obs_toiture_etat VARCHAR(20) NOT NULL DEFAULT '',
                    ADD COLUMN IF NOT EXISTS obs_toiture_age INTEGER NULL,
                    ADD COLUMN IF NOT EXISTS obs_toiture_notes TEXT NOT NULL DEFAULT '',
                    ADD COLUMN IF NOT EXISTS obs_facade_etat VARCHAR(20) NOT NULL DEFAULT '',
                    ADD COLUMN IF NOT EXISTS obs_facade_isolation VARCHAR(20) NOT NULL DEFAULT '',
                    ADD COLUMN IF NOT EXISTS obs_facade_notes TEXT NOT NULL DEFAULT '',
                    ADD COLUMN IF NOT EXISTS obs_menuiseries_type VARCHAR(20) NOT NULL DEFAULT '',
                    ADD COLUMN IF NOT EXISTS obs_menuiseries_etat VARCHAR(20) NOT NULL DEFAULT '',
                    ADD COLUMN IF NOT EXISTS obs_menuiseries_notes TEXT NOT NULL DEFAULT '',
                    ADD COLUMN IF NOT EXISTS obs_chauffage_type VARCHAR(20) NOT NULL DEFAULT '',
                    ADD COLUMN IF NOT EXISTS obs_chauffage_age INTEGER NULL,
                    ADD COLUMN IF NOT EXISTS obs_chauffage_etat VARCHAR(20) NOT NULL DEFAULT '',
                    ADD COLUMN IF NOT EXISTS obs_plomberie_etat VARCHAR(20) NOT NULL DEFAULT '',
                    ADD COLUMN IF NOT EXISTS obs_ecs_age INTEGER NULL,
                    ADD COLUMN IF NOT EXISTS obs_elec_etat VARCHAR(20) NOT NULL DEFAULT '',
                    ADD COLUMN IF NOT EXISTS obs_vmc_type VARCHAR(20) NOT NULL DEFAULT '',
                    ADD COLUMN IF NOT EXISTS obs_vmc_etat VARCHAR(20) NOT NULL DEFAULT '',
                    ADD COLUMN IF NOT EXISTS obs_humidite VARCHAR(20) NOT NULL DEFAULT '',
                    ADD COLUMN IF NOT EXISTS obs_fissures VARCHAR(20) NOT NULL DEFAULT '',
                    ADD COLUMN IF NOT EXISTS obs_risques_notes TEXT NOT NULL DEFAULT '',
                    ADD COLUMN IF NOT EXISTS obs_cout_toiture DOUBLE PRECISION NULL,
                    ADD COLUMN IF NOT EXISTS obs_cout_isolation DOUBLE PRECISION NULL,
                    ADD COLUMN IF NOT EXISTS obs_cout_chauffage DOUBLE PRECISION NULL,
                    ADD COLUMN IF NOT EXISTS obs_cout_menuiseries DOUBLE PRECISION NULL,
                    ADD COLUMN IF NOT EXISTS obs_cout_plomberie DOUBLE PRECISION NULL,
                    ADD COLUMN IF NOT EXISTS obs_cout_autres DOUBLE PRECISION NULL,
                    ADD COLUMN IF NOT EXISTS obs_conso_kwh DOUBLE PRECISION NULL,
                    ADD COLUMN IF NOT EXISTS obs_cout_energie DOUBLE PRECISION NULL,
                    ADD COLUMN IF NOT EXISTS obs_classe_dpe VARCHAR(1) NOT NULL DEFAULT '',
                    ADD COLUMN IF NOT EXISTS obs_potentiel_economies VARCHAR(20) NOT NULL DEFAULT '';

                -- ── DocumentFile — champs extraction ──────────────────────────
                ALTER TABLE main_documentfile
                    ADD COLUMN IF NOT EXISTS type_rapport_detecte VARCHAR(30) NOT NULL DEFAULT '',
                    ADD COLUMN IF NOT EXISTS extraction_ok BOOLEAN NOT NULL DEFAULT FALSE,
                    ADD COLUMN IF NOT EXISTS extraction_json JSONB NULL;

                -- ── DocumentFile — nouveaux types (type_fichier) ───────────────
                -- Pas besoin de migration SQL pour les choices Django (metadata uniquement)
            """,
            reverse_sql="""
                ALTER TABLE main_document
                    DROP COLUMN IF EXISTS type_rapport,
                    DROP COLUMN IF EXISTS extraction_ok,
                    DROP COLUMN IF EXISTS extraction_json,
                    DROP COLUMN IF EXISTS extraction_alertes,
                    DROP COLUMN IF EXISTS logiciel_detecte,
                    DROP COLUMN IF EXISTS version_norme_detectee,
                    DROP COLUMN IF EXISTS dpe_classe_energie,
                    DROP COLUMN IF EXISTS dpe_classe_ges,
                    DROP COLUMN IF EXISTS dpe_conso_ep,
                    DROP COLUMN IF EXISTS dpe_emission_ges,
                    DROP COLUMN IF EXISTS dpe_surface_ref,
                    DROP COLUMN IF EXISTS dpe_date_visite,
                    DROP COLUMN IF EXISTS dpe_diagnostiqueur,
                    DROP COLUMN IF EXISTS obs_toiture_etat,
                    DROP COLUMN IF EXISTS obs_toiture_age,
                    DROP COLUMN IF EXISTS obs_toiture_notes,
                    DROP COLUMN IF EXISTS obs_facade_etat,
                    DROP COLUMN IF EXISTS obs_facade_isolation,
                    DROP COLUMN IF EXISTS obs_facade_notes,
                    DROP COLUMN IF EXISTS obs_menuiseries_type,
                    DROP COLUMN IF EXISTS obs_menuiseries_etat,
                    DROP COLUMN IF EXISTS obs_menuiseries_notes,
                    DROP COLUMN IF EXISTS obs_chauffage_type,
                    DROP COLUMN IF EXISTS obs_chauffage_age,
                    DROP COLUMN IF EXISTS obs_chauffage_etat,
                    DROP COLUMN IF EXISTS obs_plomberie_etat,
                    DROP COLUMN IF EXISTS obs_ecs_age,
                    DROP COLUMN IF EXISTS obs_elec_etat,
                    DROP COLUMN IF EXISTS obs_vmc_type,
                    DROP COLUMN IF EXISTS obs_vmc_etat,
                    DROP COLUMN IF EXISTS obs_humidite,
                    DROP COLUMN IF EXISTS obs_fissures,
                    DROP COLUMN IF EXISTS obs_risques_notes,
                    DROP COLUMN IF EXISTS obs_cout_toiture,
                    DROP COLUMN IF EXISTS obs_cout_isolation,
                    DROP COLUMN IF EXISTS obs_cout_chauffage,
                    DROP COLUMN IF EXISTS obs_cout_menuiseries,
                    DROP COLUMN IF EXISTS obs_cout_plomberie,
                    DROP COLUMN IF EXISTS obs_cout_autres,
                    DROP COLUMN IF EXISTS obs_conso_kwh,
                    DROP COLUMN IF EXISTS obs_cout_energie,
                    DROP COLUMN IF EXISTS obs_classe_dpe,
                    DROP COLUMN IF EXISTS obs_potentiel_economies;

                ALTER TABLE main_documentfile
                    DROP COLUMN IF EXISTS type_rapport_detecte,
                    DROP COLUMN IF EXISTS extraction_ok,
                    DROP COLUMN IF EXISTS extraction_json;
            """,
        ),
    ]
