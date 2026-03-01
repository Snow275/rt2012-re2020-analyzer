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
        ("recu", "Reçu"),
        ("en_cours", "En cours d'analyse"),
        ("termine", "Terminé"),
    )

    BUILDING_TYPE_CHOICES = (
        ('maison',    'Maison individuelle'),
        ('collectif', 'Logement collectif'),
        ('erp',       'ERP (établissement public)'),
    )
    ZONE_CHOICES = (
        ('H1', 'H1 — Nord / altitude (climat froid)'),
        ('H2', 'H2 — Centre / Ouest (climat tempéré)'),
        ('H3', 'H3 — Sud / littoral méditerranéen'),
    )

    name = models.CharField(max_length=255)
    client_name = models.CharField(max_length=255, blank=True, default="")
    client_email = models.EmailField(blank=True, default="")
    building_type = models.CharField(max_length=20, choices=BUILDING_TYPE_CHOICES, default='maison')
    climate_zone = models.CharField(max_length=5, choices=ZONE_CHOICES, default='H2')
    upload = models.FileField(upload_to="documents/")
    upload_date = models.DateTimeField(auto_now_add=True)
    is_active = models.BooleanField(default=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="recu")
    tracking_token = models.CharField(max_length=64, unique=True, blank=True)

    # Champs RE2020
    re2020_energy_efficiency = models.FloatField(null=True, blank=True)
    re2020_thermal_comfort = models.FloatField(null=True, blank=True)
    re2020_carbon_emissions = models.FloatField(null=True, blank=True)
    re2020_water_management = models.FloatField(null=True, blank=True)
    re2020_indoor_air_quality = models.FloatField(null=True, blank=True)

    # Champs RT2012
    rt2012_bbio = models.FloatField(null=True, blank=True)
    rt2012_cep = models.FloatField(null=True, blank=True)
    rt2012_tic = models.FloatField(null=True, blank=True)
    rt2012_airtightness = models.FloatField(null=True, blank=True)
    rt2012_enr = models.FloatField(null=True, blank=True)

    def __str__(self):
        return self.name

    def save(self, *args, **kwargs):
        if not self.tracking_token:
            import secrets
            self.tracking_token = secrets.token_urlsafe(32)
        super().save(*args, **kwargs)

    @property
    def re2020_is_conform(self):
        fields = [
            self.re2020_energy_efficiency,
            self.re2020_thermal_comfort,
            self.re2020_carbon_emissions,
        ]
        if any(v is None for v in fields):
            return None
        from main.templatetags.conformity_tags import get_seuils
        s = get_seuils(self.building_type, self.climate_zone)
        return (
            self.re2020_energy_efficiency <= s['re2020_energy_efficiency'] and
            self.re2020_thermal_comfort   <= s['re2020_thermal_comfort'] and
            self.re2020_carbon_emissions  <= s['re2020_carbon_emissions']
        )

    @property
    def rt2012_is_conform(self):
        fields = [
            self.rt2012_bbio, self.rt2012_cep, self.rt2012_tic,
            self.rt2012_airtightness, self.rt2012_enr,
        ]
        if any(v is None for v in fields):
            return None
        from main.templatetags.conformity_tags import get_seuils
        s = get_seuils(self.building_type, self.climate_zone)
        return (
            self.rt2012_bbio         <= s['rt2012_bbio'] and
            self.rt2012_cep          <= s['rt2012_cep'] and
            self.rt2012_tic          <= s['rt2012_tic'] and
            self.rt2012_airtightness <= s['rt2012_airtightness'] and
            self.rt2012_enr          >= s['rt2012_enr']
        )


class Analysis(models.Model):
    document = models.ForeignKey(Document, on_delete=models.CASCADE, related_name="analyses")
    standard = models.ForeignKey(Standard, on_delete=models.CASCADE, null=True, blank=True, related_name="analyses")
    criteria = models.CharField(max_length=255)
    value = models.FloatField()
    requirement = models.FloatField()
    compliance = models.BooleanField()

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
        ('maison',     'Maison individuelle'),
        ('collectif',  'Logement collectif'),
        ('tertiaire',  'Bâtiment tertiaire'),
        ('autre',      'Autre'),
    ]

    # Client
    client_nom   = models.CharField(max_length=255)
    client_email = models.EmailField()
    client_phone = models.CharField(max_length=30, blank=True, default='')

    # Projet
    projet_nom   = models.CharField(max_length=255, blank=True, default='')
    type_batiment = models.CharField(max_length=20, choices=TYPE_CHOICES, default='maison')
    norme        = models.CharField(max_length=20, choices=[('RT2012','RT2012'),('RE2020','RE2020'),('Les deux','Les deux')], default='RE2020')

    # Devis
    montant      = models.DecimalField(max_digits=8, decimal_places=2, null=True, blank=True)
    statut       = models.CharField(max_length=20, choices=STATUT_CHOICES, default='en_attente')
    notes        = models.TextField(blank=True, default='')

    # Dates
    created_at   = models.DateTimeField(auto_now_add=True)
    updated_at   = models.DateTimeField(auto_now=True)

    # Lien optionnel avec un dossier
    document     = models.ForeignKey(Document, on_delete=models.SET_NULL, null=True, blank=True, related_name='devis')

    class Meta:
        ordering = ['-created_at']
        verbose_name = 'Devis'
        verbose_name_plural = 'Devis'

    def __str__(self):
        return f"Devis {self.id} — {self.client_nom}"
