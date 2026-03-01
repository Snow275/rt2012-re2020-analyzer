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

    name = models.CharField(max_length=255)
    client_name = models.CharField(max_length=255, blank=True, default="")
    client_email = models.EmailField(blank=True, default="")
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
        req = {
            'energy_efficiency': 80.0,
            'thermal_comfort': 85.0,
            'carbon_emissions': 75.0,
            'water_management': 70.0,
            'indoor_air_quality': 75.0,
        }
        fields = [
            self.re2020_energy_efficiency,
            self.re2020_thermal_comfort,
            self.re2020_carbon_emissions,
            self.re2020_water_management,
            self.re2020_indoor_air_quality,
        ]
        if any(v is None for v in fields):
            return None
        return (
            self.re2020_energy_efficiency <= req['energy_efficiency'] and
            self.re2020_thermal_comfort <= req['thermal_comfort'] and
            self.re2020_carbon_emissions <= req['carbon_emissions'] and
            self.re2020_water_management <= req['water_management'] and
            self.re2020_indoor_air_quality <= req['indoor_air_quality']
        )

    @property
    def rt2012_is_conform(self):
        req = {'bbio': 50.0, 'cep': 50.0, 'tic': 27.0, 'airtightness': 0.6, 'enr': 1.0}
        fields = [
            self.rt2012_bbio, self.rt2012_cep, self.rt2012_tic,
            self.rt2012_airtightness, self.rt2012_enr,
        ]
        if any(v is None for v in fields):
            return None
        return (
            self.rt2012_bbio <= req['bbio'] and
            self.rt2012_cep <= req['cep'] and
            self.rt2012_tic <= req['tic'] and
            self.rt2012_airtightness <= req['airtightness'] and
            self.rt2012_enr >= req['enr']
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
