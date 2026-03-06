from django.contrib import admin
from .models import Document, Analysis, Devis, Standard


# ── DOCUMENT ────────────────────────────────────────────────────────────────

@admin.register(Document)
class DocumentAdmin(admin.ModelAdmin):
    list_display  = ('name', 'client_name', 'norme', 'pays', 'status', 'is_conform_display', 'upload_date')
    list_filter   = ('status', 'norme', 'pays', 'building_type')
    search_fields = ('name', 'client_name', 'client_email')
    readonly_fields = ('tracking_token', 'upload_date', 'is_conform_display')
    ordering      = ('-upload_date',)

    fieldsets = (
        ('Informations générales', {
            'fields': ('name', 'client_name', 'client_email', 'admin_notes',
                       'building_type', 'climate_zone', 'pays', 'norme',
                       'status', 'upload', 'rapport_pdf', 'tracking_token', 'is_active')
        }),
        ('Valeurs RT2012', {
            'classes': ('collapse',),
            'fields': ('rt2012_bbio', 'rt2012_cep', 'rt2012_tic',
                       'rt2012_airtightness', 'rt2012_enr'),
        }),
        ('Valeurs RE2020', {
            'classes': ('collapse',),
            'fields': ('re2020_energy_efficiency', 're2020_thermal_comfort',
                       're2020_carbon_emissions', 're2020_water_management',
                       're2020_indoor_air_quality'),
        }),
        ('Valeurs PEB (Belgique)', {
            'classes': ('collapse',),
            'fields': ('peb_espec', 'peb_ew', 'peb_u_mur',
                       'peb_u_toit', 'peb_u_plancher'),
        }),
        ('Valeurs Minergie / SIA380 (Suisse)', {
            'classes': ('collapse',),
            'fields': ('minergie_qh', 'minergie_qtot', 'minergie_n50', 'sia380_qh'),
        }),
        ('Valeurs CNEB (Canada)', {
            'classes': ('collapse',),
            'fields': ('cneb_ei', 'cneb_u_mur', 'cneb_u_toit',
                       'cneb_u_fenetre', 'cneb_infiltration'),
        }),
        ('Valeurs LENOZ (Luxembourg)', {
            'classes': ('collapse',),
            'fields': ('lenoz_ep', 'lenoz_ew', 'lenoz_u_mur', 'lenoz_u_toit'),
        }),
    )

    @admin.display(description='Conforme ?', boolean=True)
    def is_conform_display(self, obj):
        return obj.is_conform


# ── DEVIS ────────────────────────────────────────────────────────────────────

@admin.register(Devis)
class DevisAdmin(admin.ModelAdmin):
    list_display  = ('id', 'client_nom', 'projet_nom', 'norme', 'montant', 'statut', 'created_at')
    list_filter   = ('statut', 'norme', 'type_batiment')
    search_fields = ('client_nom', 'client_email', 'projet_nom')
    ordering      = ('-created_at',)
    readonly_fields = ('created_at', 'updated_at')


# ── ANALYSIS ─────────────────────────────────────────────────────────────────

@admin.register(Analysis)
class AnalysisAdmin(admin.ModelAdmin):
    list_display  = ('document', 'criteria', 'value', 'requirement', 'compliance')
    list_filter   = ('compliance',)
    search_fields = ('document__name', 'criteria')


# ── STANDARD ─────────────────────────────────────────────────────────────────

@admin.register(Standard)
class StandardAdmin(admin.ModelAdmin):
    list_display = ('name', 'type')
    list_filter  = ('type',)
