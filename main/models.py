from django.db import models


class Standard(models.Model):
    TYPE_CHOICES = (
        ("RE2020", "RE2020"),
        ("RT2012", "RT2012"),
    )
    name = models.CharField(max_length=100)
    type = models.CharField(max_length=10, choices=TYPE_CHOICES)
    energy_efficiency = models.FloatField()
    thermal_comfort = models.FloatField()
    carbon_emissions = models.FloatField()
    water_management = models.FloatField()
    indoor_air_quality = models.FloatField()

    def __str__(self):
        return f"{self.name} ({self.type})"


class Document(models.Model):
    STATUS_CHOICES = (
        ("recu",     "Reçu"),
        ("en_cours", "En cours d'analyse"),
        ("termine",  "Terminé"),
    )
    BUILDING_TYPE_CHOICES = (
        ('maison',    'Maison individuelle'),
        ('collectif', 'Logement collectif'),
        ('erp',       'ERP (établissement public)'),
    )
    ZONE_CHOICES = (
        # France
        ('H1', 'H1 — Nord / altitude (climat froid)'),
        ('H2', 'H2 — Centre / Ouest (climat tempéré)'),
        ('H3', 'H3 — Sud / littoral méditerranéen'),
        # Belgique
        ('BE-I',   'Zone I — Côtière (Belgique)'),
        ('BE-II',  'Zone II — Centrale (Belgique)'),
        ('BE-III', 'Zone III — Ardennaise (Belgique)'),
        # Suisse
        ('CH-I',   'Zone I — Genève / Tessin'),
        ('CH-II',  'Zone II — Plateau'),
        ('CH-III', 'Zone III — Préalpes'),
        ('CH-IV',  'Zone IV — Alpes'),
        ('CH-V',   'Zone V — Haute montagne'),
        ('CH-VI',  'Zone VI — Très haute altitude'),
        # Canada
        ('CA-4',  'Zone 4 — Vancouver / Victoria'),
        ('CA-5',  'Zone 5 — Toronto / Montréal'),
        ('CA-6',  'Zone 6 — Ottawa / Québec'),
        ('CA-7',  'Zone 7a — Winnipeg / Edmonton'),
        ('CA-7b', 'Zone 7b — Territoires du Nord'),
        ('CA-8',  'Zone 8 — Grand Nord'),
        # Luxembourg
        ('LU-A', 'Zone A — Vallée de la Moselle'),
        ('LU-B', 'Zone B — Plateau central'),
    )
    PAYS_CHOICES = (
        ('FR', '🇫🇷 France'),
        ('BE', '🇧🇪 Belgique'),
        ('CH', '🇨🇭 Suisse'),
        ('CA', '🇨🇦 Canada'),
        ('LU', '🇱🇺 Luxembourg'),
    )
    NORME_CHOICES = (
        ('RT2012',   'RT2012'),
        ('RE2020',   'RE2020'),
        ('PEB',      'PEB'),
        ('MINERGIE', 'Minergie'),
        ('SIA380',   'SIA 380'),
        ('CNEB2015', 'CNEB 2015'),
        ('CNEB2020', 'CNEB 2020'),
        ('LENOZ',    'LENOZ'),
    )
    TYPE_ANALYSE_CHOICES = (
        ('energie', 'Validation thermique & énergétique'),
        ('carbone', 'Bilan carbone immobilier'),
    )

    # ── Nouveau : type de rapport détecté automatiquement ──────────────
    TYPE_RAPPORT_CHOICES = (
        ('inconnu',           'Non détecté'),
        ('climawin_rt2012',   'Climawin — RT2012'),
        ('climawin_re2020',   'Climawin — RE2020'),
        ('pleiades_rt2012',   'Pléiades — RT2012'),
        ('pleiades_re2020',   'Pléiades — RE2020'),
        ('dpe',               'DPE'),
        ('attestation_rt2012','Attestation RT2012'),
        ('attestation_re2020','Attestation RE2020'),
        ('etude_thermique',   'Étude thermique générique'),
        ('facture',           'Facture énergie'),
        ('autre',             'Autre document'),
    )

    name          = models.CharField(max_length=255)
    client_name   = models.CharField(max_length=255, blank=True, default="")
    client_email  = models.EmailField(blank=True, default="")
    admin_notes   = models.TextField(blank=True, default="")
    building_type = models.CharField(max_length=20, choices=BUILDING_TYPE_CHOICES, default='maison')
    climate_zone  = models.CharField(max_length=6,  choices=ZONE_CHOICES, default='H2')
    upload        = models.FileField(upload_to="documents/")
    upload_date   = models.DateTimeField(auto_now_add=True)
    is_active     = models.BooleanField(default=True)
    status        = models.CharField(max_length=20, choices=STATUS_CHOICES, default="recu")
    tracking_token= models.CharField(max_length=64, unique=True, blank=True)
    rapport_pdf   = models.FileField(upload_to="rapports/", null=True, blank=True)
    pays          = models.CharField(max_length=5,  choices=PAYS_CHOICES, default="FR")
    norme         = models.CharField(max_length=10, choices=NORME_CHOICES, default="RE2020")

    # ── Infos bâtiment ─────────────────────────────────────────────────
    surface_totale     = models.FloatField(null=True, blank=True)
    annee_construction = models.IntegerField(null=True, blank=True)
    nombre_logements   = models.IntegerField(null=True, blank=True)
    type_analyse       = models.CharField(max_length=10, choices=TYPE_ANALYSE_CHOICES, default='energie')

    # ── Rapport IA sauvegardé ──────────────────────────────────────────
    rapport_ia_json = models.TextField(null=True, blank=True)

    # ── Type de rapport détecté + métadonnées extraction ──────────────
    type_rapport         = models.CharField(max_length=30, choices=TYPE_RAPPORT_CHOICES, default='inconnu')
    extraction_ok        = models.BooleanField(default=False)
    extraction_json      = models.JSONField(null=True, blank=True)   # résumé brut extrait par Claude
    extraction_alertes   = models.JSONField(null=True, blank=True)   # liste d'alertes de cohérence
    logiciel_detecte     = models.CharField(max_length=100, blank=True, default='')  # ex: "Climawin v4.2"
    version_norme_detectee = models.CharField(max_length=50, blank=True, default='') # ex: "RT2012 - Arrêté 2010"

    # ── Champs RE2020 ──────────────────────────────────────────────────
    re2020_energy_efficiency  = models.FloatField(null=True, blank=True)
    re2020_thermal_comfort    = models.FloatField(null=True, blank=True)
    re2020_carbon_emissions   = models.FloatField(null=True, blank=True)
    re2020_water_management   = models.FloatField(null=True, blank=True)
    re2020_indoor_air_quality = models.FloatField(null=True, blank=True)

    # ── Champs RT2012 ──────────────────────────────────────────────────
    rt2012_bbio         = models.FloatField(null=True, blank=True)
    rt2012_cep          = models.FloatField(null=True, blank=True)
    rt2012_tic          = models.FloatField(null=True, blank=True)
    rt2012_airtightness = models.FloatField(null=True, blank=True)
    rt2012_enr          = models.FloatField(null=True, blank=True)

    # ── Champs PEB (Belgique) ──────────────────────────────────────────
    peb_espec     = models.FloatField(null=True, blank=True)
    peb_ew        = models.FloatField(null=True, blank=True)
    peb_u_mur     = models.FloatField(null=True, blank=True)
    peb_u_toit    = models.FloatField(null=True, blank=True)
    peb_u_plancher= models.FloatField(null=True, blank=True)

    # ── Champs Minergie / SIA380 (Suisse) ─────────────────────────────
    minergie_qh   = models.FloatField(null=True, blank=True)
    minergie_qtot = models.FloatField(null=True, blank=True)
    minergie_n50  = models.FloatField(null=True, blank=True)
    sia380_qh     = models.FloatField(null=True, blank=True)

    # ── Champs CNEB (Canada) ───────────────────────────────────────────
    cneb_ei          = models.FloatField(null=True, blank=True)
    cneb_u_mur       = models.FloatField(null=True, blank=True)
    cneb_u_toit      = models.FloatField(null=True, blank=True)
    cneb_u_fenetre   = models.FloatField(null=True, blank=True)
    cneb_infiltration= models.FloatField(null=True, blank=True)

    # ── Champs LENOZ (Luxembourg) ──────────────────────────────────────
    lenoz_ep    = models.FloatField(null=True, blank=True)
    lenoz_ew    = models.FloatField(null=True, blank=True)
    lenoz_u_mur = models.FloatField(null=True, blank=True)
    lenoz_u_toit= models.FloatField(null=True, blank=True)

    # ── Champs DPE ────────────────────────────────────────────────────
    dpe_classe_energie  = models.CharField(max_length=1, blank=True, default='')  # A à G
    dpe_classe_ges      = models.CharField(max_length=1, blank=True, default='')  # A à G
    dpe_conso_ep        = models.FloatField(null=True, blank=True)   # kWh ep/m².an
    dpe_emission_ges    = models.FloatField(null=True, blank=True)   # kgCO2eq/m².an
    dpe_surface_ref     = models.FloatField(null=True, blank=True)   # m²
    dpe_date_visite     = models.CharField(max_length=20, blank=True, default='')
    dpe_diagnostiqueur  = models.CharField(max_length=255, blank=True, default='')


    def __str__(self):
        return self.name

    def save(self, *args, **kwargs):
        if not self.tracking_token:
            import secrets
            self.tracking_token = secrets.token_urlsafe(32)
        super().save(*args, **kwargs)

    @property
    def is_conform(self):
        from main.templatetags.conformity_tags import get_seuils, NORME_FIELDS, CRITERIA_GREATER_EQUAL
        norme_fields = NORME_FIELDS.get(self.norme, [])
        if not norme_fields:
            return None
        s = get_seuils(self.building_type, self.climate_zone, self.pays, self.norme)
        for field, _, _ in norme_fields:
            val = getattr(self, field, None)
            if val is None:
                return None
            limit = s.get(field)
            if limit is None:
                continue
            if field in CRITERIA_GREATER_EQUAL:
                if float(val) < limit:
                    return False
            else:
                if float(val) > limit:
                    return False
        return True

    @property
    def re2020_is_conform(self):
        return self.is_conform if self.norme == 'RE2020' else None

    @property
    def rt2012_is_conform(self):
        return self.is_conform if self.norme == 'RT2012' else None

    @property
    def type_rapport_label(self):
        return dict(self.TYPE_RAPPORT_CHOICES).get(self.type_rapport, 'Non détecté')

    @property
    def has_dpe(self):
        return bool(self.dpe_classe_energie)


