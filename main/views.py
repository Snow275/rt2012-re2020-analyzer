from django.shortcuts import render, redirect, get_object_or_404
from django.http import HttpResponse, JsonResponse
from django.contrib import messages
from django.template.loader import render_to_string
from django.core.mail import send_mail
from django.conf import settings as django_settings
from django.views.decorators.csrf import csrf_exempt
from rest_framework.decorators import api_view
from rest_framework.response import Response
from rest_framework import status

from .models import Document, Analysis
from .forms import DocumentForm, ContactForm
from .serializers import DocumentSerializer, AnalysisSerializer

import PyPDF2
import re


# ──────────────────────────────────────────────
# UTILITAIRES
# ──────────────────────────────────────────────

def fetch_re2020_requirements():
    return {
        'energy_efficiency': 80.0,
        'thermal_comfort': 85.0,
        'carbon_emissions': 75.0,
        'water_management': 70.0,
        'indoor_air_quality': 75.0,
    }


def fetch_rt2012_requirements():
    return {
        'bbio': 50.0,
        'cep': 50.0,
        'tic': 27.0,
        'airtightness': 0.6,
        'enr': 1.0,
    }


def extract_text_from_pdf(upload_path):
    text = ""
    try:
        with open(upload_path, "rb") as file:
            reader = PyPDF2.PdfReader(file)
            for page in reader.pages:
                extracted = page.extract_text()
                if extracted:
                    text += extracted
    except Exception as e:
        print(f"Erreur lecture PDF: {e}")
    return text


def parse_pdf_text(text):
    data = {}
    re2020_section = ""
    rt2012_section = ""

    if "RE2020" in text and "RT2012" in text:
        re2020_section = text.split("RE2020")[1].split("RT2012")[0]
        rt2012_section = text.split("RT2012")[1]
    elif "RE2020" in text:
        re2020_section = text.split("RE2020")[1]
    elif "RT2012" in text:
        rt2012_section = text.split("RT2012")[1]

    # RE2020
    for pattern, key in [
        (r'Cep\s*=\s*([\d.]+)', 'energy_efficiency'),
        (r'DH\s*=\s*([\d.]+)', 'thermal_comfort'),
        (r'Ic.?energie\s*=\s*([\d.]+)', 'carbon_emissions'),
        (r'Eau\s*=\s*([\d.]+)', 'water_management'),
        (r'Qai\s*=\s*([\d.]+)', 'indoor_air_quality'),
    ]:
        m = re.search(pattern, re2020_section, re.IGNORECASE)
        if m:
            data[key] = float(m.group(1))

    # RT2012
    for pattern, key in [
        (r'Bbio\s*=\s*([\d.]+)', 'bbio'),
        (r'Cep\s*=\s*([\d.]+)', 'cep_rt'),
        (r'Tic\s*=\s*([\d.]+)', 'tic'),
        (r'Etancheite\s*=\s*([\d.]+)', 'airtightness'),
        (r'Enr\s*=\s*([\d.]+)', 'enr'),
    ]:
        m = re.search(pattern, rt2012_section, re.IGNORECASE)
        if m:
            data[key] = float(m.group(1))

    return data


def analyze_document(document, data):
    document.re2020_energy_efficiency = data.get('energy_efficiency')
    document.re2020_thermal_comfort = data.get('thermal_comfort')
    document.re2020_carbon_emissions = data.get('carbon_emissions')
    document.re2020_water_management = data.get('water_management')
    document.re2020_indoor_air_quality = data.get('indoor_air_quality')
    document.rt2012_bbio = data.get('bbio')
    document.rt2012_cep = data.get('cep_rt')
    document.rt2012_tic = data.get('tic')
    document.rt2012_airtightness = data.get('airtightness')
    document.rt2012_enr = data.get('enr')
    document.status = 'en_cours'
    document.save()


# ──────────────────────────────────────────────
# VUES PUBLIQUES
# ──────────────────────────────────────────────

def landing(request):
    """Page d'accueil publique — vitrine commerciale."""
    return render(request, 'main/landing.html')


