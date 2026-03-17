from django.contrib import admin
from .models import SiteSettings


@admin.register(SiteSettings)
class SiteSettingsAdmin(admin.ModelAdmin):
    fieldsets = (
        ("🔧 Mode Maintenance", {
            "fields": ("maintenance_mode",),
            "description": (
                "<strong>⚠️ Attention :</strong> En activant la maintenance, "
                "tous les visiteurs (sauf les admins) verront la page de maintenance. "
                "Vous pouvez toujours accéder au site normalement."
            ),
        }),
        ("✏️ Contenu de la page", {
            "fields": ("maintenance_title", "maintenance_message"),
        }),
    )

    def has_add_permission(self, request):
        # Empêcher la création d'une 2e instance
        return not SiteSettings.objects.exists()

    def has_delete_permission(self, request, obj=None):
        return False

    def changelist_view(self, request, extra_context=None):
        # Rediriger directement vers l'édition de l'unique instance
        obj = SiteSettings.get_solo()
        from django.shortcuts import redirect
        return redirect(f'/admin/main/sitesettings/{obj.pk}/change/')
