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
    name = models.CharField(max_length=255)
    upload = models.FileField(upload_to="documents/")
    upload_date = models.DateTimeField(auto_now_add=True)
    is_active = models.BooleanField(default=True)

    energy_efficiency = models.FloatField(null=True, blank=True)
    thermal_comfort = models.FloatField(null=True, blank=True)
    carbon_emissions = models.FloatField(null=True, blank=True)
    water_management = models.FloatField(null=True, blank=True)
    indoor_air_quality = models.FloatField(null=True, blank=True)

    def __str__(self):
        return self.name


class Analysis(models.Model):
    document = models.ForeignKey(Document, on_delete=models.CASCADE)
    standard = models.ForeignKey(Standard, on_delete=models.CASCADE)

    criteria = models.CharField(max_length=255)
    value = models.FloatField()
    requirement = models.FloatField()
    compliance = models.BooleanField()

    def __str__(self):
        return f"{self.document.name} - {self.criteria}"
