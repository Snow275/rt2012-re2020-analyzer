from django import template

register = template.Library()

@register.filter
def is_conform(value, limit):
    try:
        return float(value) >= float(limit)  # inversé : valeur ≥ seuil = conforme
    except (ValueError, TypeError):
        return False
