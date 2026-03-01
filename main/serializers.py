from rest_framework import serializers
from .models import Document, Analysis


class AnalysisSerializer(serializers.ModelSerializer):
    class Meta:
        model = Analysis
        fields = '__all__'


class DocumentSerializer(serializers.ModelSerializer):
    analyses = AnalysisSerializer(many=True, read_only=True)
    re2020_is_conform = serializers.SerializerMethodField()
    rt2012_is_conform = serializers.SerializerMethodField()

    class Meta:
        model = Document
        fields = [
            'id', 'name', 'client_name', 'client_email',
            'upload_date', 'status', 'tracking_token',
            're2020_energy_efficiency', 're2020_thermal_comfort',
            're2020_carbon_emissions', 're2020_water_management',
            're2020_indoor_air_quality',
            'rt2012_bbio', 'rt2012_cep', 'rt2012_tic',
            'rt2012_airtightness', 'rt2012_enr',
            're2020_is_conform', 'rt2012_is_conform',
            'analyses',
        ]

    def get_re2020_is_conform(self, obj):
        return obj.re2020_is_conform

    def get_rt2012_is_conform(self, obj):
        return obj.rt2012_is_conform
