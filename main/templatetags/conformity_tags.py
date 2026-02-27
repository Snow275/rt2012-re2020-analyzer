from django import template

register = template.Library()

criteria_gte = {
    're2020_indoor_air_quality': True,
    'rt2012_enr': True,
}

criteria_lte = {
    're2020_energy_efficiency': True,
    're2020_thermal_comfort': True,
    're2020_carbon_emissions': True,
    're2020_water_management': True,
    'rt2012_bbio': True,
    'rt2012_cep': True,
    'rt2012_tic': True,
    'rt2012_airtightness': True,
}

@register.filter
def is_conform_adapted(value, key):
    try:
        value = float(value)
    except (TypeError, ValueError):
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
