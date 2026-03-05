from django import template

register = template.Library()

# ══════════════════════════════════════════════════════════
# SEUILS PAR PAYS ET NORME — valeurs standards modifiables
# ══════════════════════════════════════════════════════════

# ── FRANCE RT2012 ─────────────────────────────────────────
RT2012_BBIO_BASE        = {'maison': 60,  'collectif': 80,  'erp': 80}
RT2012_BBIO_ZONE_MODIF  = {'H1': +10, 'H2': 0, 'H3': -10}
RT2012_CEP_MAX          = {'maison': 50,  'collectif': 50,  'erp': 120}
RT2012_TIC_MAX          = {'H1': 26, 'H2': 27, 'H3': 28}
RT2012_AIRTIGHTNESS_MAX = {'maison': 0.6, 'collectif': 1.0, 'erp': 1.0}
RT2012_ENR_MIN          = 1.0

# ── FRANCE RE2020 ─────────────────────────────────────────
RE2020_CEP_MAX             = {'maison': 100, 'collectif': 100, 'erp': 150}
RE2020_DH_MAX              = {'H1': 1000, 'H2': 1250, 'H3': 1500}
RE2020_IC_ENERGIE_MAX      = {'maison': 160, 'collectif': 160, 'erp': 250}
RE2020_IC_CONSTRUCTION_MAX = {'maison': 640, 'collectif': 740, 'erp': 840}

# ── BELGIQUE PEB ──────────────────────────────────────────
PEB_ESPEC_MAX      = {'maison': 100, 'collectif': 100, 'erp': 150}
PEB_EW_MAX         = {'maison': 100, 'collectif': 100, 'erp': 100}
PEB_U_MUR_MAX      = 0.24
PEB_U_TOIT_MAX     = 0.20
PEB_U_PLANCHER_MAX = 0.30

# ── SUISSE MINERGIE ───────────────────────────────────────
MINERGIE_QH_MAX   = {'maison': 60, 'collectif': 55, 'erp': 55}
MINERGIE_QTOT_MAX = {'maison': 38, 'collectif': 38, 'erp': 45}
MINERGIE_N50_MAX  = 0.6

# ── SUISSE SIA380 ─────────────────────────────────────────
SIA380_QH_MAX = {'maison': 90, 'collectif': 80, 'erp': 80}

# ── CANADA CNEB2020 ───────────────────────────────────────
CNEB2020_EI_MAX           = {'maison': 150, 'collectif': 130, 'erp': 200}
CNEB2020_U_MUR_MAX        = 0.21
CNEB2020_U_TOIT_MAX       = 0.16
CNEB2020_U_FENETRE_MAX    = 1.6
CNEB2020_INFILTRATION_MAX = 0.25

# ── CANADA CNEB2015 ───────────────────────────────────────
CNEB2015_EI_MAX           = {'maison': 170, 'collectif': 150, 'erp': 220}
CNEB2015_U_MUR_MAX        = 0.24
CNEB2015_U_TOIT_MAX       = 0.18
CNEB2015_U_FENETRE_MAX    = 1.8
CNEB2015_INFILTRATION_MAX = 0.30

# ── LUXEMBOURG LENOZ ──────────────────────────────────────
LENOZ_EP_MAX      = {'maison': 90,  'collectif': 90,  'erp': 130}
LENOZ_EW_MAX      = {'maison': 100, 'collectif': 100, 'erp': 100}
LENOZ_U_MUR_MAX   = 0.22
LENOZ_U_TOIT_MAX  = 0.17

