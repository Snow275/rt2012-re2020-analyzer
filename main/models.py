from django.db import models

class Document(models.Model):
    name = models.CharField(max_length=255)
    upload = models.FileField(upload_to='documents/')
    upload_date = models.DateTimeField(auto_now_add=True)
    is_active = models.BooleanField(default=True)
    analysis_result = models.JSONField(null=True, blank=True)

    # RT 2012 fields
    rt2012_energy_efficiency = models.FloatField(default=50.0)
    rt2012_thermal_comfort = models.FloatField(default=22.0)
    rt2012_carbon_emissions = models.FloatField(default=35.0)
    rt2012_water_management = models.FloatField(default=120.0)
    rt2012_indoor_air_quality = models.FloatField(default=800.0)

    # RE2020 fields
    re2020_energy_efficiency = models.FloatField(default=80.0)
    re2020_thermal_comfort = models.FloatField(default=85.0)
    re2020_carbon_emissions = models.FloatField(default=75.0)
    re2020_water_management = models.FloatField(default=70.0)
    re2020_indoor_air_quality = models.FloatField(default=75.0)

    def __str__(self):
        return self.name

class Analysis(models.Model):
    document = models.ForeignKey(Document, on_delete=models.CASCADE)
    criteria = models.CharField(max_length=255)
    value = models.FloatField()
    requirement = models.FloatField()
    compliance = models.BooleanField()

class Standard(models.Model):
    name = models.CharField(max_length=100)
    energy_efficiency = models.FloatField()
    thermal_comfort = models.FloatField()
    carbon_emissions = models.FloatField()
    water_management = models.FloatField()
    indoor_air_quality = models.FloatField()

    def __str__(self):
        return self.name