class FactureEnergie(models.Model):
    ENERGIE_CHOICES = [
        ('electricite', 'Électricité'),
        ('gaz',         'Gaz naturel'),
    ]
    document      = models.ForeignKey(Document, on_delete=models.CASCADE, related_name='factures')
    fichier       = models.FileField(upload_to='factures/%Y/%m/')
    nom           = models.CharField(max_length=255, blank=True)
    type_energie  = models.CharField(max_length=20, choices=ENERGIE_CHOICES, default='electricite')
    uploaded_at   = models.DateTimeField(auto_now_add=True)
    analyse_json  = models.JSONField(null=True, blank=True)
    analyse_ok    = models.BooleanField(default=False)
    analyse_error = models.TextField(blank=True)

    class Meta:
        ordering = ['uploaded_at']

    def save(self, *args, **kwargs):
        if not self.nom and self.fichier:
            self.nom = self.fichier.name.split('/')[-1]
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.nom} ({self.document})"

    @property
    def donnees(self):
        return self.analyse_json or {}


class DocumentFile(models.Model):
    TYPE_CHOICES = [
        ("document",        "Document"),
        ("etude_thermique", "Étude thermique"),
        ("dpe",             "DPE"),
        ("attestation",     "Attestation de conformité"),
        ("climawin",        "Rapport Climawin"),
        ("pleiades",        "Rapport Pléiades"),
    ]
    document     = models.ForeignKey(Document, on_delete=models.CASCADE, related_name='fichiers')
    fichier      = models.FileField(upload_to='documents/')
    nom          = models.CharField(max_length=255, blank=True)
    taille       = models.IntegerField(null=True, blank=True)
    type_fichier = models.CharField(max_length=50, choices=TYPE_CHOICES, default="document")
    uploaded_at  = models.DateTimeField(auto_now_add=True)

    # ── Résultat de l'analyse de ce fichier spécifique ────────────────
    type_rapport_detecte = models.CharField(max_length=30, blank=True, default='')
    extraction_ok        = models.BooleanField(default=False)
    extraction_json      = models.JSONField(null=True, blank=True)

    def save(self, *args, **kwargs):
        if not self.nom and self.fichier:
            self.nom = self.fichier.name.split('/')[-1]
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.document.name} — {self.nom}"


