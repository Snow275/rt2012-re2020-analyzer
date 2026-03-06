from django.shortcuts import render, redirect, get_object_or_404
from django.http import HttpResponse, JsonResponse
from django.contrib import messages
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.template.loader import render_to_string
from django.core.mail import send_mail, EmailMultiAlternatives
from django.conf import settings as django_settings
from django.views.decorators.csrf import csrf_exempt
from rest_framework.decorators import api_view
from rest_framework.response import Response
from rest_framework import status

from .models import Document, Analysis, Devis
from .forms import DocumentForm, ContactForm
from .serializers import DocumentSerializer, AnalysisSerializer

import PyPDF2
import re
import threading


def send_mail_async(sujet, corps, from_email, recipient_list):
    """Envoie un email dans un thread séparé pour ne pas bloquer la réponse HTTP."""
    def _send():
        try:
            send_mail(sujet, corps, from_email, recipient_list, fail_silently=False)
            print(f"MAIL ENVOYÉ OK → {recipient_list}")
        except Exception as e:
            print(f"ERREUR MAIL : {e}")
    t = threading.Thread(target=_send)
    t.daemon = True
    t.start()


# ──────────────────────────────────────────────
# EMAILS
# ──────────────────────────────────────────────

SITE_URL = "https://web-production-f6c00.up.railway.app"


def _send_html_async(sujet, template_name, context, destinataire):
    if not destinataire:
        return
    def _send():
        try:
            import sendgrid
            from sendgrid.helpers.mail import Mail, To
            html = render_to_string(f'main/emails/{template_name}', context)
            sg = sendgrid.SendGridAPIClient(api_key=django_settings.SENDGRID_API_KEY)
            message = Mail(
                from_email=django_settings.DEFAULT_FROM_EMAIL,
                to_emails=destinataire,
                subject=sujet,
                html_content=html,
            )
            response = sg.send(message)
            print(f"MAIL SENDGRID OK -> {destinataire} (status {response.status_code})")
        except Exception as e:
            print(f"ERREUR MAIL : {e}")
    t = threading.Thread(target=_send)
    t.daemon = True
    t.start()


def send_mail_reception(document):
    if not document.client_email:
        return
    _send_html_async(
        f"[ConformExpert] Dossier bien reçu — {document.name}",
        "email_reception.html",
        {'doc_id': f"{document.id:04d}", 'doc_name': document.name,
         'client_name': document.client_name or '',
         'date_depot': document.upload_date.strftime('%d/%m/%Y à %H:%M')},
        document.client_email,
    )


def send_mail_validation_devis(document, devis=None):
    if not document.client_email:
        return
    montant_ht = float(devis.montant) if devis and devis.montant else 0
    tva = round(montant_ht * 0.20, 2)
    _send_html_async(
        f"[ConformExpert] Votre devis — {document.name}",
        "email_devis.html",
        {'doc_id': f"{document.id:04d}", 'doc_name': document.name,
         'client_name': document.client_name or '',
         'accepter_url': f"{SITE_URL}/suivi/{document.tracking_token}/?accepter_devis=1",
         'montant_ht': f"{montant_ht:.2f}", 'tva': f"{tva:.2f}",
         'montant_ttc': f"{montant_ht + tva:.2f}",
         'norme': devis.norme if devis else 'RT2012 / RE2020',
         'notes': devis.notes if devis else ''},
        document.client_email,
    )


def send_mail_analyse_commence(document):
    if not document.client_email:
        return
    _send_html_async(
        "[ConformExpert] L'analyse de votre dossier a démarré",
        "email_analyse_commence.html",
        {'doc_id': f"{document.id:04d}", 'doc_name': document.name,
         'client_name': document.client_name or '',
         'tracking_url': f"{SITE_URL}/suivi/{document.tracking_token}/"},
        document.client_email,
    )


def send_mail_analyse_terminee(document):
    if not document.client_email:
        return
    _send_html_async(
        f"[ConformExpert] Votre rapport est disponible — {document.name}",
        "email_analyse_terminee.html",
        {'doc_id': f"{document.id:04d}", 'doc_name': document.name,
         'client_name': document.client_name or '',
         'tracking_url': f"{SITE_URL}/suivi/{document.tracking_token}/",
         'rapport_items': [
             "Analyse complète des critères RT2012 / RE2020",
             "Conclusion de conformité détaillée",
             "Recommandations éventuelles",
             "Rapport PDF téléchargeable",
         ]},
        document.client_email,
    )


# ──────────────────────────────────────────────
# AUTH
# ──────────────────────────────────────────────

def admin_login(request):
    if request.user.is_authenticated:
        return redirect('home')
    if request.method == 'POST':
        username = request.POST.get('username')
        password = request.POST.get('password')
        user = authenticate(request, username=username, password=password)
        if user is not None and user.is_staff:
            login(request, user)
            return redirect(request.GET.get('next', 'home'))
        else:
            messages.error(request, 'Identifiants incorrects ou accès non autorisé.')
    return render(request, 'main/login.html')


def admin_logout(request):
    logout(request)
    return redirect('landing')


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
    """
    Extrait les valeurs numériques du texte PDF selon la norme détectée.
    Supporte : RT2012, RE2020, PEB, MINERGIE, SIA380, CNEB2015/2020, LENOZ.
    Chaque pattern cherche sur tout le texte avec des variantes souples.
    """
    data = {}
    t = text  # on cherche sur tout le texte

    # ── FRANCE RT2012 ──────────────────────────────────────
    for pattern, key in [
        (r'Bbio\s*[=:]\s*([\d.,]+)',        'rt2012_bbio'),
        (r'Cep\s*[=:]\s*([\d.,]+)',         'rt2012_cep'),
        (r'Tic\s*[=:]\s*([\d.,]+)',         'rt2012_tic'),
        (r'[Ee]tanch[e\xe9]it[e\xe9]\s*[=:]\s*([\d.,]+)', 'rt2012_airtightness'),
        (r'ENR\s*[=:]\s*([\d.,]+)',         'rt2012_enr'),
    ]:
        m = re.search(pattern, t, re.IGNORECASE)
        if m:
            data[key] = float(m.group(1).replace(',', '.'))

    # ── FRANCE RE2020 ──────────────────────────────────────
    for pattern, key in [
        (r'Cep,?nr\s*[=:]\s*([\d.,]+)',             're2020_energy_efficiency'),
        (r'DH\s*[=:]\s*([\d.,]+)',                  're2020_thermal_comfort'),
        (r'Ic.{0,10}[ée]nergie\s*[=:]\s*([\d.,]+)', 're2020_carbon_emissions'),
        (r'Ic.{0,10}construction\s*[=:]\s*([\d.,]+)','re2020_ic_construction'),
    ]:
        m = re.search(pattern, t, re.IGNORECASE)
        if m:
            data[key] = float(m.group(1).replace(',', '.'))

    # ── BELGIQUE PEB ───────────────────────────────────────
    for pattern, key in [
        (r'Espec\s*[=:]\s*([\d.,]+)',   'peb_espec'),
        (r'\bEw\b\s*[=:]\s*([\d.,]+)', 'peb_ew'),
        (r'U\s*mur\s*[=:]\s*([\d.,]+)', 'peb_u_mur'),
        (r'U\s*toit\s*[=:]\s*([\d.,]+)','peb_u_toit'),
        (r'U\s*plancher\s*[=:]\s*([\d.,]+)','peb_u_plancher'),
    ]:
        m = re.search(pattern, t, re.IGNORECASE)
        if m:
            data[key] = float(m.group(1).replace(',', '.'))

    # ── SUISSE MINERGIE / SIA380 ───────────────────────────
    for pattern, key in [
        (r'Qh\s*[=:]\s*([\d.,]+)',   'minergie_qh'),
        (r'Qtot\s*[=:]\s*([\d.,]+)', 'minergie_qtot'),
        (r'n50\s*[=:]\s*([\d.,]+)',  'minergie_n50'),
    ]:
        m = re.search(pattern, t, re.IGNORECASE)
        if m:
            data[key] = float(m.group(1).replace(',', '.'))

    # ── CANADA CNEB2015 / CNEB2020 ─────────────────────────
    for pattern, key in [
        (r'[Ii]ntensit[eé].{0,20}[=:]\s*([\d.,]+)', 'cneb_ei'),
        (r'U\s*mur\s*[=:]\s*([\d.,]+)',            'cneb_u_mur'),
        (r'U\s*toit\s*[=:]\s*([\d.,]+)',           'cneb_u_toit'),
        (r'U\s*fen[eê]tre\s*[=:]\s*([\d.,]+)',     'cneb_u_fenetre'),
        (r'[Ii]nfiltration\s*[=:]\s*([\d.,]+)',     'cneb_infiltration'),
    ]:
        m = re.search(pattern, t, re.IGNORECASE)
        if m:
            data[key] = float(m.group(1).replace(',', '.'))

    # ── LUXEMBOURG LENOZ ───────────────────────────────────
    for pattern, key in [
        (r'[Ee]nergie\s+primaire\s*[=:]\s*([\d.,]+)', 'lenoz_ep'),
        (r'\bEw\b\s*[=:]\s*([\d.,]+)',               'lenoz_ew'),
        (r'U\s*mur\s*[=:]\s*([\d.,]+)',               'lenoz_u_mur'),
        (r'U\s*toit\s*[=:]\s*([\d.,]+)',              'lenoz_u_toit'),
    ]:
        m = re.search(pattern, t, re.IGNORECASE)
        if m:
            data[key] = float(m.group(1).replace(',', '.'))

    return data