def home(request):
    documents = Document.objects.filter(is_active=True)
    total_projects = documents.count()

    compliant_count = sum(
        1 for doc in documents
        if doc.rt2012_is_conform is True or doc.re2020_is_conform is True
    )
    compliance_rate = round((compliant_count / total_projects * 100), 1) if total_projects else 0

    carbon_values = [
        doc.re2020_carbon_emissions for doc in documents
        if doc.re2020_carbon_emissions is not None
    ]
    avg_carbon = round(sum(carbon_values) / len(carbon_values), 1) if carbon_values else 0

    context = {
        'documents': documents,
        'total_projects': total_projects,
        'compliance_rate': compliance_rate,
        'avg_carbon': avg_carbon,
    }
    return render(request, 'main/home.html', context)


def import_document(request):
    if request.method == "POST":
        form = DocumentForm(request.POST, request.FILES)
        if form.is_valid():
            document = form.save()
            upload_path = document.upload.path
            text = extract_text_from_pdf(upload_path)
            data = parse_pdf_text(text)
            analyze_document(document, data)
            messages.success(request, "Dossier reçu. Votre lien de suivi a été créé.")
            return redirect('tracking', token=document.tracking_token)
        else:
            messages.error(request, "Veuillez corriger les erreurs ci-dessous.")
    else:
        form = DocumentForm()
    return render(request, "main/import.html", {
        "form": form,
        "doc_items": [
            "Notice thermique / étude thermique",
            "Attestation RT2012 ou RE2020",
            "Plans architecturaux (PDF)",
            "DPE si disponible",
            "CCTP / descriptif technique",
        ],
        "steps": [
            "Accusé de réception sous 24h",
            "Confirmation de complétude du dossier",
            "Analyse documentaire complète",
            "Livraison du rapport PDF + lien de suivi",
        ],
    })


def get_tracking_steps(document):
    steps_def = [
        ("Dossier reçu et validé", 'recu'),
        ("Analyse de l'enveloppe thermique", 'en_cours'),
        ("Vérification systèmes & attestations", 'en_cours'),
        ("Rédaction du rapport", 'en_cours'),
        ("Livraison du rapport PDF", 'termine'),
    ]
    order = ['recu', 'en_cours', 'termine']
    current_idx = order.index(document.status)
    result = []
    for label, needed_status in steps_def:
        needed_idx = order.index(needed_status)
        if current_idx > needed_idx:
            state = 'done'
        elif current_idx == needed_idx:
            state = 'active'
        else:
            state = 'pending'
        result.append((label, state))
    return result


def tracking(request, token):
    document = get_object_or_404(Document, tracking_token=token)
    step_list = get_tracking_steps(document)
    progress_pct = {'recu': 15, 'en_cours': 60, 'termine': 100}.get(document.status, 15)
    return render(request, 'main/tracking.html', {
        'document': document,
        'step_list': step_list,
        'progress_pct': progress_pct,
    })


def results(request):
    documents = Document.objects.filter(is_active=True)
    re2020_req = fetch_re2020_requirements()
    rt2012_req = fetch_rt2012_requirements()
    context = {
        'documents': documents,
        're2020_requirements': re2020_req,
        'rt2012_requirements': rt2012_req,
    }
    return render(request, 'main/results.html', context)


def history(request):
    documents = Document.objects.all().order_by('-upload_date')
    return render(request, 'main/history.html', {'documents': documents})


def contact(request):
    if request.method == 'POST':
        form = ContactForm(request.POST)
        if form.is_valid():
            # Envoi email (si EMAIL_BACKEND configuré)
            try:
                send_mail(
                    subject=f"[ConformExpert] Nouveau contact : {form.cleaned_data['name']}",
                    message=(
                        f"Nom : {form.cleaned_data['name']}\n"
                        f"Email : {form.cleaned_data['email']}\n"
                        f"Téléphone : {form.cleaned_data.get('phone', 'N/A')}\n"
                        f"Profil : {form.cleaned_data.get('profile', 'N/A')}\n\n"
                        f"Message :\n{form.cleaned_data['message']}"
                    ),
                    from_email=django_settings.DEFAULT_FROM_EMAIL,
                    recipient_list=[django_settings.CONTACT_EMAIL],
                    fail_silently=True,
                )
            except Exception:
                pass
            messages.success(request, 'Message envoyé. Nous vous répondons sous 48h.')
            return redirect('contact')
    else:
        form = ContactForm()
    return render(request, 'main/contact.html', {'form': form})


