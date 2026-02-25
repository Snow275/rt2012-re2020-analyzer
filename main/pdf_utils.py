from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.platypus import PageBreak
import os


def generate_report(document):

    file_path = f"/tmp/report_{document.id}.pdf"
    pdf = SimpleDocTemplate(file_path, pagesize=A4)
    elements = []

    styles = getSampleStyleSheet()

    # ===== PAGE DE GARDE =====
    elements.append(Paragraph("Rapport d’Analyse Réglementaire", styles['Title']))
    elements.append(Spacer(1, 30))
    elements.append(Paragraph(f"Document : {document.name}", styles['Normal']))
    elements.append(Paragraph(f"Date : {document.upload_date.strftime('%d %b %Y')}", styles['Normal']))
    elements.append(Spacer(1, 50))
    elements.append(Paragraph("Outil de comparaison RE2020 / RT2012", styles['Normal']))
    elements.append(PageBreak())

    # ===== SECTION RE2020 =====
    elements.append(Paragraph("Analyse RE2020", styles['Heading2']))
    elements.append(Spacer(1, 15))

    data = [
        ["Critère", "Valeur"],
        ["Efficacité énergétique", document.re2020_energy_efficiency],
        ["Confort thermique", document.re2020_thermal_comfort],
        ["Émissions carbone", document.re2020_carbon_emissions],
        ["Gestion de l’eau", document.re2020_water_management],
        ["Qualité air intérieur", document.re2020_indoor_air_quality],
    ]

    table = Table(data, colWidths=[250, 150])
    table.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), colors.grey),
        ('TEXTCOLOR',(0,0),(-1,0),colors.white),
        ('GRID', (0,0), (-1,-1), 0.5, colors.black),
    ]))

    elements.append(table)
    elements.append(Spacer(1, 20))

    pdf.build(elements)

    return file_path
