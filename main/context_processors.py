def site_settings(request):
    """
    Context processor — injecte les SiteSettings dans tous les templates.
    À ajouter dans settings.py > TEMPLATES > OPTIONS > context_processors.
    """
    try:
        from .models import SiteSettings
        return {'settings': SiteSettings.get_solo()}
    except Exception:
        return {'settings': None}
