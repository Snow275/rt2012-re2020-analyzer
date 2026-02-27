from django import template

register = template.Library()

@register.filter
def is_conform(value, limit):
    try:
        return float(value) <= float(limit)
    except (ValueError, TypeError):
        return False
