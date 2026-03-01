from django import template

register = template.Library()

# Seul critère où une valeur HAUTE est bonne (plus d'ENR = mieux)
CRITERIA_GREATER_EQUAL = {
    'rt2012_enr',
}

# Tous les autres : valeur doit être INFÉRIEURE au seuil (moins = mieux)
CRITERIA_LOWER_EQUAL = {
    're2020_energy_efficiency',
    're2020_thermal_comfort',    # DH : degrés-heures, dépasser le seuil = non conforme
    're2020_carbon_emissions',
    're2020_water_management',
    're2020_indoor_air_quality', # Qai : dépasser le seuil = non conforme
    'rt2012_bbio',
    'rt2012_cep',
    'rt2012_tic',
    'rt2012_airtightness',
}

SEUILS = {
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

@register.filter
def is_conform_adapted(value, key):
    if value is None:
        return False
    limit = SEUILS.get(key)
    if limit is None:
        return False
    try:
        val = float(value)
    except (ValueError, TypeError):
        return False

    if key in CRITERIA_GREATER_EQUAL:
        return val >= limit
    elif key in CRITERIA_LOWER_EQUAL:
        return val <= limit
    else:
        return False