def analyze_document(document, data):
    # ── FR RT2012 ──
    document.rt2012_bbio        = data.get('rt2012_bbio')
    document.rt2012_cep         = data.get('rt2012_cep')
    document.rt2012_tic         = data.get('rt2012_tic')
    document.rt2012_airtightness= data.get('rt2012_airtightness')
    document.rt2012_enr         = data.get('rt2012_enr')
    # ── FR RE2020 ──
    document.re2020_energy_efficiency = data.get('re2020_energy_efficiency')
    document.re2020_thermal_comfort   = data.get('re2020_thermal_comfort')
    document.re2020_carbon_emissions  = data.get('re2020_carbon_emissions')
    # ── BE PEB ──
    document.peb_espec      = data.get('peb_espec')
    document.peb_ew         = data.get('peb_ew')
    document.peb_u_mur      = data.get('peb_u_mur')
    document.peb_u_toit     = data.get('peb_u_toit')
    document.peb_u_plancher = data.get('peb_u_plancher')
    # ── CH MINERGIE / SIA380 ──
    document.minergie_qh   = data.get('minergie_qh')
    document.minergie_qtot = data.get('minergie_qtot')
    document.minergie_n50  = data.get('minergie_n50')
    document.sia380_qh     = data.get('minergie_qh') or data.get('sia380_qh')
    # ── CA CNEB ──
    document.cneb_ei          = data.get('cneb_ei')
    document.cneb_u_mur       = data.get('cneb_u_mur')
    document.cneb_u_toit      = data.get('cneb_u_toit')
    document.cneb_u_fenetre   = data.get('cneb_u_fenetre')
    document.cneb_infiltration= data.get('cneb_infiltration')
    # ── LU LENOZ ──
    document.lenoz_ep    = data.get('lenoz_ep')
    document.lenoz_ew    = data.get('lenoz_ew')
    document.lenoz_u_mur = data.get('lenoz_u_mur')
    document.lenoz_u_toit= data.get('lenoz_u_toit')
    # Ne pas changer le statut ici — il reste 'recu' jusqu'à validation manuelle
    document.save()


# ──────────────────────────────────────────────
# VUES PUBLIQUES
# ──────────────────────────────────────────────

def landing(request):
    """Page d'accueil publique — vitrine commerciale."""
    return render(request, 'main/landing.html')