class SiteSettings(models.Model):
    """
    Paramètres globaux du site — singleton (une seule ligne en base).
    Accessible depuis l'admin Django.
    """
    maintenance_mode = models.BooleanField(
        default=False,
        verbose_name="Mode maintenance",
        help_text="Activer pour afficher la page de maintenance à tous les visiteurs (sauf admins).",
    )
    maintenance_message = models.TextField(
        blank=True,
        default="Nous effectuons des mises à jour pour améliorer votre expérience. Nous serons de retour très bientôt.",
        verbose_name="Message affiché",
    )
    maintenance_title = models.CharField(
        max_length=200,
        blank=True,
        default="Site en maintenance",
        verbose_name="Titre affiché",
    )

    class Meta:
        verbose_name = "Paramètres du site"
        verbose_name_plural = "Paramètres du site"

    def __str__(self):
        status = "🔴 EN MAINTENANCE" if self.maintenance_mode else "🟢 En ligne"
        return f"Paramètres du site — {status}"

    @classmethod
    def get_solo(cls):
        obj, _ = cls.objects.get_or_create(pk=1)
        return obj

    def save(self, *args, **kwargs):
        self.pk = 1
        super().save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        pass  # Empêcher la suppression


class Analysis(models.Model):
    document    = models.ForeignKey(Document, on_delete=models.CASCADE, related_name="analyses")
    standard    = models.ForeignKey(Standard, on_delete=models.CASCADE, null=True, blank=True, related_name="analyses")
    criteria    = models.CharField(max_length=255)
    value       = models.FloatField()
    requirement = models.FloatField()
    compliance  = models.BooleanField()

    def __str__(self):
        return f"{self.document.name} - {self.criteria}"


