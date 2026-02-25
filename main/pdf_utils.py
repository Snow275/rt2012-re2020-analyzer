from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, PageBreak
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4


def generate_report(document):

    file_path = f"/tmp/report_{document.id}.pdf"
    pdf = SimpleDocTemplate(file_path, pagesize=A4)
    elements = []

    styles = getSampleStyleSheet()

    # =========================
    # PAGE DE GARDE PREMIUM
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
    # CALCUL SCORES GLOBAUX
    # =========================

    re2020_values = [
        document.re2020_energy_efficiency or 0,
        document.re2020_thermal_comfort or 0,
        document.re2020_carbon_emissions or 0,
        document.re2020_water_management or 0,
        document.re2020_indoor_air_quality or 0,
    ]

    rt2012_values = [
        document.rt2012_energy_efficiency or 0,
        document.rt2012_thermal_comfort or 0,
        document.rt2012_carbon_emissions or 0,
        document.rt2012_water_management or 0,
        document.rt2012_indoor_air_quality or 0,
    ]

    re2020_score = round(sum(re2020_values) / len(re2020_values), 1)
    rt2012_score = round(sum(rt2012_values) / len(rt2012_values), 1)

    def global_status(score):
        if score >= 75:
            return "Conforme"
        elif score >= 50:
            return "Partiellement conforme"
        else:
            return "Non conforme"

    re2020_status = global_status(re2020_score)
    rt2012_status = global_status(rt2012_score)

    def risk_level(status):
        if status == "Conforme":
            return "Faible"
        elif status == "Partiellement conforme":
            return "Modéré"
        else:
            return "Élevé"

    re2020_risk = risk_level(re2020_status)
    rt2012_risk = risk_level(rt2012_status)

    # =========================
    # EXECUTIVE SUMMARY
    # =========================

    elements.append(Paragraph("Executive Summary", styles['Heading1']))
    elements.append(Spacer(1, 20))

    elements.append(Paragraph(f"Score global RE2020 : {re2020_score} %", styles['Normal']))
    elements.append(Paragraph(f"Statut RE2020 : {re2020_status}", styles['Normal']))
    elements.append(Paragraph(f"Niveau de risque RE2020 : {re2020_risk}", styles['Normal']))

    elements.append(Spacer(1, 20))

    elements.append(Paragraph(f"Score global RT2012 : {rt2012_score} %", styles['Normal']))
    elements.append(Paragraph(f"Statut RT2012 : {rt2012_status}", styles['Normal']))
    elements.append(Paragraph(f"Niveau de risque RT2012 : {rt2012_risk}", styles['Normal']))

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
