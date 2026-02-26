from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, PageBreak
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4


def generate_report(document):

    file_path = f"/tmp/report_{document.id}.pdf"
    pdf = SimpleDocTemplate(file_path, pagesize=A4)
    elements = []

    styles = getSampleStyleSheet()

    big_score = ParagraphStyle(
        name='BigScore',
        parent=styles['Heading1'],
        fontSize=36,
        alignment=1
    )

    # =========================
    # PAGE DE GARDE
    # =========================

    elements.append(Spacer(1, 120))
    elements.append(Paragraph("SaaS", styles['Title']))
    elements.append(Spacer(1, 10))
    elements.append(Paragraph("Regulatory Decision Intelligence", styles['Heading3']))
    elements.append(Spacer(1, 40))
    elements.append(Paragraph("RAPPORT D’ANALYSE RÉGLEMENTAIRE", styles['Heading1']))
    elements.append(Spacer(1, 10))
    elements.append(Paragraph("Comparatif RE2020 / RT2012", styles['Heading2']))
    elements.append(Spacer(1, 40))
    elements.append(Paragraph(f"Document analysé : {document.name}", styles['Normal']))
    elements.append(Paragraph(f"Date d’analyse : {document.upload_date.strftime('%d %b %Y')}", styles['Normal']))
    elements.append(Spacer(1, 80))
    elements.append(Paragraph("Document confidentiel – Diffusion restreinte", styles['Normal']))
    elements.append(Paragraph("Powered by SaaS", styles['Normal']))
    elements.append(PageBreak())

    # =========================
    # CALCUL SCORES
    # =========================

    re2020_values = [
        document.re2020_energy_efficiency or 0,
        document.re2020_thermal_comfort or 0,
        document.re2020_carbon_emissions or 0,
        document.re2020_water_management or 0,
        document.re2020_indoor_air_quality or 0,
    ]

    rt2012_values = [
        document.rt2012_bbio or 0,
        document.rt2012_cep or 0,
        document.rt2012_tic or 0,
        document.rt2012_airtightness or 0,
        document.rt2012_enr or 0,
    ]

    re2020_score = round(sum(re2020_values) / len(re2020_values), 1)
    rt2012_score = round(sum(rt2012_values) / len(rt2012_values), 1)

    def global_status(score):
        if score >= 75:
            return "Conforme"
        elif score >= 50:
            return "Partiellement conforme"
        return "Non conforme"

    re2020_status = global_status(re2020_score)
    rt2012_status = global_status(rt2012_score)

    def executive_interpretation(score):
        if score >= 75:
            return "Le projet présente un niveau de conformité élevé et un risque réglementaire faible pour un investisseur."
        elif score >= 50:
            return "Le projet nécessite des ajustements techniques avant sécurisation complète du risque réglementaire."
        else:
            return "Le projet présente un risque réglementaire significatif pouvant impacter la rentabilité et les délais."

    re2020_comment = executive_interpretation(re2020_score)
    rt2012_comment = executive_interpretation(rt2012_score)
    
    # =========================
    # EXECUTIVE SUMMARY
    # =========================

    elements.append(Paragraph("Executive Summary", styles['Heading1']))
    elements.append(Spacer(1, 20))

    elements.append(Paragraph("RE2020", styles['Heading2']))
    elements.append(Spacer(1, 10))
    elements.append(Paragraph(f"{re2020_score} %", big_score))
    elements.append(Spacer(1, 10))
    elements.append(Paragraph(f"Statut : {re2020_status}", styles['Normal']))
    elements.append(Spacer(1, 20))
    elements.append(Paragraph(re2020_comment, styles['Normal']))

    elements.append(Paragraph("RT2012", styles['Heading2']))
    elements.append(Spacer(1, 10))
    elements.append(Paragraph(f"{rt2012_score} %", big_score))
    elements.append(Spacer(1, 10))
    elements.append(Paragraph(f"Statut : {rt2012_status}", styles['Normal']))
    elements.append(Spacer(1, 10))
    elements.append(Paragraph(rt2012_comment, styles['Normal']))

    elements.append(Spacer(1, 30))
    elements.append(Paragraph("Comparative Regulatory Overview", styles['Heading2']))
    elements.append(Spacer(1, 15))

    comparative_data = [
        ["Réglementation", "Score (%)", "Statut"],
        ["RE2020", re2020_score, re2020_status],
        ["RT2012", rt2012_score, rt2012_status],
    ]

    comparative_table = Table(comparative_data, colWidths=[150, 100, 150])
    comparative_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.black),
    ]))

    elements.append(comparative_table)

    elements.append(Spacer(1, 30))
    elements.append(Paragraph("Gap Analysis", styles['Heading2']))
    elements.append(Spacer(1, 15))

    gap_data = [
        ["Critère", "RE2020", "RT2012", "Écart"],
    ]

    criteria = [
        ("Efficacité énergétique", document.re2020_energy_efficiency or 0, document.rt2012_energy_efficiency or 0),
        ("Confort thermique", document.re2020_thermal_comfort or 0, document.rt2012_thermal_comfort or 0),
        ("Émissions carbone", document.re2020_carbon_emissions or 0, document.rt2012_carbon_emissions or 0),
        ("Gestion de l’eau", document.re2020_water_management or 0, document.rt2012_water_management or 0),
        ("Qualité air intérieur", document.re2020_indoor_air_quality or 0, document.rt2012_indoor_air_quality or 0),
    ]

    for label, re_val, rt_val in criteria:
        gap = re_val - rt_val
        gap_data.append([label, re_val, rt_val, gap])

    gap_table = Table(gap_data, colWidths=[150, 80, 80, 80])
    gap_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.black),
    ]))

    elements.append(gap_table)

    elements.append(Spacer(1, 30))
    elements.append(Paragraph("Global Risk Assessment", styles['Heading2']))
    elements.append(Spacer(1, 15))

    def risk_profile(score):
        if score >= 75:
            return ("Faible", 
                    "Impact financier limité", 
                    "Risque de retard faible", 
                    "Projet réglementairement sécurisé")
        elif score >= 50:
            return ("Modéré", 
                    "Ajustements budgétaires à prévoir", 
                    "Risque de retard modéré", 
                    "Optimisation réglementaire recommandée")
        else:
            return ("Élevé", 
                    "Risque financier significatif", 
                    "Risque de blocage administratif", 
                    "Révision stratégique urgente nécessaire")

    re_risk_level, re_financial, re_delay, re_operational = risk_profile(re2020_score)
    rt_risk_level, rt_financial, rt_delay, rt_operational = risk_profile(rt2012_score)

    risk_data = [
        ["Réglementation", "Niveau", "Financier", "Délai", "Opérationnel"],
        ["RE2020", re_risk_level, re_financial, re_delay, re_operational],
        ["RT2012", rt_risk_level, rt_financial, rt_delay, rt_operational],
    ]

    risk_table = Table(risk_data, colWidths=[100, 70, 120, 120, 120])
    risk_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.black),
    ]))

    elements.append(risk_table)

    elements.append(Spacer(1, 30))
    elements.append(Paragraph("Strategic Recommendations", styles['Heading2']))
    elements.append(Spacer(1, 15))

    def recommendations(score):
        if score >= 75:
            return [
                "Maintenir la stratégie actuelle.",
                "Optimiser marginalement les performances techniques.",
                "Sécuriser les financements sur la base de la conformité élevée."
            ]
        elif score >= 50:
            return [
                "Prioriser les critères non conformes.",
                "Allouer un budget d’optimisation technique.",
                "Revoir le calendrier de dépôt si nécessaire."
            ]
        else:
            return [
                "Revoir la stratégie technique globale.",
                "Réaliser une étude approfondie des postes critiques.",
                "Reporter toute décision d’investissement majeur."
            ]

    re_reco = recommendations(re2020_score)
    rt_reco = recommendations(rt2012_score)

    elements.append(Paragraph("RE2020", styles['Heading3']))
    for r in re_reco:
        elements.append(Paragraph(f"- {r}", styles['Normal']))

    elements.append(Spacer(1, 15))

    elements.append(Paragraph("RT2012", styles['Heading3']))
    for r in rt_reco:
        elements.append(Paragraph(f"- {r}", styles['Normal']))

    elements.append(Spacer(1, 30))
    elements.append(Paragraph("Executive Investment Verdict", styles['Heading2']))
    elements.append(Spacer(1, 15))

    global_average = round((re2020_score + rt2012_score) / 2, 1)

    if global_average >= 75:
        verdict = "Investissement recommandé : Le projet présente un profil réglementaire sécurisé et compatible avec une stratégie d’investissement."
    elif global_average >= 50:
        verdict = "Investissement sous conditions : Des ajustements techniques sont nécessaires avant sécurisation complète du risque."
    else:
        verdict = "Investissement déconseillé en l’état : Le risque réglementaire et financier est significatif."

    elements.append(Paragraph(verdict, styles['Normal']))
    elements.append(PageBreak())

    # =========================
    # EXIGENCES
    # =========================
    re2020_req = {
        "energy": 80,
        "thermal": 85,
        "carbon": 75,
        "water": 70,
        "air": 75,
    }

    rt2012_req = {
        "energy": 50,
        "thermal": 22,
        "carbon": 35,
        "water": 120,
        "air": 800,
    }

    # =========================
    # TABLEAU RE2020
    # =========================
    elements.append(Paragraph("Analyse RE2020", styles['Heading2']))
    elements.append(Spacer(1, 15))

    data_re2020 = [
        ["Critère", "Valeur", "Exigence", "Statut"],
    ]

    rows = [
        ("Efficacité énergétique", document.re2020_energy_efficiency, re2020_req["energy"]),
        ("Confort thermique", document.re2020_thermal_comfort, re2020_req["thermal"]),
        ("Émissions carbone", document.re2020_carbon_emissions, re2020_req["carbon"]),
        ("Gestion de l’eau", document.re2020_water_management, re2020_req["water"]),
        ("Qualité air intérieur", document.re2020_indoor_air_quality, re2020_req["air"]),
    ]

    for label, value, requirement in rows:
        value = value if value is not None else 0
        status = "Conforme" if value >= requirement else "Non conforme"
        data_re2020.append([label, value, requirement, status])

    table_re2020 = Table(data_re2020, colWidths=[170, 80, 80, 100])
    table_re2020.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.black),
    ]))

    elements.append(table_re2020)
    elements.append(Spacer(1, 30))

    # =========================
    # TABLEAU RT2012
    # =========================
    elements.append(Paragraph("Analyse RT2012", styles['Heading2']))
    elements.append(Spacer(1, 15))

    data_rt2012 = [
        ["Critère", "Valeur", "Exigence", "Statut"],
    ]

    rows_rt = [
        ("Efficacité énergétique", document.rt2012_energy_efficiency, rt2012_req["energy"]),
        ("Confort thermique", document.rt2012_thermal_comfort, rt2012_req["thermal"]),
        ("Émissions carbone", document.rt2012_carbon_emissions, rt2012_req["carbon"]),
        ("Gestion de l’eau", document.rt2012_water_management, rt2012_req["water"]),
        ("Qualité air intérieur", document.rt2012_indoor_air_quality, rt2012_req["air"]),
    ]

    for label, value, requirement in rows_rt:
        value = value if value is not None else 0
        status = "Conforme" if value >= requirement else "Non conforme"
        data_rt2012.append([label, value, requirement, status])

    table_rt2012 = Table(data_rt2012, colWidths=[170, 80, 80, 100])
    table_rt2012.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.black),
    ]))

    elements.append(table_rt2012)

    pdf.build(elements)

    return file_path