class Devis(models.Model):
    STATUT_CHOICES = [
        ('en_attente', 'En attente'),
        ('accepte',    'Accepté'),
        ('refuse',     'Refusé'),
        ('facture',    'Facturé'),
    ]
    TYPE_CHOICES = [
        ('maison',    'Maison individuelle'),
        ('collectif', 'Logement collectif'),
        ('tertiaire', 'Bâtiment tertiaire'),
        ('autre',     'Autre'),
    ]

    client_nom    = models.CharField(max_length=255)
    client_email  = models.EmailField()
    client_phone  = models.CharField(max_length=30, blank=True, default='')
    projet_nom    = models.CharField(max_length=255, blank=True, default='')
    type_batiment = models.CharField(max_length=20, choices=TYPE_CHOICES, default='maison')
    norme         = models.CharField(max_length=20, choices=[('RT2012','RT2012'),('RE2020','RE2020'),('Les deux','Les deux')], default='RE2020')
    montant       = models.DecimalField(max_digits=8, decimal_places=2, null=True, blank=True)
    statut        = models.CharField(max_length=20, choices=STATUT_CHOICES, default='en_attente')
    notes         = models.TextField(blank=True, default='')
    motif_refus   = models.TextField(blank=True, default='', verbose_name='Motif de refus')
    created_at    = models.DateTimeField(auto_now_add=True)
    updated_at    = models.DateTimeField(auto_now=True)
    document      = models.ForeignKey(Document, on_delete=models.SET_NULL, null=True, blank=True, related_name='devis')

    class Meta:
        ordering = ['-created_at']
        verbose_name = 'Devis'
        verbose_name_plural = 'Devis'

    def __str__(self):
        return f"Devis {self.id} — {self.client_nom}"


class Message(models.Model):
    AUTEUR_CHOICES = [
        ('admin',  'ConformExpert'),
        ('client', 'Client'),
    ]

    document    = models.ForeignKey(Document, on_delete=models.CASCADE, related_name='messages')
    auteur      = models.CharField(max_length=10, choices=AUTEUR_CHOICES, default='admin')
    contenu     = models.TextField()
    fichier     = models.FileField(upload_to='messages/', blank=True, null=True)
    fichier_nom = models.CharField(max_length=255, blank=True, default='')
    lu_admin    = models.BooleanField(default=False)
    lu_client   = models.BooleanField(default=False)
    created_at  = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['created_at']
        verbose_name = 'Message'
        verbose_name_plural = 'Messages'

    def __str__(self):
        return f"[{self.get_auteur_display()}] {self.document.name} — {self.created_at:%d/%m/%Y %H:%M}"
