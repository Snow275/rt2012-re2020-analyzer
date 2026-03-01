from django import template

register = template.Library()

# ──────────────────────────────────────────────
# SEUILS DYNAMIQUES
# Sources : RT2012 (arrêté 26/10/2010) + RE2020 (décret 2021-1004)
# ──────────────────────────────────────────────

RT2012_BBIO_BASE = {
    'maison':    60,
    'collectif': 80,
    'erp':       80,
}

RT2012_BBIO_ZONE_MODIF = {
    'H1': +10,
    'H2': 0,
    'H3': -10,
}

RT2012_CEP_MAX = {
    'maison':    50,
    'collectif': 50,
    'erp':       120,
}

RT2012_TIC_MAX = {
    'H1': 26,
    'H2': 27,
    'H3': 28,
}

RT2012_AIRTIGHTNESS_MAX = {
    'maison':    0.6,
    'collectif': 1.0,
    'erp':       1.0,
}

RT2012_ENR_MIN = 1.0

RE2020_CEP_MAX = {
    'maison':    100,
    'collectif': 100,
    'erp':       150,
}

RE2020_DH_MAX = {
    'H1': 1000,
    'H2': 1250,
    'H3': 1500,
}

RE2020_IC_ENERGIE_MAX = {
    'maison':    160,
    'collectif': 160,
    'erp':       250,
}

RE2020_IC_CONSTRUCTION_MAX = {
    'maison':    640,
    'collectif': 740,
    'erp':       840,
}

CRITERIA_GREATER_EQUAL = {'rt2012_enr'}

CRITERIA_LOWER_EQUAL = {
    'rt2012_bbio', 'rt2012_cep', 'rt2012_tic', 'rt2012_airtightness',
    're2020_energy_efficiency', 're2020_thermal_comfort',
    're2020_carbon_emissions', 're2020_ic_construction',
}


def get_seuils(building_type='maison', zone='H2'):
    bbio_base = RT2012_BBIO_BASE.get(building_type, 60)
    bbio_modif = RT2012_BBIO_ZONE_MODIF.get(zone, 0)
    return {
        'rt2012_bbio':              bbio_base + bbio_modif,
        'rt2012_cep':               RT2012_CEP_MAX.get(building_type, 50),
        'rt2012_tic':               RT2012_TIC_MAX.get(zone, 27),
        'rt2012_airtightness':      RT2012_AIRTIGHTNESS_MAX.get(building_type, 0.6),
        'rt2012_enr':               RT2012_ENR_MIN,
        're2020_energy_efficiency': RE2020_CEP_MAX.get(building_type, 100),
        're2020_thermal_comfort':   RE2020_DH_MAX.get(zone, 1250),
        're2020_carbon_emissions':  RE2020_IC_ENERGIE_MAX.get(building_type, 160),
        're2020_ic_construction':   RE2020_IC_CONSTRUCTION_MAX.get(building_type, 640),
    }


@register.filter
def is_conform_adapted(value, key):
    """Filtre simple avec seuils par défaut (maison, H2)."""
    if value is None:
        return False
    limit = get_seuils().get(key)
    if limit is None:
        return False
    try:
        val = float(value)
    except (ValueError, TypeError):
        return False
    if key in CRITERIA_GREATER_EQUAL:
        return val >= limit
    return val <= limit


@register.simple_tag
def get_seuil(key, building_type='maison', zone='H2'):
    """Retourne la valeur du seuil pour affichage."""
    return get_seuils(building_type, zone).get(key, '—')


@register.simple_tag
def check_conform(value, key, building_type='maison', zone='H2'):
    """Vérifie la conformité avec seuils dynamiques.
    Usage : {% check_conform doc.rt2012_bbio 'rt2012_bbio' doc.building_type doc.climate_zone %}"""
    if value is None:
        return False
    seuils = get_seuils(building_type, zone)
    limit = seuils.get(key)
    if limit is None:
        return False
    try:
        val = float(value)
    except (ValueError, TypeError):
        return False
    if key in CRITERIA_GREATER_EQUAL:
        return val >= limit
    return val <= limit
