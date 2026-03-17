from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    """
    Migration de synchronisation d'état uniquement.
    La base de données est déjà à jour via les migrations RunSQL précédentes.
    Cette migration informe seulement Django ORM de l'état actuel des modèles
    sans exécuter aucun SQL (SeparateDatabaseAndState).
    """

    dependencies = [
        ('main', '0011_sitesettings_bigautofield'),
    ]

    operations = [
        migrations.SeparateDatabaseAndState(
            database_operations=[],  # Aucune opération SQL — la base est déjà à jour
            state_operations=[

                # ── Standard ──────────────────────────────────────────────
                migrations.CreateModel(
                    name='Standard',
                    fields=[
                        ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                        ('name', models.CharField(max_length=100)),
                        ('type', models.CharField(choices=[('RE2020', 'RE2020'), ('RT2012', 'RT2012')], max_length=10)),
                        ('energy_efficiency', models.FloatField()),
                        ('thermal_comfort', models.FloatField()),
                        ('carbon_emissions', models.FloatField()),
                        ('water_management', models.FloatField()),
                        ('indoor_air_quality', models.FloatField()),
                    ],
                ),

                # ── Document ──────────────────────────────────────────────
                migrations.CreateModel(
                    name='Document',
                    fields=[
                        ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                        ('name', models.CharField(max_length=255)),
                        ('client_name', models.CharField(blank=True, default='', max_length=255)),
                        ('client_email', models.EmailField(blank=True, default='')),
                        ('admin_notes', models.TextField(blank=True, default='')),
                        ('building_type', models.CharField(default='maison', max_length=20)),
                        ('climate_zone', models.CharField(default='H2', max_length=6)),
                        ('upload', models.FileField(upload_to='documents/')),
                        ('upload_date', models.DateTimeField(auto_now_add=True)),
                        ('is_active', models.BooleanField(default=True)),
                        ('status', models.CharField(default='recu', max_length=20)),
                        ('tracking_token', models.CharField(blank=True, max_length=64, unique=True)),
                        ('rapport_pdf', models.FileField(blank=True, null=True, upload_to='rapports/')),
                        ('pays', models.CharField(default='FR', max_length=5)),
                        ('norme', models.CharField(default='RE2020', max_length=10)),
                        ('surface_totale', models.FloatField(blank=True, null=True)),
                        ('annee_construction', models.IntegerField(blank=True, null=True)),
                        ('nombre_logements', models.IntegerField(blank=True, null=True)),
                        ('type_analyse', models.CharField(default='energie', max_length=10)),
                        ('rapport_ia_json', models.TextField(blank=True, null=True)),
                        ('type_rapport', models.CharField(default='inconnu', max_length=30)),
                        ('extraction_ok', models.BooleanField(default=False)),
                        ('extraction_json', models.JSONField(blank=True, null=True)),
                        ('extraction_alertes', models.JSONField(blank=True, null=True)),
                        ('logiciel_detecte', models.CharField(blank=True, default='', max_length=100)),
                        ('version_norme_detectee', models.CharField(blank=True, default='', max_length=50)),
                        ('re2020_energy_efficiency', models.FloatField(blank=True, null=True)),
                        ('re2020_thermal_comfort', models.FloatField(blank=True, null=True)),
                        ('re2020_carbon_emissions', models.FloatField(blank=True, null=True)),
                        ('re2020_water_management', models.FloatField(blank=True, null=True)),
                        ('re2020_indoor_air_quality', models.FloatField(blank=True, null=True)),
                        ('rt2012_bbio', models.FloatField(blank=True, null=True)),
                        ('rt2012_cep', models.FloatField(blank=True, null=True)),
                        ('rt2012_tic', models.FloatField(blank=True, null=True)),
                        ('rt2012_airtightness', models.FloatField(blank=True, null=True)),
                        ('rt2012_enr', models.FloatField(blank=True, null=True)),
                        ('peb_espec', models.FloatField(blank=True, null=True)),
                        ('peb_ew', models.FloatField(blank=True, null=True)),
                        ('peb_u_mur', models.FloatField(blank=True, null=True)),
                        ('peb_u_toit', models.FloatField(blank=True, null=True)),
                        ('peb_u_plancher', models.FloatField(blank=True, null=True)),
                        ('minergie_qh', models.FloatField(blank=True, null=True)),
                        ('minergie_qtot', models.FloatField(blank=True, null=True)),
                        ('minergie_n50', models.FloatField(blank=True, null=True)),
                        ('sia380_qh', models.FloatField(blank=True, null=True)),
                        ('cneb_ei', models.FloatField(blank=True, null=True)),
                        ('cneb_u_mur', models.FloatField(blank=True, null=True)),
                        ('cneb_u_toit', models.FloatField(blank=True, null=True)),
                        ('cneb_u_fenetre', models.FloatField(blank=True, null=True)),
                        ('cneb_infiltration', models.FloatField(blank=True, null=True)),
                        ('lenoz_ep', models.FloatField(blank=True, null=True)),
                        ('lenoz_ew', models.FloatField(blank=True, null=True)),
                        ('lenoz_u_mur', models.FloatField(blank=True, null=True)),
                        ('lenoz_u_toit', models.FloatField(blank=True, null=True)),
                        ('dpe_classe_energie', models.CharField(blank=True, default='', max_length=1)),
                        ('dpe_classe_ges', models.CharField(blank=True, default='', max_length=1)),
                        ('dpe_conso_ep', models.FloatField(blank=True, null=True)),
                        ('dpe_emission_ges', models.FloatField(blank=True, null=True)),
                        ('dpe_surface_ref', models.FloatField(blank=True, null=True)),
                        ('dpe_date_visite', models.CharField(blank=True, default='', max_length=20)),
                        ('dpe_diagnostiqueur', models.CharField(blank=True, default='', max_length=255)),
                        ('obs_toiture_etat', models.CharField(blank=True, default='', max_length=20)),
                        ('obs_toiture_age', models.IntegerField(blank=True, null=True)),
                        ('obs_toiture_notes', models.TextField(blank=True, default='')),
                        ('obs_facade_etat', models.CharField(blank=True, default='', max_length=20)),
                        ('obs_facade_isolation', models.CharField(blank=True, default='', max_length=20)),
                        ('obs_facade_notes', models.TextField(blank=True, default='')),
                        ('obs_menuiseries_type', models.CharField(blank=True, default='', max_length=20)),
                        ('obs_menuiseries_etat', models.CharField(blank=True, default='', max_length=20)),
                        ('obs_menuiseries_notes', models.TextField(blank=True, default='')),
                        ('obs_chauffage_type', models.CharField(blank=True, default='', max_length=20)),
                        ('obs_chauffage_age', models.IntegerField(blank=True, null=True)),
                        ('obs_chauffage_etat', models.CharField(blank=True, default='', max_length=20)),
                        ('obs_plomberie_etat', models.CharField(blank=True, default='', max_length=20)),
                        ('obs_ecs_age', models.IntegerField(blank=True, null=True)),
                        ('obs_elec_etat', models.CharField(blank=True, default='', max_length=20)),
                        ('obs_vmc_type', models.CharField(blank=True, default='', max_length=20)),
                        ('obs_vmc_etat', models.CharField(blank=True, default='', max_length=20)),
                        ('obs_humidite', models.CharField(blank=True, default='', max_length=20)),
                        ('obs_fissures', models.CharField(blank=True, default='', max_length=20)),
                        ('obs_risques_notes', models.TextField(blank=True, default='')),
                        ('obs_cout_toiture', models.FloatField(blank=True, null=True)),
                        ('obs_cout_isolation', models.FloatField(blank=True, null=True)),
                        ('obs_cout_chauffage', models.FloatField(blank=True, null=True)),
                        ('obs_cout_menuiseries', models.FloatField(blank=True, null=True)),
                        ('obs_cout_plomberie', models.FloatField(blank=True, null=True)),
                        ('obs_cout_autres', models.FloatField(blank=True, null=True)),
                        ('obs_conso_kwh', models.FloatField(blank=True, null=True)),
                        ('obs_cout_energie', models.FloatField(blank=True, null=True)),
                        ('obs_classe_dpe', models.CharField(blank=True, default='', max_length=1)),
                        ('obs_potentiel_economies', models.CharField(blank=True, default='', max_length=20)),
                    ],
                ),

                # ── FactureEnergie ─────────────────────────────────────────
                migrations.CreateModel(
                    name='FactureEnergie',
                    fields=[
                        ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                        ('document', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='factures', to='main.document')),
                        ('fichier', models.FileField(upload_to='factures/%Y/%m/')),
                        ('nom', models.CharField(blank=True, max_length=255)),
                        ('type_energie', models.CharField(default='electricite', max_length=20)),
                        ('uploaded_at', models.DateTimeField(auto_now_add=True)),
                        ('analyse_json', models.JSONField(blank=True, null=True)),
                        ('analyse_ok', models.BooleanField(default=False)),
                        ('analyse_error', models.TextField(blank=True)),
                    ],
                    options={'ordering': ['uploaded_at']},
                ),

                # ── DocumentFile ───────────────────────────────────────────
                migrations.CreateModel(
                    name='DocumentFile',
                    fields=[
                        ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                        ('document', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='fichiers', to='main.document')),
                        ('fichier', models.FileField(upload_to='documents/')),
                        ('nom', models.CharField(blank=True, max_length=255)),
                        ('taille', models.IntegerField(blank=True, null=True)),
                        ('type_fichier', models.CharField(default='document', max_length=50)),
                        ('uploaded_at', models.DateTimeField(auto_now_add=True)),
                        ('type_rapport_detecte', models.CharField(blank=True, default='', max_length=30)),
                        ('extraction_ok', models.BooleanField(default=False)),
                        ('extraction_json', models.JSONField(blank=True, null=True)),
                    ],
                ),

                # ── Analysis ───────────────────────────────────────────────
                migrations.CreateModel(
                    name='Analysis',
                    fields=[
                        ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                        ('document', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='analyses', to='main.document')),
                        ('standard', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, related_name='analyses', to='main.standard')),
                        ('criteria', models.CharField(max_length=255)),
                        ('value', models.FloatField()),
                        ('requirement', models.FloatField()),
                        ('compliance', models.BooleanField()),
                    ],
                ),

                # ── Devis ──────────────────────────────────────────────────
                migrations.CreateModel(
                    name='Devis',
                    fields=[
                        ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                        ('client_nom', models.CharField(max_length=255)),
                        ('client_email', models.EmailField()),
                        ('client_phone', models.CharField(blank=True, default='', max_length=30)),
                        ('projet_nom', models.CharField(blank=True, default='', max_length=255)),
                        ('type_batiment', models.CharField(default='maison', max_length=20)),
                        ('norme', models.CharField(default='RE2020', max_length=20)),
                        ('montant', models.DecimalField(blank=True, decimal_places=2, max_digits=8, null=True)),
                        ('statut', models.CharField(default='en_attente', max_length=20)),
                        ('notes', models.TextField(blank=True, default='')),
                        ('created_at', models.DateTimeField(auto_now_add=True)),
                        ('updated_at', models.DateTimeField(auto_now=True)),
                        ('document', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='devis', to='main.document')),
                    ],
                    options={'ordering': ['-created_at'], 'verbose_name': 'Devis', 'verbose_name_plural': 'Devis'},
                ),
            ],
        ),
    ]