# ══════════════════════════════════════════════════════════
CRITERIA_GREATER_EQUAL = {'rt2012_enr'}
CRITERIA_LOWER_EQUAL = {
    'rt2012_bbio', 'rt2012_cep', 'rt2012_tic', 'rt2012_airtightness',
    're2020_energy_efficiency', 're2020_thermal_comfort',
    're2020_carbon_emissions', 're2020_ic_construction',
    'peb_espec', 'peb_ew', 'peb_u_mur', 'peb_u_toit', 'peb_u_plancher',
    'minergie_qh', 'minergie_qtot', 'minergie_n50', 'sia380_qh',
    'cneb_ei', 'cneb_u_mur', 'cneb_u_toit', 'cneb_u_fenetre', 'cneb_infiltration',
    'lenoz_ep', 'lenoz_ew', 'lenoz_u_mur', 'lenoz_u_toit',
}

NORMES_PAR_PAYS = {
    'FR': ['RT2012', 'RE2020'],
    'BE': ['PEB'],
    'CH': ['MINERGIE', 'SIA380'],
    'CA': ['CNEB2015', 'CNEB2020'],
    'LU': ['LENOZ'],
}

NORME_FIELDS = {
    'RT2012': [
        ('rt2012_bbio',         'Bbio',        ''),
        ('rt2012_cep',          'Cep',          'kWh ep/m².an'),
        ('rt2012_tic',          'Tic',          '°C'),
        ('rt2012_airtightness', 'Étanchéité',   'm³/h.m²'),
        ('rt2012_enr',          'ENR',          ''),
    ],
    'RE2020': [
        ('re2020_energy_efficiency', 'Cep,nr',           'kWh/m².an'),
        ('re2020_carbon_emissions',  'Ic énergie CO₂',   'kgCO2eq/m².an'),
        ('re2020_thermal_comfort',   'DH (confort été)',  'DH'),
    ],
    'PEB': [
        ('peb_espec',      'Espec',      'kWh/m².an'),
        ('peb_ew',         'Ew',         ''),
        ('peb_u_mur',      'U mur',      'W/m².K'),
        ('peb_u_toit',     'U toit',     'W/m².K'),
        ('peb_u_plancher', 'U plancher', 'W/m².K'),
    ],
    'MINERGIE': [
        ('minergie_qh',   'Qh',   'kWh/m².an'),
        ('minergie_qtot', 'Qtot', 'kWh/m².an'),
        ('minergie_n50',  'n50',  'h⁻¹'),
    ],
    'SIA380': [
        ('sia380_qh', 'Qh', 'kWh/m².an'),
    ],
    'CNEB2020': [
        ('cneb_ei',           'Intensité énergétique', 'kWh/m².an'),
        ('cneb_u_mur',        'U mur',                 'W/m².K'),
        ('cneb_u_toit',       'U toit',                'W/m².K'),
        ('cneb_u_fenetre',    'U fenêtre',             'W/m².K'),
        ('cneb_infiltration', 'Infiltration',          'L/s.m²'),
    ],
    'CNEB2015': [
        ('cneb_ei',           'Intensité énergétique', 'kWh/m².an'),
        ('cneb_u_mur',        'U mur',                 'W/m².K'),
        ('cneb_u_toit',       'U toit',                'W/m².K'),
        ('cneb_u_fenetre',    'U fenêtre',             'W/m².K'),
        ('cneb_infiltration', 'Infiltration',          'L/s.m²'),
    ],
    'LENOZ': [
        ('lenoz_ep',     'Énergie primaire', 'kWh/m².an'),
        ('lenoz_ew',     'Ew',               ''),
        ('lenoz_u_mur',  'U mur',            'W/m².K'),
        ('lenoz_u_toit', 'U toit',           'W/m².K'),
    ],
}


