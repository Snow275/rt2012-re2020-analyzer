import os
from django.shortcuts import render


class MaintenanceMiddleware:
    """
    Middleware de maintenance.
    Priorité : variable d'env MAINTENANCE_MODE > paramètre en base (SiteSettings).
    Les superusers Django peuvent toujours accéder au site.
    """

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if self._is_maintenance_active():
            # Superusers peuvent bypasser
            if request.user.is_authenticated and request.user.is_superuser:
                return self.get_response(request)

            # Laisser passer l'admin Django (pour pouvoir désactiver la maintenance)
            if request.path.startswith('/admin/'):
                return self.get_response(request)

            # Retourner la page de maintenance (503 Service Unavailable)
            return render(request, 'main/maintenance.html', status=503)

        return self.get_response(request)

    def _is_maintenance_active(self):
        # 1. Variable d'environnement (priorité absolue)
        env_flag = os.environ.get('MAINTENANCE_MODE', '').strip().lower()
        if env_flag == 'true':
            return True
        if env_flag == 'false':
            return False

        # 2. Paramètre en base via SiteSettings
        try:
            from .models import SiteSettings
            settings = SiteSettings.get_solo()
            return settings.maintenance_mode
        except Exception:
            return False
