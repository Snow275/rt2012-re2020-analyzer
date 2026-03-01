from django import template

register = template.Library()

CRITERIA_GREATER_EQUAL = {
    're2020_thermal_comfort',
    're2020_indoor_air_quality',
}

CRITERIA_LOWER_EQUAL = {
    're2020_energy_efficiency',
    're2020_carbon_emissions',
    're2020_water_management',
    # ajoute les autres critères qui se comparent par <=
}

@register.filter
def is_conform_adapted(value, key):
    seuils = { ... } # ta dict de seuils
    limit = seuils.get(key)
    if limit is None or value is None:
        return False
    try:
        val = float(value)
    except (ValueError, TypeError):
        return False
    if key in CRITERIA_GREATER_EQUAL:
        return val >= limit
    if key in CRITERIA_LOWER_EQUAL:
        return val <= limit
    return False

    # Change ici suivant ta façon de récupérer les seuils
    seuils = {
        're2020_energy_efficiency': 80.0,
        're2020_thermal_comfort': 85.0,
        're2020_carbon_emissions': 75.0,
        're2020_water_management': 70.0,
        're2020_indoor_air_quality': 75.0,
        'rt2012_bbio': 50.0,
        'rt2012_cep': 50.0,
        'rt2012_tic': 27.0,
        'rt2012_airtightness': 0.6,
        'rt2012_enr': 1.0,
    }

    limit = seuils.get(key)
    if limit is None:
        return False

    if key in criteria_gte:
        return value >= limit
    elif key in criteria_lte:
        return value <= limit
    else:
        return False