@login_required(login_url='/login/')
def home(request):
    from django.utils import timezone
    from datetime import timedelta

    documents = Document.objects.filter(is_active=True).order_by('-upload_date')
    total_projects = documents.count()

    compliant_count = sum(
        1 for doc in documents
        if doc.is_conform is True
    )
    compliance_rate = round((compliant_count / total_projects * 100), 1) if total_projects else 0

    # Dossiers en attente
    pending_count = documents.filter(status='recu').count()

    # Dossiers reçus depuis + de 5 jours sans traitement
    five_days_ago = timezone.now() - timedelta(days=5)
    old_pending = documents.filter(status='recu', upload_date__lt=five_days_ago).count()

    # Devis (protégé si table pas encore créée)
    try:
        recent_devis = list(Devis.objects.all()[:5])
        devis_en_attente = Devis.objects.filter(statut='en_attente').count()
    except Exception:
        recent_devis = []
        devis_en_attente = 0

    context = {
        'documents': documents,
        'total_projects': total_projects,
        'compliance_rate': compliance_rate,
        'pending_count': pending_count,
        'old_pending': old_pending,
        'recent_devis': recent_devis,
        'devis_en_attente': devis_en_attente,
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
            send_mail_reception(document)
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

    # Acceptation du devis via lien email
    devis_accepte = False
    if request.GET.get('accepter_devis') == '1' and document.status == 'recu':
        document.status = 'en_cours'
        document.save()
        send_mail_analyse_commence(document)
        step_list = get_tracking_steps(document)
        progress_pct = 60
        devis_accepte = True

    return render(request, 'main/tracking.html', {
        'document': document,
        'step_list': step_list,
        'progress_pct': progress_pct,
        'devis_accepte': devis_accepte,
    })


@login_required(login_url='/login/')
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


@login_required(login_url='/login/')
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


@login_required(login_url='/login/')
def settings_view(request):
    from main.templatetags.conformity_tags import (
        get_seuils, NORME_FIELDS, NORMES_PAR_PAYS
    )

    PAYS_LABELS = {
        'FR': '🇫🇷 France',
        'BE': '🇧🇪 Belgique',
        'CH': '🇨🇭 Suisse',
        'CA': '🇨🇦 Canada',
        'LU': '🇱🇺 Luxembourg',
    }
    NORME_LABELS = {
        'RT2012': 'RT 2012', 'RE2020': 'RE 2020', 'PEB': 'PEB',
        'MINERGIE': 'Minergie', 'SIA380': 'SIA 380',
        'CNEB2015': 'CNEB 2015', 'CNEB2020': 'CNEB 2020', 'LENOZ': 'LENOZ',
    }

    seuils_par_pays = []
    for pays_code, normes in NORMES_PAR_PAYS.items():
        normes_data = []
        for norme_code in normes:
            seuils = get_seuils('maison', 'H2', pays_code, norme_code)
            fields = NORME_FIELDS.get(norme_code, [])
            fields_seuils = []
            for field, label, unit in fields:
                val = seuils.get(field, '—')
                if isinstance(val, float) and val == int(val):
                    val = int(val)
                fields_seuils.append((label, val, unit))
            normes_data.append((norme_code, NORME_LABELS.get(norme_code, norme_code), fields_seuils))
        seuils_par_pays.append((pays_code, PAYS_LABELS.get(pays_code, pays_code), normes_data))

    return render(request, 'main/settings.html', {
        'seuils_par_pays': seuils_par_pays,
    })


def update_re2020(request):
    if request.method == 'POST':
        messages.success(request, 'Paramètres RE2020 mis à jour.')
    else:
        messages.error(request, 'Méthode invalide.')
    return redirect('settings')


@login_required(login_url='/login/')
def delete_document(request, doc_id):
    if request.method == 'POST':
        document = get_object_or_404(Document, id=doc_id)
        document.delete()
        messages.success(request, 'Dossier supprimé.')
    return redirect('history')


@login_required(login_url='/login/')
def edit_document(request, doc_id):
    document = get_object_or_404(Document, id=doc_id)

    STATUS_CHOICES = [
        ('recu',     'Dossier reçu'),
        ('en_cours', 'Analyse en cours'),
        ('termine',  'Analyse terminée'),
    ]

    # Tous les champs éditables par norme
    ALL_NORME_FIELDS = {
        'RT2012': [
            ('rt2012_bbio',         'Bbio', ''),
            ('rt2012_cep',          'Cep', 'kWh ep/m².an'),
            ('rt2012_tic',          'Tic', '°C'),
            ('rt2012_airtightness', 'Étanchéité', 'm³/h.m²'),
            ('rt2012_enr',          'ENR', ''),
        ],
        'RE2020': [
            ('re2020_energy_efficiency', 'Cep,nr', 'kWh/m².an'),
            ('re2020_carbon_emissions',  'Ic énergie CO₂', 'kgCO2eq/m².an'),
            ('re2020_thermal_comfort',   'DH (confort été)', 'DH'),
        ],
        'PEB': [
            ('peb_espec',     'Espec', 'kWh/m².an'),
            ('peb_ew',        'Ew', ''),
            ('peb_u_mur',     'U mur', 'W/m².K'),
            ('peb_u_toit',    'U toit', 'W/m².K'),
            ('peb_u_plancher','U plancher', 'W/m².K'),
        ],
        'MINERGIE': [
            ('minergie_qh',   'Qh', 'kWh/m².an'),
            ('minergie_qtot', 'Qtot', 'kWh/m².an'),
            ('minergie_n50',  'n50', 'h⁻¹'),
        ],
        'SIA380': [
            ('sia380_qh', 'Qh', 'kWh/m².an'),
        ],
        'CNEB2015': [
            ('cneb_ei',          'Intensité énergétique', 'kWh/m².an'),
            ('cneb_u_mur',       'U mur', 'W/m².K'),
            ('cneb_u_toit',      'U toit', 'W/m².K'),
            ('cneb_u_fenetre',   'U fenêtre', 'W/m².K'),
            ('cneb_infiltration','Infiltration', 'L/s.m²'),
        ],
        'CNEB2020': [
            ('cneb_ei',          'Intensité énergétique', 'kWh/m².an'),
            ('cneb_u_mur',       'U mur', 'W/m².K'),
            ('cneb_u_toit',      'U toit', 'W/m².K'),
            ('cneb_u_fenetre',   'U fenêtre', 'W/m².K'),
            ('cneb_infiltration','Infiltration', 'L/s.m²'),
        ],
        'LENOZ': [
            ('lenoz_ep',    'Énergie primaire', 'kWh/m².an'),
            ('lenoz_ew',    'Ew', ''),
            ('lenoz_u_mur', 'U mur', 'W/m².K'),
            ('lenoz_u_toit','U toit', 'W/m².K'),
        ],
    }

    # Champs pour la norme du dossier courant (pour le template)
    RT2012_FIELDS = ALL_NORME_FIELDS.get('RT2012', [])
    RE2020_FIELDS = ALL_NORME_FIELDS.get('RE2020', [])
    norme_fields  = ALL_NORME_FIELDS.get(document.norme, [])

    if request.method == 'POST':
        # Statut
        new_status = request.POST.get('status')
        old_status = document.status
        if new_status in dict(STATUS_CHOICES):
            document.status = new_status

        # Norme (permet de la changer depuis le formulaire)
        new_norme = request.POST.get('norme', document.norme)
        if new_norme in ALL_NORME_FIELDS:
            document.norme = new_norme

        # Sauvegarder TOUS les champs de toutes les normes présents dans le POST
        for fields in ALL_NORME_FIELDS.values():
            for field, _, _ in fields:
                val = request.POST.get(field, '').strip()
                if val:
                    try:
                        setattr(document, field, float(val.replace(',', '.')))
                    except ValueError:
                        pass

        # Infos client
        document.client_name  = request.POST.get('client_name', '').strip()
        document.client_email = request.POST.get('client_email', '').strip()
        document.admin_notes  = request.POST.get('admin_notes', '').strip()

        document.save()

        # Envoi des emails selon changement de statut
        if old_status != new_status:
            if new_status == 'recu':
                # Dossier validé → envoyer devis
                try:
                    devis = document.devis.filter(statut='en_attente').first()
                except Exception:
                    devis = None
                send_mail_validation_devis(document, devis)
                messages.info(request, f'Email de validation + devis envoyé à {document.client_email}.' if document.client_email else 'Pas d\'email client renseigné.')
            elif new_status == 'en_cours':
                send_mail_analyse_commence(document)
                messages.info(request, f'Email "analyse commencée" envoyé à {document.client_email}.' if document.client_email else 'Pas d\'email client renseigné.')
            elif new_status == 'termine':
                send_mail_analyse_terminee(document)
                messages.info(request, f'Email "rapport disponible" envoyé à {document.client_email}.' if document.client_email else 'Pas d\'email client renseigné.')

        messages.success(request, f'Dossier « {document.name} » mis à jour.')
        return redirect('edit_document', doc_id=doc_id)

    return render(request, 'main/edit_document.html', {
        'document': document,
        'status_choices': STATUS_CHOICES,
        'rt2012_fields': RT2012_FIELDS,
        're2020_fields': RE2020_FIELDS,
        'norme_fields': norme_fields,
        'all_norme_fields': ALL_NORME_FIELDS,
        'norme_choices': Document.NORME_CHOICES,
        'email_steps': [
            ('1', '#60a5fa', 'rgba(59,130,246,.12)', 'Confirmation reception', 'Confirmer la reception du dossier', 'reception'),
            ('2', '#c8a84b', 'rgba(200,168,75,.12)', 'Envoi du devis', "Devis avec bouton d'acceptation", 'devis'),
            ('3', '#2dd4bf', 'rgba(20,184,166,.12)', 'Debut analyse + lien suivi', "Notifier le demarrage de l'analyse", 'analyse_commence'),
            ('4', '#27c93f', 'rgba(39,201,63,.12)', 'Rapport final disponible', 'Rapport telechargeable sur le lien suivi', 'analyse_terminee'),
        ],
    })


@login_required(login_url='/login/')
def send_email_manual(request, doc_id, email_type):
    if request.method != 'POST':
        return redirect('edit_document', doc_id=doc_id)
    document = get_object_or_404(Document, id=doc_id)
    if not document.client_email:
        messages.error(request, 'Aucun email client renseigne.')
        return redirect('edit_document', doc_id=doc_id)
    if email_type == 'reception':
        send_mail_reception(document)
        messages.success(request, f'Email de reception envoye a {document.client_email}.')
    elif email_type == 'devis':
        if request.POST.get('create_devis'):
            montant = request.POST.get('montant', '').strip()
            devis = Devis(
                client_nom=document.client_name or document.client_email,
                client_email=document.client_email,
                projet_nom=request.POST.get('projet_nom', document.name),
                norme=request.POST.get('norme', 'RE2020'),
                montant=float(montant) if montant else None,
                notes=request.POST.get('notes', ''),
                statut='en_attente',
                document=document,
            )
            devis.save()
        else:
            devis = document.devis.filter(statut='en_attente').first()
        send_mail_validation_devis(document, devis)
        messages.success(request, f'Email devis envoyé à {document.client_email}.')
    elif email_type == 'analyse_commence':
        send_mail_analyse_commence(document)
        messages.success(request, f'Email analyse demarree envoye a {document.client_email}.')
    elif email_type == 'analyse_terminee':
        send_mail_analyse_terminee(document)
        messages.success(request, f'Email rapport disponible envoye a {document.client_email}.')
    return redirect('edit_document', doc_id=doc_id)

@login_required(login_url='/login/')
def upload_rapport_pdf(request, doc_id):
    if request.method == 'POST' and request.FILES.get('rapport_pdf'):
        document = get_object_or_404(Document, id=doc_id)
        document.rapport_pdf = request.FILES['rapport_pdf']
        document.save()
        messages.success(request, 'Rapport PDF uploadé avec succès.')
    return redirect('edit_document', doc_id=doc_id)

def download_rapport_word(request, doc_id):
    from docx import Document as DocxDocument
    from docx.shared import Pt, RGBColor, Cm
    from io import BytesIO
    document = get_object_or_404(Document, id=doc_id)
    doc = DocxDocument()
    doc.add_heading(f'Rapport ConformExpert — {document.name}', 0)
    doc.add_paragraph(f'Référence : DOC-{document.id:04d}')
    doc.add_paragraph(f'Client : {document.client_name or "—"}')
    doc.add_paragraph(f'Date : {document.upload_date.strftime("%d/%m/%Y")}')
    doc.add_heading('RT2012', level=1)
    for label, val in [('Bbio', document.rt2012_bbio), ('Cep', document.rt2012_cep), ('Tic', document.rt2012_tic), ('Étanchéité', document.rt2012_airtightness), ('ENR', document.rt2012_enr)]:
        doc.add_paragraph(f'{label} : {val if val is not None else "—"}')
    doc.add_heading('RE2020', level=1)
    for label, val in [('Cep,nr', document.re2020_energy_efficiency), ('Ic énergie', document.re2020_carbon_emissions), ('DH', document.re2020_thermal_comfort)]:
        doc.add_paragraph(f'{label} : {val if val is not None else "—"}')
    buffer = BytesIO()
    doc.save(buffer)
    buffer.seek(0)
    safe_name = document.name.replace(' ', '_')
    response = HttpResponse(buffer.read(), content_type='application/vnd.openxmlformats-officedocument.wordprocessingml.document')
    response['Content-Disposition'] = f'attachment; filename="rapport_{safe_name}.docx"'
    return response


def download_report(request, document_id):
    document = get_object_or_404(Document, id=document_id)

    from io import BytesIO
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.styles import ParagraphStyle
    from reportlab.lib.units import cm
    from reportlab.lib import colors
    from reportlab.platypus import (
        SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle,
        HRFlowable, PageBreak, KeepTogether
    )
    from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT
    from reportlab.platypus.flowables import BalancedColumns
    from main.templatetags.conformity_tags import get_seuils, CRITERIA_GREATER_EQUAL, NORME_FIELDS
    from datetime import date

    # ── Couleurs ──────────────────────────────────────────
    NAVY   = colors.HexColor('#0C1929')
    NAVY2  = colors.HexColor('#112236')
    GOLD   = colors.HexColor('#C8A84B')
    GOLD_L = colors.HexColor('#E0D4A0')
    GREEN  = colors.HexColor('#1A9E2E')
    GREEN_L= colors.HexColor('#E8F8EE')
    RED    = colors.HexColor('#C62828')
    RED_L  = colors.HexColor('#FEF0F0')
    LGRAY  = colors.HexColor('#F8F8FC')
    MGRAY  = colors.HexColor('#E0E0E8')
    WHITE  = colors.white
    MUTED  = colors.HexColor('#888899')
    TEXT   = colors.HexColor('#1A1A2E')

    W = 17 * cm
    PAGE_W, PAGE_H = A4

    buffer = BytesIO()

    # ── Styles ────────────────────────────────────────────
    def s(name, **kw):
        defaults = dict(fontName='Helvetica', fontSize=9, textColor=TEXT, leading=13)
        defaults.update(kw)
        return ParagraphStyle(name, **defaults)

    body   = s('body', spaceAfter=4)
    bold   = s('bold', fontName='Helvetica-Bold')
    muted  = s('muted', textColor=MUTED, fontSize=8)
    center = s('center', alignment=TA_CENTER)
    ok_s   = s('ok',  fontName='Helvetica-Bold', textColor=GREEN, alignment=TA_CENTER)
    nok_s  = s('nok', fontName='Helvetica-Bold', textColor=RED,   alignment=TA_CENTER)
    gold_s = s('gold',fontName='Helvetica-Bold', textColor=GOLD,  fontSize=8, characterSpacing=1)
    white_s= s('white',textColor=WHITE)
    small  = s('small', fontSize=7.5, textColor=MUTED)

    seuils    = get_seuils(document.building_type, document.climate_zone, document.pays, document.norme)
    is_conform= document.is_conform
    norme     = document.norme
    pays_labels = {'FR': 'France', 'BE': 'Belgique', 'CH': 'Suisse', 'CA': 'Canada', 'LU': 'Luxembourg'}
    pays_label  = pays_labels.get(document.pays, document.pays)
    today_str   = date.today().strftime("%d/%m/%Y")

    # ── Helpers ───────────────────────────────────────────
    def verdict_para(val):
        if val is None: return Paragraph("— Non évalué", center)
        if val:         return Paragraph("✓  Conforme",  ok_s)
        return              Paragraph("✗  Non conforme", nok_s)

    def criteria_row(label, value, key, unit=""):
        if value is None:
            return None
        limit  = seuils.get(key, "—")
        sign   = "≥" if key in CRITERIA_GREATER_EQUAL else "≤"
        if isinstance(limit, (int, float)):
            conform = value >= limit if key in CRITERIA_GREATER_EQUAL else value <= limit
        else:
            conform = False
        return [
            Paragraph(label, body),
            Paragraph(f"<b>{value}</b>", s('v', fontName='Helvetica-Bold', alignment=TA_CENTER)),
            Paragraph(f"{sign} {limit}", s('sl', textColor=MUTED, alignment=TA_CENTER)),
            Paragraph(unit, s('u', fontSize=8, textColor=MUTED, alignment=TA_CENTER)),
            Paragraph("✓ Conforme" if conform else "✗ Non conforme",
                      s('r', fontName='Helvetica-Bold',
                        textColor=GREEN if conform else RED, alignment=TA_CENTER)),
        ]

    def section_header(title, num=None):
        label = f"{num}. {title}" if num else title
        return [
            HRFlowable(width=W, thickness=1.5, color=GOLD, spaceAfter=5),
            Paragraph(label.upper(), s('sh', fontName='Helvetica-Bold', fontSize=8,
                                       textColor=GOLD, spaceBefore=4, spaceAfter=6, characterSpacing=1)),
        ]

    def criteria_table(rows_data):
        rows = [r for r in rows_data if r is not None]
        if not rows:
            return []
        header = [
            Paragraph("Critère",  s('th', fontName='Helvetica-Bold', fontSize=8, textColor=WHITE)),
            Paragraph("Valeur",   s('th2', fontName='Helvetica-Bold', fontSize=8, textColor=WHITE, alignment=TA_CENTER)),
            Paragraph("Seuil",    s('th3', fontName='Helvetica-Bold', fontSize=8, textColor=WHITE, alignment=TA_CENTER)),
            Paragraph("Unité",    s('th4', fontName='Helvetica-Bold', fontSize=8, textColor=WHITE, alignment=TA_CENTER)),
            Paragraph("Résultat", s('th5', fontName='Helvetica-Bold', fontSize=8, textColor=WHITE, alignment=TA_CENTER)),
        ]
        data = [header] + rows
        col_w = [6.5*cm, 2*cm, 2*cm, 2.5*cm, 4*cm]
        t = Table(data, colWidths=col_w)
        style = [
            ('BACKGROUND',   (0,0), (-1,0), NAVY),
            ('TOPPADDING',   (0,0), (-1,-1), 6),
            ('BOTTOMPADDING',(0,0), (-1,-1), 6),
            ('LEFTPADDING',  (0,0), (-1,-1), 8),
            ('RIGHTPADDING', (0,0), (-1,-1), 8),
            ('LINEBELOW',    (0,0), (-1,-2), 0.5, MGRAY),
            ('ROUNDEDCORNERS', [4,4,4,4]),
        ]
        for i in range(1, len(data)):
            if i % 2 == 0:
                style.append(('BACKGROUND', (0,i), (-1,i), LGRAY))
        t.setStyle(TableStyle(style))
        return [t, Spacer(1, 0.4*cm)]

    def reco_box(icon, title, text, bg, border_color):
        inner = Table([[
            Paragraph(icon, s('ri', fontSize=14)),
            Table([[
                Paragraph(title, s('rt', fontName='Helvetica-Bold', fontSize=9, textColor=TEXT)),
                Paragraph(text,  s('rb', fontSize=8.5, textColor=colors.HexColor('#555555'), leading=13)),
            ]], colWidths=[W - 2.5*cm])
        ]], colWidths=[0.8*cm, W - 1.5*cm])
        inner.setStyle(TableStyle([
            ('VALIGN', (0,0), (-1,-1), 'TOP'),
            ('LEFTPADDING', (0,0), (-1,-1), 0),
            ('RIGHTPADDING', (0,0), (-1,-1), 0),
            ('TOPPADDING', (0,0), (-1,-1), 0),
            ('BOTTOMPADDING', (0,0), (-1,-1), 0),
        ]))
        outer = Table([[inner]], colWidths=[W])
        outer.setStyle(TableStyle([
            ('BACKGROUND',    (0,0), (-1,-1), bg),
            ('LINEAFTER',     (0,0), (0,-1),  3, border_color),
            ('LINEBEFORE',    (0,0), (0,-1),  3, border_color),
            ('TOPPADDING',    (0,0), (-1,-1), 8),
            ('BOTTOMPADDING', (0,0), (-1,-1), 8),
            ('LEFTPADDING',   (0,0), (-1,-1), 10),
            ('RIGHTPADDING',  (0,0), (-1,-1), 10),
            ('ROUNDEDCORNERS',[4,4,4,4]),
        ]))
        return [outer, Spacer(1, 0.3*cm)]

    # ── PAGE 1 : COUVERTURE ───────────────────────────────
    story = []

    # Fond navy pleine page simulé avec un grand tableau
    verdict_color = GREEN if is_conform else (RED if is_conform is not None else MUTED)
    verdict_bg    = GREEN_L if is_conform else (RED_L if is_conform is not None else LGRAY)
    verdict_text  = "✓  Dossier Conforme" if is_conform else ("✗  Non Conforme" if is_conform is not None else "—  En cours d'analyse")

    cover_data = [[
        Paragraph(
            f'<font color="#C8A84B" size="18"><b>Conform</b></font>'
            f'<font color="white" size="18"><b>Expert</b></font>',
            s('logo', fontName='Helvetica-Bold', fontSize=18, textColor=WHITE, leading=22)
        )
    ],[
        Spacer(1, 1.5*cm)
    ],[
        Paragraph(
            'RAPPORT D\'ANALYSE DE CONFORMITÉ THERMIQUE',
            s('ey', fontName='Helvetica-Bold', fontSize=8, textColor=GOLD,
              characterSpacing=1.5, leading=12)
        )
    ],[
        Paragraph(
            f'<font color="white" size="22"><b>{document.name}</b></font>',
            s('ct', fontSize=22, textColor=WHITE, leading=28)
        )
    ],[
        Paragraph(
            f'<font color="#AAAACC">{document.get_building_type_display()} &nbsp;·&nbsp; {norme} &nbsp;·&nbsp; {pays_label}</font>',
            s('cs', fontSize=11, textColor=MUTED, leading=16)
        )
    ],[
        Spacer(1, 0.8*cm)
    ],[
        Table([[
            Paragraph(verdict_text,
                      s('vt', fontName='Helvetica-Bold', fontSize=13,
                        textColor=verdict_color, alignment=TA_CENTER))
        ]], colWidths=[9*cm],
            style=TableStyle([
                ('BACKGROUND',    (0,0),(-1,-1), verdict_bg),
                ('BOX',           (0,0),(-1,-1), 1.5, verdict_color),
                ('TOPPADDING',    (0,0),(-1,-1), 10),
                ('BOTTOMPADDING', (0,0),(-1,-1), 10),
                ('ROUNDEDCORNERS',[20,20,20,20]),
            ]))
    ],[
        Spacer(1, 1*cm)
    ],[
        # Grille méta-données
        Table([
            [
                Table([[Paragraph('RÉFÉRENCE', muted)],[Paragraph(f'DOC-{document.id:04d}', s('mv',fontName='Helvetica-Bold',textColor=WHITE,fontSize=10))]],
                      style=TableStyle([('TOPPADDING',(0,0),(-1,-1),0),('BOTTOMPADDING',(0,0),(-1,-1),0),('LEFTPADDING',(0,0),(-1,-1),0),('RIGHTPADDING',(0,0),(-1,-1),0)])),
                Table([[Paragraph('DATE DU RAPPORT', muted)],[Paragraph(today_str, s('mv2',fontName='Helvetica-Bold',textColor=WHITE,fontSize=10))]],
                      style=TableStyle([('TOPPADDING',(0,0),(-1,-1),0),('BOTTOMPADDING',(0,0),(-1,-1),0),('LEFTPADDING',(0,0),(-1,-1),0),('RIGHTPADDING',(0,0),(-1,-1),0)])),
                Table([[Paragraph('CLIENT', muted)],[Paragraph(document.client_name or '—', s('mv3',fontName='Helvetica-Bold',textColor=WHITE,fontSize=10))]],
                      style=TableStyle([('TOPPADDING',(0,0),(-1,-1),0),('BOTTOMPADDING',(0,0),(-1,-1),0),('LEFTPADDING',(0,0),(-1,-1),0),('RIGHTPADDING',(0,0),(-1,-1),0)])),
            ]
        ], colWidths=[5.6*cm, 5.6*cm, 5.8*cm],
           style=TableStyle([('TOPPADDING',(0,0),(-1,-1),0),('BOTTOMPADDING',(0,0),(-1,-1),0),('LEFTPADDING',(0,0),(-1,-1),0),('RIGHTPADDING',(0,0),(-1,-1),0)]))
    ]]

    cover_table = Table(cover_data, colWidths=[W])
    cover_table.setStyle(TableStyle([
        ('BACKGROUND',    (0,0), (-1,-1), NAVY),
        ('TOPPADDING',    (0,0), (-1,-1), 0),
        ('BOTTOMPADDING', (0,0), (-1,-1), 6),
        ('LEFTPADDING',   (0,0), (-1,-1), 0),
        ('RIGHTPADDING',  (0,0), (-1,-1), 0),
        ('VALIGN',        (0,0), (-1,-1), 'MIDDLE'),
    ]))

    # Wrapper cover pleine page
    cover_page = Table([[cover_table]], colWidths=[PAGE_W - 4*cm])
    cover_page.setStyle(TableStyle([
        ('BACKGROUND',    (0,0), (-1,-1), NAVY),
        ('TOPPADDING',    (0,0), (-1,-1), 2.5*cm),
        ('BOTTOMPADDING', (0,0), (-1,-1), 1.5*cm),
        ('LEFTPADDING',   (0,0), (-1,-1), 2.2*cm),
        ('RIGHTPADDING',  (0,0), (-1,-1), 2.2*cm),
    ]))
    story.append(cover_page)

    # Pied de couverture
    footer_cover = Table([[
        Paragraph('ConformExpert · Analyse documentaire indépendante', s('fcl', fontSize=8, textColor=colors.HexColor('#666677'))),
        Paragraph('Confidentiel · Usage interne', s('fcr', fontSize=8, textColor=GOLD, alignment=TA_RIGHT)),
    ]], colWidths=[W/2, W/2])
    footer_cover.setStyle(TableStyle([
        ('BACKGROUND',    (0,0),(-1,-1), NAVY),
        ('TOPPADDING',    (0,0),(-1,-1), 8),
        ('BOTTOMPADDING', (0,0),(-1,-1), 8),
        ('LINEABOVE',     (0,0),(-1,-1), 0.5, colors.HexColor('#C8A84B33')),
        ('LEFTPADDING',   (0,0),(-1,-1), 0),
        ('RIGHTPADDING',  (0,0),(-1,-1), 0),
    ]))
    story.append(footer_cover)
    story.append(PageBreak())

    # ── PAGE 2 : SOMMAIRE ─────────────────────────────────
    story += section_header("Sommaire")
    story.append(Paragraph(f"Rapport d'analyse — {document.name}", muted))
    story.append(Spacer(1, 0.4*cm))

    toc_items = [
        ("1. Résumé exécutif & verdict global", "3"),
        ("2. Informations du dossier", "3"),
        (f"3. Analyse {norme} — Critères de conformité", "4"),
        ("4. Recommandations & points d'attention", "5"),
    ]
    if document.admin_notes:
        toc_items.append(("5. Notes & observations de l'expert", "5"))
    toc_items.append(("6. Mentions légales & disclaimer", "6"))

    for label, page in toc_items:
        row = Table([[
            Paragraph(label, s('tl', fontSize=10, fontName='Helvetica')),
            Paragraph(page,  s('tp', fontSize=9,  fontName='Helvetica-Bold', textColor=GOLD, alignment=TA_RIGHT)),
        ]], colWidths=[W - 1.5*cm, 1.5*cm])
        row.setStyle(TableStyle([
            ('TOPPADDING',    (0,0),(-1,-1), 7),
            ('BOTTOMPADDING', (0,0),(-1,-1), 7),
            ('LINEBELOW',     (0,0),(-1,-1), 0.5, MGRAY),
            ('LEFTPADDING',   (0,0),(-1,-1), 0),
            ('RIGHTPADDING',  (0,0),(-1,-1), 0),
        ]))
        story.append(row)

    story.append(PageBreak())

    # ── PAGE 3 : RÉSUMÉ + INFOS ───────────────────────────
    story += section_header("Résumé exécutif & verdict global", 1)

    # Verdict banner
    verdict_banner = Table([[
        Table([[
            Paragraph(f'VERDICT — {norme}',
                      s('vbl', fontName='Helvetica-Bold', fontSize=8, textColor=GOLD, characterSpacing=1)),
            Paragraph(verdict_text,
                      s('vbv', fontName='Helvetica-Bold', fontSize=16, textColor=WHITE, leading=22)),
        ]], colWidths=[W - 2*cm]),
    ]], colWidths=[W])
    verdict_banner.setStyle(TableStyle([
        ('BACKGROUND',    (0,0),(-1,-1), NAVY),
        ('TOPPADDING',    (0,0),(-1,-1), 14),
        ('BOTTOMPADDING', (0,0),(-1,-1), 14),
        ('LEFTPADDING',   (0,0),(-1,-1), 16),
        ('RIGHTPADDING',  (0,0),(-1,-1), 16),
        ('ROUNDEDCORNERS',[6,6,6,6]),
    ]))
    story.append(verdict_banner)
    story.append(Spacer(1, 0.6*cm))

    story += section_header("Informations du dossier", 2)
    info_rows = [
        ["Référence",        f"DOC-{document.id:04d}"],
        ["Norme analysée",   norme],
        ["Pays",             pays_label],
        ["Type de bâtiment", document.get_building_type_display()],
        ["Zone climatique",  f"Zone {document.climate_zone}" if document.climate_zone else "—"],
        ["Date de dépôt",    document.upload_date.strftime("%d/%m/%Y")],
        ["Date du rapport",  today_str],
        ["Client",           document.client_name or "—"],
        ["Email client",     document.client_email or "—"],
    ]
    info_table = Table(
        [[Paragraph(r[0], muted), Paragraph(r[1], bold)] for r in info_rows],
        colWidths=[4.5*cm, 12.5*cm]
    )
    info_table.setStyle(TableStyle([
        ('BACKGROUND',    (0,0), (0,-1), LGRAY),
        ('TOPPADDING',    (0,0), (-1,-1), 6),
        ('BOTTOMPADDING', (0,0), (-1,-1), 6),
        ('LEFTPADDING',   (0,0), (-1,-1), 8),
        ('RIGHTPADDING',  (0,0), (-1,-1), 8),
        ('LINEBELOW',     (0,0), (-1,-2), 0.5, MGRAY),
    ]))
    story.append(info_table)
    story.append(PageBreak())

    # ── PAGE 4 : CRITÈRES ─────────────────────────────────
    story += section_header(f"{norme} — Critères de conformité", 3)

    if norme == 'RT2012':
        story += criteria_table([
            criteria_row("Bbio — Besoins bioclimatiques",           document.rt2012_bbio,         "rt2012_bbio"),
            criteria_row("Cep — Consommation énergie primaire",     document.rt2012_cep,           "rt2012_cep",  "kWh ep/m².an"),
            criteria_row("Tic — Température intérieure conv.",       document.rt2012_tic,           "rt2012_tic",  "°C"),
            criteria_row("Étanchéité à l'air",                      document.rt2012_airtightness,  "rt2012_airtightness", "m³/h.m²"),
            criteria_row("ENR — Énergies renouvelables",             document.rt2012_enr,           "rt2012_enr"),
        ])
    elif norme == 'RE2020':
        story += criteria_table([
            criteria_row("Cep,nr — Énergie non renouvelable",        document.re2020_energy_efficiency, "re2020_energy_efficiency", "kWh/m².an"),
            criteria_row("Ic énergie — Émissions CO₂ exploitation",  document.re2020_carbon_emissions,  "re2020_carbon_emissions",  "kgCO2eq/m².an"),
            criteria_row("DH — Degrés-heures (confort été)",         document.re2020_thermal_comfort,   "re2020_thermal_comfort",   "DH"),
        ])
    elif norme == 'PEB':
        story += criteria_table([
            criteria_row("Espec — Énergie spécifique",               document.peb_espec,      "peb_espec",      "kWh/m².an"),
            criteria_row("Ew — Indicateur global de performance",     document.peb_ew,         "peb_ew"),
            criteria_row("U mur — Coefficient thermique",             document.peb_u_mur,      "peb_u_mur",      "W/m².K"),
            criteria_row("U toit — Coefficient thermique",            document.peb_u_toit,     "peb_u_toit",     "W/m².K"),
            criteria_row("U plancher — Coefficient thermique",        document.peb_u_plancher, "peb_u_plancher", "W/m².K"),
        ])
    elif norme == 'MINERGIE':
        story += criteria_table([
            criteria_row("Qh — Chaleur de chauffage annuelle",        document.minergie_qh,   "minergie_qh",   "kWh/m².an"),
            criteria_row("Qtot — Énergie totale pondérée",            document.minergie_qtot, "minergie_qtot", "kWh/m².an"),
            criteria_row("n50 — Taux de renouvellement d'air",        document.minergie_n50,  "minergie_n50",  "h⁻¹"),
        ])
    elif norme == 'SIA380':
        story += criteria_table([
            criteria_row("Qh — Chaleur de chauffage (SIA 380/1)",     document.sia380_qh, "sia380_qh", "kWh/m².an"),
        ])
    elif norme in ('CNEB2015', 'CNEB2020'):
        story += criteria_table([
            criteria_row("Intensité énergétique",                     document.cneb_ei,           "cneb_ei",           "kWh/m².an"),
            criteria_row("U mur — Valeur thermique enveloppe",        document.cneb_u_mur,        "cneb_u_mur",        "W/m².K"),
            criteria_row("U toit — Valeur thermique toiture",         document.cneb_u_toit,       "cneb_u_toit",       "W/m².K"),
            criteria_row("U fenêtre — Performance des vitrages",      document.cneb_u_fenetre,    "cneb_u_fenetre",    "W/m².K"),
            criteria_row("Infiltration — Étanchéité à l'air",         document.cneb_infiltration, "cneb_infiltration", "L/s.m²"),
        ])
    elif norme == 'LENOZ':
        story += criteria_table([
            criteria_row("Énergie primaire",                          document.lenoz_ep,     "lenoz_ep",     "kWh/m².an"),
            criteria_row("Ew — Indicateur de performance globale",    document.lenoz_ew,     "lenoz_ew"),
            criteria_row("U mur — Coefficient thermique",             document.lenoz_u_mur,  "lenoz_u_mur",  "W/m².K"),
            criteria_row("U toit — Coefficient thermique",            document.lenoz_u_toit, "lenoz_u_toit", "W/m².K"),
        ])

    story.append(PageBreak())

    # ── PAGE 5 : RECOMMANDATIONS ──────────────────────────
    story += section_header("Recommandations & points d'attention", 4)

    if is_conform is True:
        story += reco_box("✅", f"Dossier conforme aux exigences {norme}",
                          "L'ensemble des critères analysés respecte les seuils réglementaires en vigueur. Aucune action corrective n'est requise.",
                          GREEN_L, GREEN)

    if is_conform is None:
        story += reco_box("📋", "Analyse en cours — données incomplètes",
                          "Les données nécessaires à l'évaluation complète n'ont pas encore été renseignées. Les recommandations seront disponibles une fois l'analyse finalisée.",
                          LGRAY, MUTED)

    # Recos par norme
    if norme == 'RT2012':
        if document.rt2012_bbio is not None and document.rt2012_bbio > seuils.get('rt2012_bbio', 9999):
            story += reco_box("⚠", "Bbio — Besoins bioclimatiques non conformes",
                              "Améliorer l'isolation de l'enveloppe, optimiser l'orientation et les surfaces vitrées, renforcer la compacité du bâtiment.",
                              RED_L, RED)
        if document.rt2012_cep is not None and document.rt2012_cep > seuils.get('rt2012_cep', 9999):
            story += reco_box("⚠", "Cep — Consommation énergétique non conforme",
                              "Optimiser les systèmes de chauffage/climatisation, installer des équipements haute efficacité, intégrer des énergies renouvelables.",
                              RED_L, RED)
        if document.rt2012_tic is not None and document.rt2012_tic > seuils.get('rt2012_tic', 9999):
            story += reco_box("🌡", "Tic — Température intérieure conventionnelle élevée",
                              "Renforcer la protection solaire, améliorer l'inertie thermique, prévoir une ventilation nocturne efficace.",
                              colors.HexColor('#FFFBF0'), GOLD)
        if document.rt2012_airtightness is not None and document.rt2012_airtightness > seuils.get('rt2012_airtightness', 9999):
            story += reco_box("💨", "Étanchéité à l'air insuffisante",
                              "Revoir les jonctions et points singuliers de l'enveloppe, traiter les passages de réseaux, réaliser un test d'infiltrométrie.",
                              RED_L, RED)

    elif norme == 'RE2020':
        if document.re2020_energy_efficiency is not None and document.re2020_energy_efficiency > seuils.get('re2020_energy_efficiency', 9999):
            story += reco_box("⚠", "Cep,nr — Énergie non renouvelable excessive",
                              "Privilégier des énergies décarbonées (PAC, solaire thermique), améliorer l'isolation et réduire les consommations auxiliaires.",
                              RED_L, RED)
        if document.re2020_carbon_emissions is not None and document.re2020_carbon_emissions > seuils.get('re2020_carbon_emissions', 9999):
            story += reco_box("🌍", "Ic énergie — Émissions carbone non conformes",
                              "Basculer vers des énergies renouvelables, remplacer les systèmes à combustibles fossiles, optimiser la consommation globale.",
                              RED_L, RED)
        if document.re2020_thermal_comfort is not None and document.re2020_thermal_comfort > seuils.get('re2020_thermal_comfort', 9999):
            story += reco_box("🌡", "DH — Confort d'été insuffisant",
                              "Installer des brise-soleils ou débords de toiture, augmenter l'inertie thermique, prévoir une ventilation nocturne.",
                              colors.HexColor('#FFFBF0'), GOLD)

    elif norme == 'PEB':
        if document.peb_espec is not None and document.peb_espec > seuils.get('peb_espec', 9999):
            story += reco_box("⚠", "Espec — Énergie spécifique non conforme (PEB)",
                              "Améliorer l'isolation globale, optimiser les systèmes de chauffage et ventilation, recourir aux énergies renouvelables.",
                              RED_L, RED)
        if document.peb_u_mur is not None and document.peb_u_mur > seuils.get('peb_u_mur', 9999):
            story += reco_box("🧱", "U mur — Isolation des parois insuffisante",
                              "Renforcer l'isolation des murs par l'intérieur ou l'extérieur pour atteindre le coefficient U requis par la réglementation PEB.",
                              RED_L, RED)

    elif norme == 'MINERGIE':
        if document.minergie_qh is not None and document.minergie_qh > seuils.get('minergie_qh', 9999):
            story += reco_box("⚠", "Qh — Besoins de chaleur trop élevés (Minergie)",
                              "Améliorer l'isolation de l'enveloppe (murs, toiture, plancher), optimiser les vitrages et réduire les ponts thermiques.",
                              RED_L, RED)
        if document.minergie_n50 is not None and document.minergie_n50 > seuils.get('minergie_n50', 9999):
            story += reco_box("💨", "n50 — Étanchéité à l'air insuffisante (Minergie)",
                              "Traiter les points singuliers (passages de réseaux, jonctions menuiseries), mettre en place une membrane d'étanchéité continue.",
                              RED_L, RED)

    elif norme in ('CNEB2015', 'CNEB2020'):
        if document.cneb_ei is not None and document.cneb_ei > seuils.get('cneb_ei', 9999):
            story += reco_box("⚠", f"Intensité énergétique non conforme ({norme})",
                              "Réduire les besoins en chauffage et climatisation, améliorer l'enveloppe thermique, intégrer des systèmes à haute efficacité.",
                              RED_L, RED)

    elif norme == 'LENOZ':
        if document.lenoz_ep is not None and document.lenoz_ep > seuils.get('lenoz_ep', 9999):
            story += reco_box("⚠", "Énergie primaire non conforme (LENOZ)",
                              "Optimiser les systèmes énergétiques, intégrer des sources renouvelables et améliorer l'enveloppe thermique du bâtiment.",
                              RED_L, RED)

    # Notes admin
    if document.admin_notes:
        story += section_header("Notes & observations de l'expert", 5)
        notes_table = Table([[
            Paragraph(document.admin_notes.replace('\n', '<br/>'),
                      s('nt', fontSize=9, textColor=TEXT, leading=14))
        ]], colWidths=[W])
        notes_table.setStyle(TableStyle([
            ('BACKGROUND',    (0,0),(-1,-1), LGRAY),
            ('LINEBEFORE',    (0,0),(0,-1),  3, GOLD),
            ('TOPPADDING',    (0,0),(-1,-1), 10),
            ('BOTTOMPADDING', (0,0),(-1,-1), 10),
            ('LEFTPADDING',   (0,0),(-1,-1), 12),
            ('RIGHTPADDING',  (0,0),(-1,-1), 12),
        ]))
        story.append(notes_table)

    story.append(PageBreak())

    # ── PAGE 6 : MENTIONS LÉGALES ─────────────────────────
    story += section_header("Mentions légales & disclaimer", 6)

    disclaimer_items = [
        ("Nature du rapport",
         "Ce rapport est établi sur la base des documents fournis par le client et constitue une analyse documentaire indépendante. Il ne se substitue pas à une attestation officielle de conformité délivrée par un organisme accrédité."),
        ("Responsabilité",
         "ConformExpert s'engage à fournir une analyse rigoureuse et objective des documents transmis. La conformité finale du bâtiment relève de la responsabilité du maître d'ouvrage et des professionnels en charge de la construction."),
        ("Confidentialité",
         "Ce document est strictement confidentiel et destiné exclusivement au client mentionné en page de couverture. Toute reproduction ou diffusion sans autorisation écrite de ConformExpert est interdite."),
        ("Réglementations de référence",
         "RT2012 : Arrêté du 26 octobre 2010 · RE2020 : Décret n°2021-1004 du 29 juillet 2021 · PEB : Directive européenne 2010/31/UE · Minergie / SIA380 : Normes SIA Suisse · CNEB : Code national de l'énergie pour les bâtiments (Canada) · LENOZ : Règlement grand-ducal du 23 juillet 2016 (Luxembourg)"),
        ("Contact",
         "ConformExpert · contact@conformexpert.fr · Délai garanti 15 jours ouvrés"),
    ]

    for title, text in disclaimer_items:
        disc_table = Table([[
            Paragraph(title, s('dt', fontName='Helvetica-Bold', fontSize=9, textColor=TEXT)),
            Paragraph(text,  s('dd', fontSize=8.5, textColor=colors.HexColor('#555555'), leading=13)),
        ]], colWidths=[4*cm, W - 4*cm])
        disc_table.setStyle(TableStyle([
            ('BACKGROUND',    (0,0),(-1,-1), LGRAY),
            ('TOPPADDING',    (0,0),(-1,-1), 8),
            ('BOTTOMPADDING', (0,0),(-1,-1), 8),
            ('LEFTPADDING',   (0,0),(-1,-1), 10),
            ('RIGHTPADDING',  (0,0),(-1,-1), 10),
            ('LINEBELOW',     (0,0),(-1,-1), 0.5, MGRAY),
            ('VALIGN',        (0,0),(-1,-1), 'TOP'),
        ]))
        story.append(disc_table)

    # ── BUILD ─────────────────────────────────────────────
    def add_footer(canvas, doc_obj):
        canvas.saveState()
        canvas.setFont('Helvetica', 7.5)
        canvas.setFillColor(MUTED)
        canvas.drawString(2*cm, 1.2*cm, f"ConformExpert · Analyse indépendante {norme} · {pays_label}")
        canvas.drawRightString(PAGE_W - 2*cm, 1.2*cm, f"Page {doc_obj.page}")
        canvas.setStrokeColor(MGRAY)
        canvas.setLineWidth(0.5)
        canvas.line(2*cm, 1.5*cm, PAGE_W - 2*cm, 1.5*cm)
        canvas.restoreState()

    doc_pdf = SimpleDocTemplate(
        buffer, pagesize=A4,
        leftMargin=2*cm, rightMargin=2*cm,
        topMargin=2*cm, bottomMargin=2.5*cm,
        title=f"Rapport ConformExpert – {document.name}"
    )
    doc_pdf.build(story, onLaterPages=add_footer, onFirstPage=lambda c, d: None)

    buffer.seek(0)
    response = HttpResponse(buffer.read(), content_type='application/pdf')
    safe_name = document.name.replace(' ', '_').replace('/', '-')
    response['Content-Disposition'] = f'inline; filename="rapport_{safe_name}.pdf"'
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


# ──────────────────────────────────────────────
# DEVIS
# ──────────────────────────────────────────────

@login_required(login_url='/login/')
def devis_list(request):
    from django.db.models import Sum
    from datetime import date
    current_statut = request.GET.get('statut', '')
    qs = Devis.objects.all()
    if current_statut:
        qs = qs.filter(statut=current_statut)

    # KPIs
    today = date.today()
    nb_acceptes = Devis.objects.filter(statut='accepte').count()
    nb_attente  = Devis.objects.filter(statut='en_attente').count()
    nb_refuses  = Devis.objects.filter(statut='refuse').count()
    total       = Devis.objects.count()

    ca_mois  = Devis.objects.filter(statut='accepte', created_at__year=today.year, created_at__month=today.month).aggregate(s=Sum('montant'))['s'] or 0
    ca_total = Devis.objects.filter(statut='accepte').aggregate(s=Sum('montant'))['s'] or 0
    ca_attente = Devis.objects.filter(statut='en_attente').aggregate(s=Sum('montant'))['s'] or 0

    taux_conversion = round(nb_acceptes / total * 100) if total else 0
    taux_attente    = round(nb_attente  / total * 100) if total else 0
    taux_refuses    = round(nb_refuses  / total * 100) if total else 0

    # Revenus 6 derniers mois
    from datetime import timedelta
    import calendar
    revenus_mois = []
    max_montant = 1
    for i in range(5, -1, -1):
        m = (today.month - i - 1) % 12 + 1
        y = today.year - ((today.month - i - 1) // 12)
        montant = Devis.objects.filter(statut='accepte', created_at__year=y, created_at__month=m).aggregate(s=Sum('montant'))['s'] or 0
        revenus_mois.append({'label': calendar.month_abbr[m][:3], 'montant': int(montant), 'raw': montant})
        if montant > max_montant:
            max_montant = montant
    for r in revenus_mois:
        r['pct'] = round(r['raw'] / max_montant * 100) if max_montant else 0

    return render(request, 'main/devis_list.html', {
        'devis_list': qs,
        'total': total,
        'nb_acceptes': nb_acceptes,
        'nb_attente': nb_attente,
        'nb_refuses': nb_refuses,
        'ca_mois': int(ca_mois),
        'ca_total': int(ca_total),
        'ca_attente': int(ca_attente),
        'taux_conversion': taux_conversion,
        'taux_attente': taux_attente,
        'taux_refuses': taux_refuses,
        'revenus_mois': revenus_mois,
        'current_statut': current_statut,
        'statut_choices': Devis.STATUT_CHOICES,
    })


@login_required(login_url='/login/')
def devis_create(request):
    if request.method == 'POST':
        d = Devis()
        d.client_nom   = request.POST.get('client_nom', '').strip()
        d.client_email = request.POST.get('client_email', '').strip()
        d.client_phone = request.POST.get('client_phone', '').strip()
        d.projet_nom   = request.POST.get('projet_nom', '').strip()
        d.type_batiment = request.POST.get('type_batiment', 'maison')
        d.norme        = request.POST.get('norme', 'RE2020')
        d.statut       = request.POST.get('statut', 'en_attente')
        d.notes        = request.POST.get('notes', '').strip()
        montant = request.POST.get('montant', '').strip()
        d.montant = float(montant) if montant else None
        d.save()
        messages.success(request, f'Devis pour {d.client_nom} créé.')
        return redirect('devis_edit', d.id)
    return render(request, 'main/devis_form.html', {'devis': None})


@login_required(login_url='/login/')
def devis_edit(request, devis_id):
    d = get_object_or_404(Devis, id=devis_id)
    if request.method == 'POST':
        d.client_nom   = request.POST.get('client_nom', '').strip()
        d.client_email = request.POST.get('client_email', '').strip()
        d.client_phone = request.POST.get('client_phone', '').strip()
        d.projet_nom   = request.POST.get('projet_nom', '').strip()
        d.type_batiment = request.POST.get('type_batiment', 'maison')
        d.norme        = request.POST.get('norme', 'RE2020')
        d.statut       = request.POST.get('statut', 'en_attente')
        d.notes        = request.POST.get('notes', '').strip()
        montant = request.POST.get('montant', '').strip()
        d.montant = float(montant) if montant else None
        d.save()
        messages.success(request, 'Devis mis à jour.')
        return redirect('devis_edit', d.id)
    return render(request, 'main/devis_form.html', {'devis': d})


@login_required(login_url='/login/')
def devis_delete(request, devis_id):
    d = get_object_or_404(Devis, id=devis_id)
    if request.method == 'POST':
        d.delete()
        messages.success(request, 'Devis supprimé.')
    return redirect('devis_list')