def faq(request):
    faq_items = [
        {"question": "Quelle est la différence entre RT2012 et RE2020 ?",
         "answer": "La RT2012 encadre la consommation énergétique via Bbio, Cep et Tic. La RE2020, en vigueur depuis janvier 2022, va plus loin : elle intègre le bilan carbone sur le cycle de vie du bâtiment et renforce les exigences de confort d'été."},
        {"question": "Quels documents dois-je fournir ?",
         "answer": "Pour une analyse complète : notice ou étude thermique réglementaire, attestations RT2012 ou RE2020, plans architecturaux PDF, DPE si disponible, CCTP. Plus le dossier est complet, plus l'analyse est précise."},
        {"question": "Quel est le délai de livraison ?",
         "answer": "Nous garantissons la livraison du rapport sous 15 jours ouvrés après réception d'un dossier complet. Ce délai est affiché sur votre lien de suivi dès la réception."},
        {"question": "Comment fonctionne le lien de suivi ?",
         "answer": "Après dépôt, vous recevez un lien unique. Il vous permet de suivre l'avancement en temps réel et de télécharger le rapport dès sa livraison. Aucune création de compte n'est nécessaire."},
        {"question": "Mon analyse est-elle vraiment indépendante ?",
         "answer": "Oui. Notre analyse est réalisée sans lien avec le bureau d'études ou le maître d'ouvrage. Cette indépendance garantit une lecture objective et non biaisée de vos documents."},
        {"question": "Proposez-vous des visites sur site ?",
         "answer": "Oui, sur demande et en complément de l'analyse documentaire. La visite est disponible en option pour les dossiers collectifs ou tertiaires."},
    ]
    return render(request, 'main/faq.html', {'faq_items': faq_items})


def settings_view(request):
    re2020_req = fetch_re2020_requirements()
    rt2012_req = fetch_rt2012_requirements()
    return render(request, 'main/settings.html', {
        're2020_req': re2020_req,
        'rt2012_req': rt2012_req,
    })


def update_re2020(request):
    if request.method == 'POST':
        messages.success(request, 'Paramètres RE2020 mis à jour.')
    else:
        messages.error(request, 'Méthode invalide.')
    return redirect('settings')


def delete_document(request, doc_id):
    if request.method == 'POST':
        document = get_object_or_404(Document, id=doc_id)
        document.delete()
        messages.success(request, 'Dossier supprimé.')
    return redirect('history')