def get_seuils(building_type='maison', zone='H2', pays='FR', norme='RE2020'):
    bt = building_type or 'maison'
    z  = zone or 'H2'

    if pays == 'FR' and norme == 'RT2012':
        return {
            'rt2012_bbio':         RT2012_BBIO_BASE.get(bt, 60) + RT2012_BBIO_ZONE_MODIF.get(z, 0),
            'rt2012_cep':          RT2012_CEP_MAX.get(bt, 50),
            'rt2012_tic':          RT2012_TIC_MAX.get(z, 27),
            'rt2012_airtightness': RT2012_AIRTIGHTNESS_MAX.get(bt, 0.6),
            'rt2012_enr':          RT2012_ENR_MIN,
        }
    if pays == 'FR' and norme == 'RE2020':
        return {
            're2020_energy_efficiency': RE2020_CEP_MAX.get(bt, 100),
            're2020_thermal_comfort':   RE2020_DH_MAX.get(z, 1250),
            're2020_carbon_emissions':  RE2020_IC_ENERGIE_MAX.get(bt, 160),
            're2020_ic_construction':   RE2020_IC_CONSTRUCTION_MAX.get(bt, 640),
        }
    if pays == 'BE' and norme == 'PEB':
        return {
            'peb_espec':      PEB_ESPEC_MAX.get(bt, 100),
            'peb_ew':         PEB_EW_MAX.get(bt, 100),
            'peb_u_mur':      PEB_U_MUR_MAX,
            'peb_u_toit':     PEB_U_TOIT_MAX,
            'peb_u_plancher': PEB_U_PLANCHER_MAX,
        }
    if pays == 'CH' and norme == 'MINERGIE':
        return {
            'minergie_qh':   MINERGIE_QH_MAX.get(bt, 60),
            'minergie_qtot': MINERGIE_QTOT_MAX.get(bt, 38),
            'minergie_n50':  MINERGIE_N50_MAX,
        }
    if pays == 'CH' and norme == 'SIA380':
        return {'sia380_qh': SIA380_QH_MAX.get(bt, 90)}
    if pays == 'CA' and norme == 'CNEB2020':
        return {
            'cneb_ei':           CNEB2020_EI_MAX.get(bt, 150),
            'cneb_u_mur':        CNEB2020_U_MUR_MAX,
            'cneb_u_toit':       CNEB2020_U_TOIT_MAX,
            'cneb_u_fenetre':    CNEB2020_U_FENETRE_MAX,
            'cneb_infiltration': CNEB2020_INFILTRATION_MAX,
        }
    if pays == 'CA' and norme == 'CNEB2015':
        return {
            'cneb_ei':           CNEB2015_EI_MAX.get(bt, 170),
            'cneb_u_mur':        CNEB2015_U_MUR_MAX,
            'cneb_u_toit':       CNEB2015_U_TOIT_MAX,
            'cneb_u_fenetre':    CNEB2015_U_FENETRE_MAX,
            'cneb_infiltration': CNEB2015_INFILTRATION_MAX,
        }
    if pays == 'LU' and norme == 'LENOZ':
        return {
            'lenoz_ep':    LENOZ_EP_MAX.get(bt, 90),
            'lenoz_ew':    LENOZ_EW_MAX.get(bt, 100),
            'lenoz_u_mur': LENOZ_U_MUR_MAX,
            'lenoz_u_toit':LENOZ_U_TOIT_MAX,
        }
    # fallback
    return {
        're2020_energy_efficiency': RE2020_CEP_MAX.get(bt, 100),
        're2020_thermal_comfort':   RE2020_DH_MAX.get(z, 1250),
        're2020_carbon_emissions':  RE2020_IC_ENERGIE_MAX.get(bt, 160),
        're2020_ic_construction':   RE2020_IC_CONSTRUCTION_MAX.get(bt, 640),
    }


@register.filter
def attr(obj, field_name):
    return getattr(obj, field_name, None)


@register.simple_tag
def get_seuil(key, building_type='maison', zone='H2', pays='FR', norme='RE2020'):
    return get_seuils(building_type, zone, pays, norme).get(key, '—')


@register.simple_tag
def check_conform(value, key, building_type='maison', zone='H2', pays='FR', norme='RE2020'):
    if value is None:
        return False
    seuils = get_seuils(building_type, zone, pays, norme)
    limit  = seuils.get(key)
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
def get_norme_fields(norme):
    return NORME_FIELDS.get(norme, [])


@register.simple_tag
def get_normes_pays(pays):
    return NORMES_PAR_PAYS.get(pays, [])
