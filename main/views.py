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
    return render(request, "main/import.html", {"form": form})


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
    return render(request, 'main/tracking.html', {
        'document': document,
        'step_list': step_list,
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
        response['Content-Disposition'] = f'attachment; filename="rapport_{document.name}.pdf"'
        return response
    except ImportError:
        return HttpResponse("WeasyPrint non installé.", status=500)


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