def download_report(request, document_id):
    document = get_object_or_404(Document, id=document_id)

    from io import BytesIO
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.lib.units import cm
    from reportlab.lib import colors
    from reportlab.platypus import (
        SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, HRFlowable
    )
    from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT
    from main.templatetags.conformity_tags import get_seuils, CRITERIA_GREATER_EQUAL
    from datetime import date

    # ── Couleurs ──────────────────────────────────────
    NAVY   = colors.HexColor('#0C1929')
    GOLD   = colors.HexColor('#C8A84B')
    GREEN  = colors.HexColor('#1A9E2E')
    RED    = colors.HexColor('#C62828')
    LGRAY  = colors.HexColor('#F5F5F8')
    MGRAY  = colors.HexColor('#E0E0E8')
    WHITE  = colors.white
    MUTED  = colors.HexColor('#666677')
    TEXT   = colors.HexColor('#1A1A2E')

    buffer = BytesIO()
    doc = SimpleDocTemplate(
        buffer, pagesize=A4,
        leftMargin=2*cm, rightMargin=2*cm,
        topMargin=2.5*cm, bottomMargin=2*cm,
        title=f"Rapport ConformExpert – {document.name}"
    )

    styles = getSampleStyleSheet()
    body_style   = ParagraphStyle('body',   fontName='Helvetica', fontSize=9,  textColor=TEXT,  spaceAfter=4)
    bold_style   = ParagraphStyle('bold',   fontName='Helvetica-Bold', fontSize=9, textColor=TEXT)
    muted_style  = ParagraphStyle('muted',  fontName='Helvetica', fontSize=8,  textColor=MUTED, spaceAfter=4)
    center_style = ParagraphStyle('center', fontName='Helvetica', fontSize=9,  textColor=TEXT,  alignment=TA_CENTER)
    ok_style     = ParagraphStyle('ok',     fontName='Helvetica-Bold', fontSize=9, textColor=GREEN, alignment=TA_CENTER)
    nok_style    = ParagraphStyle('nok',    fontName='Helvetica-Bold', fontSize=9, textColor=RED,   alignment=TA_CENTER)

    W = 17 * cm  # largeur utile
    seuils = get_seuils(document.building_type, document.climate_zone)

    def verdict_para(value):
        if value is None:
            return Paragraph("—", center_style)
        if value:
            return Paragraph("✓  Conforme", ok_style)
        return Paragraph("✗  Non conforme", nok_style)

    def criteria_row(label, value, key, unit="", bg=WHITE):
        if value is None:
            return None
        limit = seuils.get(key, "—")
        sign = "≥" if key in CRITERIA_GREATER_EQUAL else "≤"
        conform = (value >= limit if key in CRITERIA_GREATER_EQUAL else value <= limit) if isinstance(limit, (int, float)) else False
        return [
            Paragraph(label, body_style),
            Paragraph(f"<b>{value}</b>", ParagraphStyle('v', fontName='Helvetica-Bold', fontSize=9, textColor=TEXT, alignment=TA_CENTER)),
            Paragraph(f"{sign} {limit}", ParagraphStyle('s', fontName='Helvetica', fontSize=9, textColor=MUTED, alignment=TA_CENTER)),
            Paragraph(unit, ParagraphStyle('u', fontName='Helvetica', fontSize=8, textColor=MUTED, alignment=TA_CENTER)),
            Paragraph("✓ Conforme" if conform else "✗ Non conforme",
                      ParagraphStyle('r', fontName='Helvetica-Bold', fontSize=9,
                                     textColor=GREEN if conform else RED, alignment=TA_CENTER)),
        ]

    story = []

    # ── BANDEAU TITRE ─────────────────────────────────
    title_data = [[
        Paragraph(
            f'<font color="#C8A84B" size="8">ANALYSE INDÉPENDANTE · RT2012 / RE2020</font><br/>'
            f'<font color="white" size="18"><b>{document.name}</b></font><br/>'
            f'<font color="#AAAACC" size="9">{document.get_building_type_display()} · Zone {document.climate_zone} · Déposé le {document.upload_date.strftime("%d/%m/%Y")}</font>',
            ParagraphStyle('title', fontName='Helvetica', fontSize=9, textColor=WHITE, leading=20)
        )
    ]]
    title_table = Table(title_data, colWidths=[W])
    title_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, -1), NAVY),
        ('TOPPADDING', (0, 0), (-1, -1), 14),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 14),
        ('LEFTPADDING', (0, 0), (-1, -1), 16),
        ('RIGHTPADDING', (0, 0), (-1, -1), 16),
        ('ROUNDEDCORNERS', [6, 6, 6, 6]),
    ]))
    story.append(title_table)
    story.append(Spacer(1, 0.4*cm))

    # ── VERDICTS ─────────────────────────────────────
    verdict_data = [[
        [Paragraph("RT2012", ParagraphStyle('vl', fontName='Helvetica', fontSize=8, textColor=MUTED, alignment=TA_CENTER)),
         verdict_para(document.rt2012_is_conform)],
        [Paragraph("RE2020", ParagraphStyle('vl', fontName='Helvetica', fontSize=8, textColor=MUTED, alignment=TA_CENTER)),
         verdict_para(document.re2020_is_conform)],
    ]]

    rt_bg = colors.HexColor('#E8F8EE') if document.rt2012_is_conform else colors.HexColor('#FEF0F0') if document.rt2012_is_conform is not None else LGRAY
    re_bg = colors.HexColor('#E8F8EE') if document.re2020_is_conform else colors.HexColor('#FEF0F0') if document.re2020_is_conform is not None else LGRAY

    half = W / 2 - 0.2*cm
    v_rt = Table([[Paragraph("RT2012", muted_style)], [verdict_para(document.rt2012_is_conform)]], colWidths=[half])
    v_rt.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, -1), rt_bg),
        ('BOX', (0, 0), (-1, -1), 1, MGRAY),
        ('TOPPADDING', (0, 0), (-1, -1), 10),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 10),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
    ]))
    v_re = Table([[Paragraph("RE2020", muted_style)], [verdict_para(document.re2020_is_conform)]], colWidths=[half])
    v_re.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, -1), re_bg),
        ('BOX', (0, 0), (-1, -1), 1, MGRAY),
        ('TOPPADDING', (0, 0), (-1, -1), 10),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 10),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
    ]))
    verdict_row = Table([[v_rt, v_re]], colWidths=[half + 0.2*cm, half])
    verdict_row.setStyle(TableStyle([('LEFTPADDING', (0, 0), (-1, -1), 0), ('RIGHTPADDING', (0, 0), (-1, -1), 0)]))
    story.append(verdict_row)
    story.append(Spacer(1, 0.5*cm))

    # ── INFOS DOSSIER ─────────────────────────────────
    story.append(HRFlowable(width=W, thickness=1, color=GOLD, spaceAfter=6))
    story.append(Paragraph("INFORMATIONS DU DOSSIER", ParagraphStyle('sh', fontName='Helvetica-Bold', fontSize=8, textColor=GOLD, spaceBefore=4, spaceAfter=6, characterSpacing=1)))
    info_rows = [
        ["Référence", f"DOC-{document.id:04d}"],
        ["Projet", document.name],
        ["Client", f"{document.client_name}" if document.client_name else "—"],
        ["Type de bâtiment", document.get_building_type_display()],
        ["Zone climatique", f"{document.climate_zone}"],
        ["Date de dépôt", document.upload_date.strftime("%d/%m/%Y")],
        ["Date du rapport", date.today().strftime("%d/%m/%Y")],
    ]
    info_table = Table(
        [[Paragraph(r[0], muted_style), Paragraph(r[1], bold_style)] for r in info_rows],
        colWidths=[4*cm, 13*cm]
    )
    info_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (0, -1), LGRAY),
        ('TOPPADDING', (0, 0), (-1, -1), 5),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 5),
        ('LEFTPADDING', (0, 0), (-1, -1), 8),
        ('LINEBELOW', (0, 0), (-1, -2), 0.5, MGRAY),
    ]))
    story.append(info_table)
    story.append(Spacer(1, 0.5*cm))

    def criteria_section(title, rows_data):
        if not any(r is not None for r in rows_data):
            return
        story.append(HRFlowable(width=W, thickness=1, color=GOLD, spaceAfter=6))
        story.append(Paragraph(title, ParagraphStyle('sh', fontName='Helvetica-Bold', fontSize=8, textColor=GOLD, spaceBefore=4, spaceAfter=6, characterSpacing=1)))
        header = [
            Paragraph("Critère", ParagraphStyle('th', fontName='Helvetica-Bold', fontSize=8, textColor=WHITE)),
            Paragraph("Valeur", ParagraphStyle('th', fontName='Helvetica-Bold', fontSize=8, textColor=WHITE, alignment=TA_CENTER)),
            Paragraph("Seuil", ParagraphStyle('th', fontName='Helvetica-Bold', fontSize=8, textColor=WHITE, alignment=TA_CENTER)),
            Paragraph("Unité", ParagraphStyle('th', fontName='Helvetica-Bold', fontSize=8, textColor=WHITE, alignment=TA_CENTER)),
            Paragraph("Résultat", ParagraphStyle('th', fontName='Helvetica-Bold', fontSize=8, textColor=WHITE, alignment=TA_CENTER)),
        ]
        table_data = [header] + [r for r in rows_data if r is not None]
        col_w = [6.5*cm, 2*cm, 2*cm, 2.5*cm, 4*cm]
        t = Table(table_data, colWidths=col_w)
        style = [
            ('BACKGROUND', (0, 0), (-1, 0), NAVY),
            ('TOPPADDING', (0, 0), (-1, -1), 6),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
            ('LEFTPADDING', (0, 0), (-1, -1), 8),
            ('LINEBELOW', (0, 0), (-1, -2), 0.5, MGRAY),
        ]
        for i, r in enumerate([r for r in rows_data if r is not None], 1):
            if i % 2 == 0:
                style.append(('BACKGROUND', (0, i), (-1, i), LGRAY))
        t.setStyle(TableStyle(style))
        story.append(t)
        story.append(Spacer(1, 0.5*cm))

    # ── RT2012 ────────────────────────────────────────
    criteria_section("RT2012 — CRITÈRES DE CONFORMITÉ", [
        criteria_row("Bbio (besoins bioclimatiques)", document.rt2012_bbio, "rt2012_bbio"),
        criteria_row("Cep (consommation énergie primaire)", document.rt2012_cep, "rt2012_cep", "kWh ep/m².an"),
        criteria_row("Tic (température intérieure conv.)", document.rt2012_tic, "rt2012_tic", "°C"),
        criteria_row("Etanchéité à l'air", document.rt2012_airtightness, "rt2012_airtightness", "m3/h.m2"),
        criteria_row("ENR (énergies renouvelables)", document.rt2012_enr, "rt2012_enr"),
    ])

    # ── RE2020 ────────────────────────────────────────
    criteria_section("RE2020 — CRITÈRES DE CONFORMITÉ", [
        criteria_row("Cep,nr (énergie non renouvelable)", document.re2020_energy_efficiency, "re2020_energy_efficiency", "kWh/m².an"),
        criteria_row("Ic énergie (émissions CO2 exploitation)", document.re2020_carbon_emissions, "re2020_carbon_emissions", "kgCO2eq/m².an"),
        criteria_row("DH (degrés-heures – confort été)", document.re2020_thermal_comfort, "re2020_thermal_comfort", "DH"),
    ])

    # ── FOOTER ────────────────────────────────────────
    story.append(Spacer(1, 0.3*cm))
    story.append(HRFlowable(width=W, thickness=0.5, color=MGRAY, spaceAfter=6))
    story.append(Paragraph(
        "ConformExpert — Analyse documentaire indépendante RT2012 / RE2020 · contact@conformexpert.fr",
        ParagraphStyle('footer', fontName='Helvetica', fontSize=7.5, textColor=MUTED, alignment=TA_CENTER)
    ))

    doc.build(story)
    buffer.seek(0)
    response = HttpResponse(buffer.read(), content_type='application/pdf')
    safe_name = document.name.replace(' ', '_').replace('/', '-')
    response['Content-Disposition'] = f'attachment; filename="rapport_{safe_name}.pdf"'
    return response


