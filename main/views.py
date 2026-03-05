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
        if doc.rt2012_is_conform is True or doc.re2020_is_conform is True
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
    RT2012_FIELDS = [
        ('rt2012_bbio',         'Bbio', ''),
        ('rt2012_cep',          'Cep', 'kWh ep/m².an'),
        ('rt2012_tic',          'Tic', '°C'),
        ('rt2012_airtightness', 'Étanchéité', 'm³/h.m²'),
        ('rt2012_enr',          'ENR', ''),
    ]
    RE2020_FIELDS = [
        ('re2020_energy_efficiency', 'Cep,nr', 'kWh/m².an'),
        ('re2020_carbon_emissions',  'Ic énergie CO₂', 'kgCO2eq/m².an'),
        ('re2020_thermal_comfort',   'DH (confort été)', 'DH'),
    ]

    if request.method == 'POST':
        # Statut
        new_status = request.POST.get('status')
        old_status = document.status
        if new_status in dict(STATUS_CHOICES):
            document.status = new_status

        # Valeurs RT2012
        for field, _, _ in RT2012_FIELDS:
            val = request.POST.get(field, '').strip()
            if val:
                setattr(document, field, float(val))

        # Valeurs RE2020
        for field, _, _ in RE2020_FIELDS:
            val = request.POST.get(field, '').strip()
            if val:
                setattr(document, field, float(val))

        # Infos client
        document.client_name = request.POST.get('client_name', '').strip()
        document.client_email = request.POST.get('client_email', '').strip()
        document.admin_notes = request.POST.get('admin_notes', '').strip()

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