# ──────────────────────────────────────────────
# API REST
# ──────────────────────────────────────────────

@csrf_exempt
@api_view(['GET', 'POST'])
def api_document_list(request):
    if request.method == 'GET':
        documents = Document.objects.all()
        serializer = DocumentSerializer(documents, many=True)
        return Response(serializer.data)
    elif request.method == 'POST':
        serializer = DocumentSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@csrf_exempt
@api_view(['GET'])
def api_document_detail(request, pk):
    document = get_object_or_404(Document, pk=pk)
    serializer = DocumentSerializer(document)
    return Response(serializer.data)


@csrf_exempt
@api_view(['GET'])
def api_results(request):
    documents = Document.objects.all()
    serializer = DocumentSerializer(documents, many=True)
    return Response(serializer.data)


@csrf_exempt
@api_view(['GET'])
def api_history(request):
    documents = Document.objects.all().order_by('-upload_date')
    serializer = DocumentSerializer(documents, many=True)
    return Response(serializer.data)


@csrf_exempt
@api_view(['GET'])
def api_report(request, pk):
    document = get_object_or_404(Document, pk=pk)
    context = {
        'document': document,
        're2020_limits': fetch_re2020_requirements(),
        'rt2012_limits': fetch_rt2012_requirements(),
    }
    try:
        from weasyprint import HTML as WeasyprintHTML
        html_string = render_to_string('main/report_template.html', context)
        pdf = WeasyprintHTML(string=html_string).write_pdf()
        response = HttpResponse(pdf, content_type='application/pdf')
        response['Content-Disposition'] = f'attachment; filename="report_{document.name}.pdf"'
        return response
    except ImportError:
        return Response({'error': 'WeasyPrint non installé.'}, status=500)
