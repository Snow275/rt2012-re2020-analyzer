from django.shortcuts import render, redirect, get_object_or_404
from django.http import HttpResponse, JsonResponse
from django.contrib import messages
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.template.loader import render_to_string
from django.core.mail import send_mail, EmailMultiAlternatives
from django.conf import settings
from django.conf import settings as django_settings
from django.views.decorators.csrf import csrf_exempt
from rest_framework.decorators import api_view
from rest_framework.response import Response
from rest_framework import status

from .models import Document, DocumentFile, Analysis, Devis, FactureEnergie
from .forms import DocumentForm, ContactForm
from .serializers import DocumentSerializer, AnalysisSerializer

import PyPDF2
import re
import threading
import base64


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

SITE_URL = "https://conformexpert.cc"


def _send_html_async(sujet, template_name, context, destinataire):
    if not destinataire:
        return
    def _send():
        try:
            import sendgrid
            from sendgrid.helpers.mail import Mail, To
            html = render_to_string(f'main/emails/{template_name}', context)
            sg = sendgrid.SendGridAPIClient(api_key=settings.SENDGRID_API_KEY)
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
        {
            'doc_id': f"{document.id:04d}",
            'doc_name': document.name,
            'client_name': document.client_name or '',

            'accepter_url': f"{SITE_URL}/devis/accepter/{devis.id}/",
            'refuser_url': f"{SITE_URL}/devis/refuser/{devis.id}/",

            'montant_ht': f"{montant_ht:.2f}",
            'tva': f"{tva:.2f}",
            'montant_ttc': f"{montant_ht + tva:.2f}",
            'norme': devis.norme if devis else 'RT2012 / RE2020',
            'notes': devis.notes if devis else ''
        },
        document.client_email,
    )

def accepter_devis(request, devis_id):

    devis = get_object_or_404(Devis, id=devis_id)

    # éviter double clic
    if devis.statut != "accepte":
        devis.statut = "accepte"
        devis.save()

        # si un dossier est lié → passer en analyse
        if devis.document:
            devis.document.status = "en_cours"
            devis.document.save()

        # notification admin
        _send_html_async(
            "Devis accepté",
            "email_notification_admin.html",
            {
                "client": devis.client_nom,
                "projet": devis.projet_nom,
                "montant": devis.montant,
                "reference": f"DEV-{devis.id:04d}",
            },
            "contact@conformexpert.cc"
        )

    return render(request, "main/devis_accepte.html", {
        "devis": devis
    })

def refuser_devis(request, devis_id):

    devis = get_object_or_404(Devis, id=devis_id)

    if devis.statut != "refuse":
        devis.statut = "refuse"
        devis.save()

        _send_html_async(
            "Devis refusé",
            "email_notification_admin.html",
            {
                "client": devis.client_nom,
                "projet": devis.projet_nom,
                "montant": devis.montant,
                "status": "refusé"
            },
            "contact@conformexpert.cc"
        )

    return render(request, "main/devis_refuse.html", {
        "devis": devis
    })

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


def parse_pdf_text(text, norme=None):
    """
    Extrait les valeurs thermiques du texte PDF via l'API Claude.
    Fallback sur regex si l'API est indisponible.
    """
    import json
    import os
    import urllib.request

    ANTHROPIC_API_KEY = os.environ.get('ANTHROPIC_API_KEY', '')

    if ANTHROPIC_API_KEY:
        try:
            prompt = f"""Tu es un expert en réglementation thermique. Voici le texte extrait d'un document thermique (rapport STD, DPE, notice, attestation RT/RE).

Extrais UNIQUEMENT les valeurs numériques suivantes si elles sont présentes dans le texte.
Réponds UNIQUEMENT en JSON valide, sans explication, sans markdown.

Valeurs à extraire :
- rt2012_bbio (Bbio)
- rt2012_cep (Cep)
- rt2012_tic (Tic)
- rt2012_airtightness (étanchéité à l'air / perméabilité)
- rt2012_enr (ENR)
- re2020_energy_efficiency (Cep,nr)
- re2020_thermal_comfort (DH degrés-heures)
- re2020_carbon_emissions (Ic énergie / émissions CO2)
- peb_espec (Espec)
- peb_ew (Ew)
- peb_u_mur (U mur)
- peb_u_toit (U toit)
- peb_u_plancher (U plancher)
- minergie_qh (Qh chaleur)
- minergie_qtot (Qtot)
- minergie_n50 (n50)
- sia380_qh (Qh SIA)
- cneb_ei (intensité énergétique)
- cneb_u_mur
- cneb_u_toit
- cneb_u_fenetre
- cneb_infiltration
- lenoz_ep (énergie primaire)
- lenoz_ew
- lenoz_u_mur
- lenoz_u_toit

Si une valeur n'est pas trouvée, ne l'inclus pas dans le JSON.
Exemple de réponse : {{"rt2012_bbio": 45.2, "rt2012_cep": 72.0}}

Texte du document :
{text[:8000]}"""

            payload = json.dumps({
                "model": "claude-sonnet-4-5",
                "max_tokens": 8192,
                "messages": [{"role": "user", "content": prompt}]
            }).encode('utf-8')

            req = urllib.request.Request(
                "https://api.anthropic.com/v1/messages",
                data=payload,
                headers={
                    "Content-Type": "application/json",
                    "x-api-key": ANTHROPIC_API_KEY,
                    "anthropic-version": "2023-06-01",
                },
                method="POST"
            )
            with urllib.request.urlopen(req, timeout=30) as resp:
                result = json.loads(resp.read().decode('utf-8'))
                raw = result['content'][0]['text'].strip()
                # Nettoyer éventuels backticks
                raw = raw.replace('```json', '').replace('```', '').strip()
                data = json.loads(raw)
                # S'assurer que toutes les valeurs sont des floats
                return {k: float(v) for k, v in data.items() if v is not None}

        except Exception as e:
            print(f"Erreur API Claude, fallback regex: {e}")

    # ── FALLBACK REGEX ─────────────────────────────────────
    data = {}
    t = text

    for pattern, key in [
        (r'Bbio\s*[=:]\s*([\d.,]+)',        'rt2012_bbio'),
        (r'Cep\s*[=:]\s*([\d.,]+)',         'rt2012_cep'),
        (r'Tic\s*[=:]\s*([\d.,]+)',         'rt2012_tic'),
        (r'[Ee]tanch[eé]it[eé]\s*[=:]\s*([\d.,]+)', 'rt2012_airtightness'),
        (r'ENR\s*[=:]\s*([\d.,]+)',         'rt2012_enr'),
        (r'Cep,?nr\s*[=:]\s*([\d.,]+)',     're2020_energy_efficiency'),
        (r'DH\s*[=:]\s*([\d.,]+)',          're2020_thermal_comfort'),
        (r'Ic.{0,10}[ée]nergie\s*[=:]\s*([\d.,]+)', 're2020_carbon_emissions'),
        (r'Espec\s*[=:]\s*([\d.,]+)',       'peb_espec'),
        (r'\bEw\b\s*[=:]\s*([\d.,]+)',    'peb_ew'),
        (r'U\s*mur\s*[=:]\s*([\d.,]+)',    'peb_u_mur'),
        (r'U\s*toit\s*[=:]\s*([\d.,]+)',   'peb_u_toit'),
        (r'U\s*plancher\s*[=:]\s*([\d.,]+)','peb_u_plancher'),
        (r'Qh\s*[=:]\s*([\d.,]+)',          'minergie_qh'),
        (r'Qtot\s*[=:]\s*([\d.,]+)',        'minergie_qtot'),
        (r'n50\s*[=:]\s*([\d.,]+)',         'minergie_n50'),
        (r'[Ii]ntensit[eé].{0,20}[=:]\s*([\d.,]+)', 'cneb_ei'),
        (r'U\s*fen[eê]tre\s*[=:]\s*([\d.,]+)',     'cneb_u_fenetre'),
        (r'[Ii]nfiltration\s*[=:]\s*([\d.,]+)',     'cneb_infiltration'),
        (r'[Ee]nergie\s+primaire\s*[=:]\s*([\d.,]+)', 'lenoz_ep'),
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

def analyse_pca(document):

    risques = []
    score = 100

    # année de construction
    if document.annee_construction and document.annee_construction < 1997:
        risques.append("Présence potentielle d’amiante (bâtiment construit avant 1997)")
        score -= 10

    # surface
    if document.surface_totale and document.surface_totale > 100000:
        risques.append("Surface du bâtiment atypique – vérification structure recommandée")
        score -= 5

    # nombre de logements
    if document.nombre_logements and document.nombre_logements > 500:
        risques.append("Bâtiment de grande capacité – contrôle technique approfondi recommandé")
        score -= 5

    return {
        "risques": risques,
        "score": score
    }
    
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
    # ── Pré-analyse énergétique ──
    docs_energie_recu = documents.filter(type_analyse="energie", status="recu")
    docs_energie_en_cours = documents.filter(type_analyse="energie", status="en_cours")
    docs_energie_termine = documents.filter(type_analyse="energie", status="termine")

    # ── PCA ──
    docs_pca_recu = documents.filter(type_analyse="pca", status="recu")
    docs_pca_en_cours = documents.filter(type_analyse="pca", status="en_cours")
    docs_pca_termine = documents.filter(type_analyse="pca", status="termine")

    # ── Analyse complète ──
    docs_complet_recu = documents.filter(type_analyse="complet", status="recu")
    docs_complet_en_cours = documents.filter(type_analyse="complet", status="en_cours")
    docs_complet_termine = documents.filter(type_analyse="complet", status="termine")
    energie_docs = documents.filter(type_analyse="energie")
    pca_docs = documents.filter(type_analyse="pca")
    complet_docs = documents.filter(type_analyse="complet")
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

    count_energie = energie_docs.count()
    count_pca = pca_docs.count()
    count_complet = complet_docs.count()

    context = {
        'documents': documents,
        'energie_docs': energie_docs,
        'pca_docs': pca_docs,
        'complet_docs': complet_docs,
        'total_projects': total_projects,
        'compliance_rate': compliance_rate,
        'pending_count': pending_count,
        'old_pending': old_pending,
        'recent_devis': recent_devis,
        'devis_en_attente': devis_en_attente,
        'docs_energie_recu': docs_energie_recu,
        'docs_energie_en_cours': docs_energie_en_cours,
        'docs_energie_termine': docs_energie_termine,

        'docs_pca_recu': docs_pca_recu,
        'docs_pca_en_cours': docs_pca_en_cours,
        'docs_pca_termine': docs_pca_termine,

        'docs_complet_recu': docs_complet_recu,
        'docs_complet_en_cours': docs_complet_en_cours,
        'docs_complet_termine': docs_complet_termine,

        'count_energie': count_energie,
        'count_pca': count_pca,
        'count_complet': count_complet,
    }
    return render(request, 'main/home.html', context)
    


def import_document(request):
    if request.method == "POST":
        data = request.POST.copy()

        type_analyse = data.get("type_analyse")

        # Si PCA → on supprime les champs énergie pour éviter la validation
        if type_analyse == "pca":
            data["climate_zone"] = ""
            data["norme"] = ""

        form = DocumentForm(data, request.FILES)

        if form.is_valid():
            document = form.save(commit=False)
            document.type_analyse = type_analyse
            document.save()

            # Multi upload
            fichiers = request.FILES.getlist("uploads")
            for f in fichiers:
                DocumentFile.objects.create(
                    document=document,
                    fichier=f,
                    nom=f.name,
                    taille=f.size,
                )
            # ── Extraction de texte (tous les fichiers uploadés) ───────────
            texte_complet = ""
            for doc_file in document.fichiers.all():
                try:
                    texte_complet += extract_text_from_pdf(doc_file.fichier.path) + "\n\n"
                except Exception:
                    pass

            # Fallback sur l'ancien champ upload si aucun fichier multi
            if not texte_complet and document.upload:
                try:
                    texte_complet = extract_text_from_pdf(document.upload.path)
                except Exception:
                    texte_complet = ""

            data = parse_pdf_text(texte_complet)
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
            "Notice ou étude thermique (RT2012, RE2020, PEB, Minergie, CNEB, LENOZ…)",
            "Plans architecturaux (PDF)",
            "Tout document technique lié à la conformité énergétique du bâtiment",
            "DPE ou équivalent si disponible",
        ],
        "steps": [
            "Accusé de réception sous 24h",
            "Confirmation de complétude du dossier",
            "Analyse documentaire complète",
            "Livraison du rapport IA + lien de suivi",
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

def mentions_legales(request):
    return render(request, 'main/mentions_legales.html')


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

    pca_seuils = [
        ("Âge max toiture", 30, "ans"),
        ("Âge max chauffage", 25, "ans"),
        ("Humidité mur max", 5, "%"),
        ("Année interdiction amiante", 1997, ""),
        ("Surface bâtiment min", 20, "m²"),
        ("Surface bâtiment max", 100000, "m²"),
        ("Nombre logements max", 1000, "")
    ]

    return render(request, 'main/settings.html', {
        'seuils_par_pays': seuils_par_pays,
        'pca_seuils': pca_seuils
    })


def update_re2020(request):
    if request.method == 'POST':
        messages.success(request, 'Paramètres RE2020 mis à jour.')
    else:
        messages.error(request, 'Méthode invalide.')
    return redirect('settings')


@csrf_exempt
def verifier_seuils(request):
    import json, os, urllib.request, urllib.error

    if not request.user.is_authenticated:
        return JsonResponse({'error': 'Session expirée — veuillez vous reconnecter'}, status=401)

    if request.method != 'POST':
        return JsonResponse({'error': 'Méthode invalide'}, status=405)

    norme = request.POST.get('norme', 'RE2020')
    ANTHROPIC_API_KEY = os.environ.get('ANTHROPIC_API_KEY', '')

    if not ANTHROPIC_API_KEY:
        return JsonResponse({'error': 'Clé API Anthropic manquante — ajoutez ANTHROPIC_API_KEY dans vos variables Railway'}, status=500)

    NORME_CONTEXTE = {
        'RT2012':   'la réglementation thermique RT 2012 française (arrêté du 26 octobre 2010)',
        'RE2020':   'la réglementation environnementale RE 2020 française (décret du 29 juillet 2021)',
        'PEB':      'la performance énergétique des bâtiments PEB en Belgique',
        'MINERGIE': 'le label Minergie en Suisse',
        'SIA380':   'la norme SIA 380/1 suisse',
        'CNEB2015': "le Code National de l'Énergie pour les Bâtiments CNEB 2015 au Canada",
        'CNEB2020': "le Code National de l'Énergie pour les Bâtiments CNEB 2020 au Canada",
        'LENOZ':    'le label LENOZ au Luxembourg',
    }

    VALEURS_ACTUELLES = {
        'RT2012':   {'Bbio max (maison)': 60, 'Bbio max (collectif)': 80, 'Cep max': 50, 'Tic max H2': 27, 'Étanchéité maison': 0.6, 'ENR min': 1.0},
        'RE2020':   {'Cep,nr max (maison)': 100, 'DH max H2': 1250, 'Ic énergie max': 160, 'Ic construction max': 640},
        'PEB':      {'Espec max': 100, 'U mur max': 0.24, 'U toit max': 0.20, 'U plancher max': 0.30},
        'MINERGIE': {'Qh max (maison)': 60, 'Qtot max': 38, 'n50 max': 0.6},
        'SIA380':   {'Qh max (maison)': 90},
        'CNEB2015': {'EI max (maison)': 170, 'U mur max': 0.24, 'U toit max': 0.18, 'U fenêtre max': 1.8, 'Infiltration max': 0.30},
        'CNEB2020': {'EI max (maison)': 150, 'U mur max': 0.21, 'U toit max': 0.16, 'U fenêtre max': 1.6, 'Infiltration max': 0.25},
        'LENOZ':    {'EP max (maison)': 90, 'Ew max': 100, 'U mur max': 0.22, 'U toit max': 0.17},
    }

    valeurs = VALEURS_ACTUELLES.get(norme, {})
    contexte = NORME_CONTEXTE.get(norme, norme)

    prompt = f"""Tu es un expert en réglementation thermique et énergétique des bâtiments.

Vérifie si les seuils suivants pour {contexte} sont toujours officiellement valides en {__import__('datetime').date.today().year}.

Valeurs actuellement dans notre système :
{json.dumps(valeurs, ensure_ascii=False, indent=2)}

Réponds UNIQUEMENT en JSON valide avec cette structure exacte, sans markdown ni explication :
{{
  "a_jour": true,
  "date_derniere_mise_a_jour": "mois et année",
  "modifications": [
    {{
      "critere": "nom du critère",
      "valeur_actuelle": 100,
      "valeur_officielle": 90,
      "commentaire": "explication courte"
    }}
  ],
  "resume": "phrase courte résumant le statut",
  "source": "texte officiel de référence"
}}

Si tout est à jour, "modifications" sera [] et "a_jour" sera true."""

    try:
        payload = json.dumps({
            "model": "claude-sonnet-4-5",
            "max_tokens": 1500,
            "messages": [{"role": "user", "content": prompt}]
        }).encode('utf-8')

        req = urllib.request.Request(
            "https://api.anthropic.com/v1/messages",
            data=payload,
            headers={
                "Content-Type": "application/json",
                "x-api-key": ANTHROPIC_API_KEY,
                "anthropic-version": "2023-06-01",
            },
            method="POST"
        )
        with urllib.request.urlopen(req, timeout=30) as resp:
            result = json.loads(resp.read().decode('utf-8'))
            raw = result['content'][0]['text'].strip().replace('```json','').replace('```','').strip()
            return JsonResponse({'success': True, 'norme': norme, 'resultat': json.loads(raw)})

    except urllib.error.HTTPError as e:
        body = e.read().decode('utf-8')
        print(f"ANTHROPIC API ERROR {e.code}: {body}")
        return JsonResponse({'error': f'API {e.code}: {body}'}, status=500)
    except Exception as e:
        print(f"VERIFIER_SEUILS ERROR: {str(e)}")
        return JsonResponse({'error': str(e)}, status=500)


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

        if "upload_openstudio" in request.POST:
            fichier = request.FILES.get("openstudio_file")

            if fichier:
                type_fichier = "openstudio_html"

                if fichier.name.endswith(".csv"):
                    type_fichier = "openstudio_csv"
                elif fichier.name.endswith(".sql"):
                    type_fichier = "openstudio_sql"

                DocumentFile.objects.create(
                    document=document,
                    fichier=fichier,
                    nom=fichier.name,
                    taille=fichier.size,
                    type_fichier=type_fichier
                )

                messages.success(request, "Rapport OpenStudio importé avec succès.")

            return redirect('edit_document', doc_id=doc_id)
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
    from reportlab.lib.units import cm, mm
    from reportlab.lib import colors
    from reportlab.platypus import (
        SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle,
        HRFlowable, PageBreak
    )
    from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT
    from reportlab.pdfgen import canvas as pdfcanvas
    from reportlab.platypus.flowables import Flowable
    from main.templatetags.conformity_tags import get_seuils, CRITERIA_GREATER_EQUAL
    from datetime import date

    PAGE_W, PAGE_H = A4  # 595.27 x 841.89 points
    ML = 2*cm; MR = 2*cm; MT = 2*cm; MB = 2.5*cm
    W = PAGE_W - ML - MR  # ~17cm

    # ── Couleurs ──
    NAVY   = colors.HexColor('#0C1929')
    NAVY2  = colors.HexColor('#0F2035')
    GOLD   = colors.HexColor('#C8A84B')
    GOLD_L = colors.HexColor('#F5EDD0')
    GREEN  = colors.HexColor('#1A9E2E')
    GREEN_L= colors.HexColor('#E8F8EE')
    RED    = colors.HexColor('#C62828')
    RED_L  = colors.HexColor('#FEF0F0')
    LGRAY  = colors.HexColor('#F8F8FC')
    MGRAY  = colors.HexColor('#E0E0E8')
    WHITE  = colors.white
    MUTED  = colors.HexColor('#888899')
    TEXT   = colors.HexColor('#1A1A2E')

    def st(name, **kw):
        d = dict(fontName='Helvetica', fontSize=9, textColor=TEXT, leading=14, spaceAfter=0)
        d.update(kw)
        return ParagraphStyle(name, **d)

    seuils     = get_seuils(document.building_type, document.climate_zone, document.pays, document.norme)
    is_conform = document.is_conform
    norme      = document.norme
    pays_map   = {'FR':'France','BE':'Belgique','CH':'Suisse','CA':'Canada','LU':'Luxembourg'}
    pays_label = pays_map.get(document.pays, document.pays)
    today_str  = date.today().strftime("%d/%m/%Y")

    if is_conform is True:
        verdict_txt = "Conforme"
        verdict_col = GREEN
        verdict_bg  = GREEN_L
    elif is_conform is False:
        verdict_txt = "Non Conforme"
        verdict_col = RED
        verdict_bg  = RED_L
    else:
        verdict_txt = "En cours d'analyse"
        verdict_col = MUTED
        verdict_bg  = LGRAY

    # ── Helpers styles ──
    def section_title(num, title):
        label = f"{num}.  {title.upper()}"
        return [
            HRFlowable(width=W, thickness=1.5, color=GOLD, spaceAfter=5, spaceBefore=10),
            Paragraph(label, st('sh', fontName='Helvetica-Bold', fontSize=8,
                                textColor=GOLD, characterSpacing=0.8, spaceAfter=8)),
        ]

    def info_table(rows):
        data = [[Paragraph(k, st('ik', fontSize=8, textColor=MUTED)),
                 Paragraph(v, st('iv', fontName='Helvetica-Bold', fontSize=9))]
                for k, v in rows]
        t = Table(data, colWidths=[4.5*cm, W - 4.5*cm])
        t.setStyle(TableStyle([
            ('BACKGROUND',    (0,0),(0,-1), LGRAY),
            ('TOPPADDING',    (0,0),(-1,-1), 5),
            ('BOTTOMPADDING', (0,0),(-1,-1), 5),
            ('LEFTPADDING',   (0,0),(-1,-1), 8),
            ('RIGHTPADDING',  (0,0),(-1,-1), 8),
            ('LINEBELOW',     (0,0),(-1,-2), 0.5, MGRAY),
            ('VALIGN',        (0,0),(-1,-1), 'MIDDLE'),
        ]))
        return t

    def criteria_section(title, rows_data):
        rows = [r for r in rows_data if r is not None]
        if not rows:
            return []
        header = [
            Paragraph("Critere", st('th', fontName='Helvetica-Bold', fontSize=8, textColor=WHITE)),
            Paragraph("Valeur",  st('th2', fontName='Helvetica-Bold', fontSize=8, textColor=WHITE, alignment=TA_CENTER)),
            Paragraph("Seuil",   st('th3', fontName='Helvetica-Bold', fontSize=8, textColor=WHITE, alignment=TA_CENTER)),
            Paragraph("Unite",   st('th4', fontName='Helvetica-Bold', fontSize=8, textColor=WHITE, alignment=TA_CENTER)),
            Paragraph("Resultat",st('th5', fontName='Helvetica-Bold', fontSize=8, textColor=WHITE, alignment=TA_CENTER)),
        ]
        data  = [header] + rows
        col_w = [7*cm, 2.2*cm, 2.2*cm, 2.3*cm, 3.3*cm]
        t = Table(data, colWidths=col_w, repeatRows=1)
        style = [
            ('BACKGROUND',    (0,0),(-1,0),  NAVY),
            ('TOPPADDING',    (0,0),(-1,-1), 6),
            ('BOTTOMPADDING', (0,0),(-1,-1), 6),
            ('LEFTPADDING',   (0,0),(-1,-1), 6),
            ('RIGHTPADDING',  (0,0),(-1,-1), 6),
            ('LINEBELOW',     (0,1),(-1,-1), 0.5, MGRAY),
            ('VALIGN',        (0,0),(-1,-1), 'MIDDLE'),
        ]
        for i in range(2, len(data), 2):
            style.append(('BACKGROUND', (0,i),(-1,i), LGRAY))
        t.setStyle(TableStyle(style))
        return [t, Spacer(1, 0.4*cm)]

    def criteria_row(label, value, key, unit=""):
        if value is None:
            return None
        limit  = seuils.get(key, "—")
        sign   = ">=" if key in CRITERIA_GREATER_EQUAL else "<="
        if isinstance(limit, (int,float)):
            ok = value >= limit if key in CRITERIA_GREATER_EQUAL else value <= limit
        else:
            ok = False
        res_style = st('res', fontName='Helvetica-Bold', fontSize=8,
                       textColor=GREEN if ok else RED, alignment=TA_CENTER)
        return [
            Paragraph(label, st('cl', fontSize=8.5)),
            Paragraph(f"<b>{value}</b>", st('cv', fontName='Helvetica-Bold', fontSize=9, alignment=TA_CENTER)),
            Paragraph(f"{sign} {limit}", st('cs', fontSize=8, textColor=MUTED, alignment=TA_CENTER)),
            Paragraph(unit, st('cu', fontSize=8, textColor=MUTED, alignment=TA_CENTER)),
            Paragraph("Conforme" if ok else "Non conforme", res_style),
        ]

    def reco_block(prefix, title, text, bg, left_color):
        full_title = f"<b>{prefix}  {title}</b>"
        data = [
            [Paragraph(full_title, st('rbt', fontName='Helvetica-Bold', fontSize=9, textColor=TEXT, spaceAfter=3))],
            [Paragraph(text, st('rbd', fontSize=8.5, textColor=colors.HexColor('#444455'), leading=13))],
        ]
        t = Table(data, colWidths=[W])
        t.setStyle(TableStyle([
            ('BACKGROUND',    (0,0),(-1,-1), bg),
            ('LINEBEFORE',    (0,0),(0,-1),  3, left_color),
            ('TOPPADDING',    (0,0),(-1,-1), 8),
            ('BOTTOMPADDING', (0,0),(-1,-1), 8),
            ('LEFTPADDING',   (0,0),(-1,-1), 12),
            ('RIGHTPADDING',  (0,0),(-1,-1), 12),
        ]))
        return [t, Spacer(1, 0.25*cm)]

    # ═══════════════════════════════════════════════════
    # PAGE 1 — COUVERTURE (canvas manuel via onFirstPage)
    # ═══════════════════════════════════════════════════

    def draw_cover(c, doc_obj):
        c.saveState()
        # Fond navy pleine page
        c.setFillColor(NAVY)
        c.rect(0, 0, PAGE_W, PAGE_H, fill=1, stroke=0)

        # Accent coin haut droit
        c.setFillColor(colors.HexColor('#C8A84B11'))
        c.circle(PAGE_W, PAGE_H, 180, fill=1, stroke=0)

        # Accent coin bas gauche
        c.setFillColor(colors.HexColor('#C8A84B0A'))
        c.circle(0, 0, 130, fill=1, stroke=0)

        # Logo
        c.setFont('Helvetica-Bold', 22)
        c.setFillColor(WHITE)
        c.drawString(ML, PAGE_H - 3.5*cm, "Conform")
        c.setFillColor(GOLD)
        lw = c.stringWidth("Conform", 'Helvetica-Bold', 22)
        c.drawString(ML + lw, PAGE_H - 3.5*cm, "Expert")

        # Eyebrow
        c.setFont('Helvetica-Bold', 7.5)
        c.setFillColor(GOLD)
        c.drawString(ML, PAGE_H - 5*cm, "RAPPORT D'ANALYSE DE CONFORMITE THERMIQUE")

        # Ligne décorative sous eyebrow
        c.setStrokeColor(GOLD)
        c.setLineWidth(1)
        c.line(ML, PAGE_H - 5.3*cm, ML + 6*cm, PAGE_H - 5.3*cm)

        # Titre projet
        title = document.name
        c.setFont('Helvetica-Bold', 24)
        c.setFillColor(WHITE)
        # Découper si trop long
        max_w = PAGE_W - ML - MR - 1*cm
        while c.stringWidth(title, 'Helvetica-Bold', 24) > max_w and len(title) > 10:
            title = title[:-1]
        if title != document.name:
            title = title[:-3] + "..."
        c.drawString(ML, PAGE_H - 7*cm, title)

        # Sous-titre
        c.setFont('Helvetica', 11)
        c.setFillColor(colors.HexColor('#AAAACC'))
        subtitle = f"{document.get_building_type_display()}  ·  {norme}  ·  {pays_label}"
        c.drawString(ML, PAGE_H - 8.2*cm, subtitle)

        # Verdict box
        v_y   = PAGE_H - 10.5*cm
        v_x   = ML
        v_w   = 9*cm
        v_h   = 1.5*cm
        # Fond
        c.setFillColor(verdict_bg)
        c.roundRect(v_x, v_y, v_w, v_h, 20, fill=1, stroke=0)
        # Bordure
        c.setStrokeColor(verdict_col)
        c.setLineWidth(1.5)
        c.roundRect(v_x, v_y, v_w, v_h, 20, fill=0, stroke=1)
        # Texte
        c.setFont('Helvetica-Bold', 12)
        c.setFillColor(verdict_col)
        tw = c.stringWidth(verdict_txt, 'Helvetica-Bold', 12)
        c.drawString(v_x + (v_w - tw)/2, v_y + 0.45*cm, verdict_txt)

        # Ligne séparatrice dorée
        c.setStrokeColor(colors.HexColor('#C8A84B44'))
        c.setLineWidth(0.5)
        c.line(ML, PAGE_H - 12.5*cm, PAGE_W - MR, PAGE_H - 12.5*cm)

        # Grille méta
        meta = [
            ("REFERENCE",      f"DOC-{document.id:04d}"),
            ("DATE DU RAPPORT", today_str),
            ("CLIENT",         document.client_name or "—"),
            ("NORME",          norme),
            ("TYPE DE BATIMENT", document.get_building_type_display()),
            ("PAYS",           pays_label),
        ]
        cols = 3
        col_w2 = (PAGE_W - ML - MR) / cols
        for i, (label, val) in enumerate(meta):
            col = i % cols
            row = i // cols
            x = ML + col * col_w2
            y = PAGE_H - 13.5*cm - row * 1.8*cm
            c.setFont('Helvetica', 7)
            c.setFillColor(MUTED)
            c.drawString(x, y, label)
            c.setFont('Helvetica-Bold', 10)
            c.setFillColor(WHITE)
            c.drawString(x, y - 0.5*cm, val)

        # Footer couverture
        c.setFillColor(colors.HexColor('#C8A84B33'))
        c.setStrokeColor(colors.HexColor('#00000000'))
        c.rect(0, 0, PAGE_W, 1.8*cm, fill=1, stroke=0)
        c.setFont('Helvetica', 8)
        c.setFillColor(colors.HexColor('#666677'))
        c.drawString(ML, 0.65*cm, "ConformExpert  ·  Analyse documentaire independante")
        c.setFillColor(GOLD)
        txt_r = "Confidentiel  ·  Usage interne"
        tw2 = c.stringWidth(txt_r, 'Helvetica', 8)
        c.drawString(PAGE_W - MR - tw2, 0.65*cm, txt_r)

        c.restoreState()

    def draw_page(c, doc_obj):
        """Footer sur les pages intérieures."""
        c.saveState()
        c.setStrokeColor(MGRAY)
        c.setLineWidth(0.5)
        c.line(ML, MB - 0.5*cm, PAGE_W - MR, MB - 0.5*cm)
        c.setFont('Helvetica', 7.5)
        c.setFillColor(MUTED)
        c.drawString(ML, MB - 1*cm, f"ConformExpert  ·  Analyse independante {norme}  ·  {pays_label}")
        page_num = str(doc_obj.page)
        tw = c.stringWidth(f"Page {page_num}", 'Helvetica', 7.5)
        c.drawString(PAGE_W - MR - tw, MB - 1*cm, f"Page {page_num}")
        c.restoreState()

    # ═══════════════════════════════════════════════════
    # STORY (pages 2+)
    # ═══════════════════════════════════════════════════
    story = []

    # Page blanche qui sert de couverture (dessinée via onFirstPage)
    story.append(Spacer(1, PAGE_H - MT - MB))
    story.append(PageBreak())

    # ── PAGE 2 : SOMMAIRE ──
    story += section_title("", "Sommaire")
    story.append(Paragraph(f"Rapport d'analyse — {document.name}",
                           st('ts', fontSize=8.5, textColor=MUTED, spaceAfter=12)))

    toc_items = [
        ("1.  Resume executif & verdict global", "3"),
        ("2.  Informations du dossier",           "3"),
        (f"3.  Analyse {norme} — Criteres de conformite", "4"),
        ("4.  Recommandations & points d'attention", "5"),
    ]
    if document.admin_notes:
        toc_items.append(("5.  Notes & observations de l'expert", "5"))
    toc_items.append(("6.  Mentions legales & disclaimer", "6"))

    for label, pg in toc_items:
        row = Table([[
            Paragraph(label, st('tl', fontSize=10)),
            Paragraph(pg, st('tp', fontName='Helvetica-Bold', fontSize=9,
                             textColor=GOLD, alignment=TA_RIGHT)),
        ]], colWidths=[W - 1.5*cm, 1.5*cm])
        row.setStyle(TableStyle([
            ('TOPPADDING',    (0,0),(-1,-1), 8),
            ('BOTTOMPADDING', (0,0),(-1,-1), 8),
            ('LEFTPADDING',   (0,0),(-1,-1), 0),
            ('RIGHTPADDING',  (0,0),(-1,-1), 0),
            ('LINEBELOW',     (0,0),(-1,-1), 0.5, MGRAY),
        ]))
        story.append(row)

    story.append(PageBreak())

    # ── PAGE 3 : RÉSUMÉ + INFOS ──
    story += section_title("1", "Resume executif & verdict global")

    # Verdict banner
    vb_data = [[
        Paragraph(f"VERDICT  —  {norme}",
                  st('vbl', fontName='Helvetica-Bold', fontSize=8, textColor=GOLD,
                     characterSpacing=0.8, spaceAfter=4)),
        Paragraph(verdict_txt,
                  st('vbv', fontName='Helvetica-Bold', fontSize=16,
                     textColor=verdict_col, alignment=TA_RIGHT)),
    ]]
    vb = Table(vb_data, colWidths=[W*0.55, W*0.45])
    vb.setStyle(TableStyle([
        ('BACKGROUND',    (0,0),(-1,-1), NAVY),
        ('TOPPADDING',    (0,0),(-1,-1), 14),
        ('BOTTOMPADDING', (0,0),(-1,-1), 14),
        ('LEFTPADDING',   (0,0),(-1,-1), 16),
        ('RIGHTPADDING',  (0,0),(-1,-1), 16),
        ('VALIGN',        (0,0),(-1,-1), 'MIDDLE'),
    ]))
    story.append(vb)
    story.append(Spacer(1, 0.6*cm))

    story += section_title("2", "Informations du dossier")
    rows_info = [
        ("Reference",        f"DOC-{document.id:04d}"),
        ("Norme analysee",   norme),
        ("Pays",             pays_label),
        ("Type de batiment", document.get_building_type_display()),
        ("Zone climatique",  f"Zone {document.climate_zone}" if document.climate_zone else "—"),
        ("Date de depot",    document.upload_date.strftime("%d/%m/%Y")),
        ("Date du rapport",  today_str),
        ("Client",           document.client_name or "—"),
        ("Email client",     document.client_email or "—"),
    ]
    story.append(info_table(rows_info))
    story.append(PageBreak())

    # ── PAGE 4 : CRITÈRES ──
    story += section_title("3", f"{norme} — Criteres de conformite")

    if norme == 'RT2012':
        story += criteria_section("RT2012", [
            criteria_row("Bbio — Besoins bioclimatiques",          document.rt2012_bbio,         "rt2012_bbio"),
            criteria_row("Cep — Consommation energie primaire",    document.rt2012_cep,           "rt2012_cep",  "kWh ep/m2.an"),
            criteria_row("Tic — Temperature interieure conv.",     document.rt2012_tic,           "rt2012_tic",  "degC"),
            criteria_row("Etancheite a l'air",                     document.rt2012_airtightness,  "rt2012_airtightness", "m3/h.m2"),
            criteria_row("ENR — Energies renouvelables",           document.rt2012_enr,           "rt2012_enr"),
        ])
    elif norme == 'RE2020':
        story += criteria_section("RE2020", [
            criteria_row("Cep,nr — Energie non renouvelable",      document.re2020_energy_efficiency, "re2020_energy_efficiency", "kWh/m2.an"),
            criteria_row("Ic energie — Emissions CO2 exploitation",document.re2020_carbon_emissions,  "re2020_carbon_emissions",  "kgCO2/m2.an"),
            criteria_row("DH — Degres-heures (confort ete)",       document.re2020_thermal_comfort,   "re2020_thermal_comfort",   "DH"),
        ])
    elif norme == 'PEB':
        story += criteria_section("PEB", [
            criteria_row("Espec — Energie specifique",             document.peb_espec,      "peb_espec",      "kWh/m2.an"),
            criteria_row("Ew — Indicateur global de performance",  document.peb_ew,         "peb_ew"),
            criteria_row("U mur",                                  document.peb_u_mur,      "peb_u_mur",      "W/m2.K"),
            criteria_row("U toit",                                 document.peb_u_toit,     "peb_u_toit",     "W/m2.K"),
            criteria_row("U plancher",                             document.peb_u_plancher, "peb_u_plancher", "W/m2.K"),
        ])
    elif norme == 'MINERGIE':
        story += criteria_section("MINERGIE", [
            criteria_row("Qh — Chaleur de chauffage annuelle",     document.minergie_qh,   "minergie_qh",   "kWh/m2.an"),
            criteria_row("Qtot — Energie totale ponderee",         document.minergie_qtot, "minergie_qtot", "kWh/m2.an"),
            criteria_row("n50 — Taux de renouvellement d'air",     document.minergie_n50,  "minergie_n50",  "h-1"),
        ])
    elif norme == 'SIA380':
        story += criteria_section("SIA380", [
            criteria_row("Qh — Chaleur de chauffage (SIA 380/1)", document.sia380_qh, "sia380_qh", "kWh/m2.an"),
        ])
    elif norme in ('CNEB2015', 'CNEB2020'):
        story += criteria_section(norme, [
            criteria_row("Intensite energetique",                  document.cneb_ei,           "cneb_ei",           "kWh/m2.an"),
            criteria_row("U mur — Valeur thermique enveloppe",     document.cneb_u_mur,        "cneb_u_mur",        "W/m2.K"),
            criteria_row("U toit — Valeur thermique toiture",      document.cneb_u_toit,       "cneb_u_toit",       "W/m2.K"),
            criteria_row("U fenetre — Performance des vitrages",   document.cneb_u_fenetre,    "cneb_u_fenetre",    "W/m2.K"),
            criteria_row("Infiltration — Etancheite a l'air",      document.cneb_infiltration, "cneb_infiltration", "L/s.m2"),
        ])
    elif norme == 'LENOZ':
        story += criteria_section("LENOZ", [
            criteria_row("Energie primaire",                       document.lenoz_ep,     "lenoz_ep",     "kWh/m2.an"),
            criteria_row("Ew — Indicateur de performance",         document.lenoz_ew,     "lenoz_ew"),
            criteria_row("U mur",                                  document.lenoz_u_mur,  "lenoz_u_mur",  "W/m2.K"),
            criteria_row("U toit",                                 document.lenoz_u_toit, "lenoz_u_toit", "W/m2.K"),
        ])

    story.append(PageBreak())

    # ── PAGE 5 : RECOMMANDATIONS ──
    story += section_title("4", "Recommandations & points d'attention")

    if is_conform is True:
        story += reco_block(">>", f"Dossier conforme aux exigences {norme}",
                            "L'ensemble des criteres analyses respecte les seuils reglementaires en vigueur. Aucune action corrective n'est requise pour l'obtention de la conformite.",
                            GREEN_L, GREEN)
    elif is_conform is None:
        story += reco_block("--", "Analyse en cours",
                            "Les donnees necessaires a l'evaluation complete n'ont pas encore ete renseignees. Les recommandations seront disponibles une fois l'analyse finalisee.",
                            LGRAY, MUTED)

    # Recos détaillées selon norme
    if norme == 'RT2012':
        if document.rt2012_bbio and document.rt2012_bbio > seuils.get('rt2012_bbio', 9999):
            story += reco_block("[!]", "Bbio — Besoins bioclimatiques non conformes",
                                "Ameliorer l'isolation de l'enveloppe, optimiser l'orientation et les surfaces vitrees, renforcer la compacite du batiment.",
                                RED_L, RED)
        if document.rt2012_cep and document.rt2012_cep > seuils.get('rt2012_cep', 9999):
            story += reco_block("[!]", "Cep — Consommation energetique non conforme",
                                "Optimiser les systemes de chauffage, installer des equipements haute efficacite, integrer des energies renouvelables.",
                                RED_L, RED)
        if document.rt2012_tic and document.rt2012_tic > seuils.get('rt2012_tic', 9999):
            story += reco_block("[~]", "Tic — Temperature interieure conventionnelle elevee",
                                "Renforcer la protection solaire, ameliorer l'inertie thermique, prevoir une ventilation nocturne efficace.",
                                colors.HexColor('#FFFBF0'), GOLD)
        if document.rt2012_airtightness and document.rt2012_airtightness > seuils.get('rt2012_airtightness', 9999):
            story += reco_block("[!]", "Etancheite a l'air insuffisante",
                                "Revoir les jonctions et points singuliers de l'enveloppe, traiter les passages de reseaux, realiser un test d'infiltrometrie.",
                                RED_L, RED)
    elif norme == 'RE2020':
        if document.re2020_energy_efficiency and document.re2020_energy_efficiency > seuils.get('re2020_energy_efficiency', 9999):
            story += reco_block("[!]", "Cep,nr — Energie non renouvelable excessive",
                                "Privilegier des energies decarbonees (PAC, solaire thermique), ameliorer l'isolation et reduire les consommations auxiliaires.",
                                RED_L, RED)
        if document.re2020_carbon_emissions and document.re2020_carbon_emissions > seuils.get('re2020_carbon_emissions', 9999):
            story += reco_block("[!]", "Ic energie — Emissions carbone non conformes",
                                "Basculer vers des energies renouvelables, remplacer les systemes a combustibles fossiles, optimiser la consommation globale.",
                                RED_L, RED)
        if document.re2020_thermal_comfort and document.re2020_thermal_comfort > seuils.get('re2020_thermal_comfort', 9999):
            story += reco_block("[~]", "DH — Confort d'ete insuffisant",
                                "Installer des brise-soleils, augmenter l'inertie thermique, prevoir une ventilation nocturne.",
                                colors.HexColor('#FFFBF0'), GOLD)
    elif norme == 'PEB':
        if document.peb_espec and document.peb_espec > seuils.get('peb_espec', 9999):
            story += reco_block("[!]", "Espec — Energie specifique non conforme (PEB)",
                                "Ameliorer l'isolation globale, optimiser les systemes de chauffage et ventilation, recourir aux energies renouvelables.",
                                RED_L, RED)
        if document.peb_u_mur and document.peb_u_mur > seuils.get('peb_u_mur', 9999):
            story += reco_block("[!]", "U mur — Isolation des parois insuffisante",
                                "Renforcer l'isolation des murs par l'interieur ou l'exterieur pour atteindre le coefficient U requis par la reglementation PEB.",
                                RED_L, RED)
    elif norme == 'MINERGIE':
        if document.minergie_qh and document.minergie_qh > seuils.get('minergie_qh', 9999):
            story += reco_block("[!]", "Qh — Besoins de chaleur trop eleves (Minergie)",
                                "Ameliorer l'isolation de l'enveloppe, optimiser les vitrages et reduire les ponts thermiques.",
                                RED_L, RED)
        if document.minergie_n50 and document.minergie_n50 > seuils.get('minergie_n50', 9999):
            story += reco_block("[!]", "n50 — Etancheite a l'air insuffisante (Minergie)",
                                "Traiter les points singuliers, mettre en place une membrane d'etancheite continue.",
                                RED_L, RED)
    elif norme in ('CNEB2015', 'CNEB2020'):
        if document.cneb_ei and document.cneb_ei > seuils.get('cneb_ei', 9999):
            story += reco_block("[!]", f"Intensite energetique non conforme ({norme})",
                                "Reduire les besoins en chauffage et climatisation, ameliorer l'enveloppe thermique, integrer des systemes a haute efficacite.",
                                RED_L, RED)
    elif norme == 'LENOZ':
        if document.lenoz_ep and document.lenoz_ep > seuils.get('lenoz_ep', 9999):
            story += reco_block("[!]", "Energie primaire non conforme (LENOZ)",
                                "Optimiser les systemes energetiques, integrer des sources renouvelables et ameliorer l'enveloppe thermique.",
                                RED_L, RED)

    # Notes admin
    if document.admin_notes:
        story += section_title("5", "Notes & observations de l'expert")
        notes_t = Table([[
            Paragraph(document.admin_notes.replace('\n','<br/>'),
                      st('nt', fontSize=9, leading=14))
        ]], colWidths=[W])
        notes_t.setStyle(TableStyle([
            ('BACKGROUND',    (0,0),(-1,-1), LGRAY),
            ('LINEBEFORE',    (0,0),(0,-1),  3, GOLD),
            ('TOPPADDING',    (0,0),(-1,-1), 10),
            ('BOTTOMPADDING', (0,0),(-1,-1), 10),
            ('LEFTPADDING',   (0,0),(-1,-1), 12),
            ('RIGHTPADDING',  (0,0),(-1,-1), 12),
        ]))
        story.append(notes_t)

    story.append(PageBreak())

    # ── PAGE 6 : MENTIONS LÉGALES ──
    story += section_title("6", "Mentions legales & disclaimer")

    disc_items = [
        ("Nature du rapport",
         "Ce rapport est etabli sur la base des documents fournis par le client et constitue une analyse documentaire independante. Il ne se substitue pas a une attestation officielle de conformite delivree par un organisme accredite."),
        ("Responsabilite",
         "ConformExpert s'engage a fournir une analyse rigoureuse et objective des documents transmis. La conformite finale du batiment releve de la responsabilite du maitre d'ouvrage et des professionnels en charge de la construction."),
        ("Confidentialite",
         "Ce document est strictement confidentiel et destine exclusivement au client mentionne en page de couverture. Toute reproduction ou diffusion sans autorisation ecrite de ConformExpert est interdite."),
        ("Reglementations",
         "RT2012 : Arrete du 26 octobre 2010  |  RE2020 : Decret n 2021-1004 du 29 juillet 2021  |  PEB : Directive europeenne 2010/31/UE  |  Minergie / SIA380 : Normes SIA Suisse  |  CNEB : Code national de l'energie pour les batiments (Canada)  |  LENOZ : Reglement grand-ducal du 23 juillet 2016 (Luxembourg)"),
        ("Contact",
         "ConformExpert  ·  contact@conformexpert.fr  ·  Delai garanti 15 jours ouvres"),
    ]
    for k, v in disc_items:
        disc_t = Table([[
            Paragraph(k, st('dk', fontName='Helvetica-Bold', fontSize=9, textColor=TEXT)),
            Paragraph(v, st('dv', fontSize=8.5, textColor=colors.HexColor('#444455'), leading=13)),
        ]], colWidths=[4*cm, W - 4*cm])
        disc_t.setStyle(TableStyle([
            ('BACKGROUND',    (0,0),(-1,-1), LGRAY),
            ('TOPPADDING',    (0,0),(-1,-1), 8),
            ('BOTTOMPADDING', (0,0),(-1,-1), 8),
            ('LEFTPADDING',   (0,0),(-1,-1), 10),
            ('RIGHTPADDING',  (0,0),(-1,-1), 10),
            ('LINEBELOW',     (0,0),(-1,-1), 0.5, MGRAY),
            ('VALIGN',        (0,0),(-1,-1), 'TOP'),
        ]))
        story.append(disc_t)

    # ── BUILD ──
    buffer = BytesIO()
    doc_pdf = SimpleDocTemplate(
        buffer, pagesize=A4,
        leftMargin=ML, rightMargin=MR,
        topMargin=MT, bottomMargin=MB,
        title=f"Rapport ConformExpert - {document.name}"
    )
    doc_pdf.build(story, onFirstPage=draw_cover, onLaterPages=draw_page)

    buffer.seek(0)
    response = HttpResponse(buffer.read(), content_type='application/pdf')
    safe_name = document.name.replace(' ','_').replace('/','_')
    response['Content-Disposition'] = f'inline; filename="rapport_{safe_name}.pdf"'
    return response

# ──────────────────────────────────────────────────────────────────────────────
# VUE À AJOUTER DANS views.py
# Endpoint AJAX : POST /dossier/<doc_id>/rapport-ia/
# ──────────────────────────────────────────────────────────────────────────────

@csrf_exempt
def generer_rapport_ia(request, doc_id):
    """
    Endpoint AJAX rapport IA.
    - GET  : retourne le rapport déjà sauvegardé (si existant)
    - POST : génère via Claude, sauvegarde en BDD, retourne le JSON
    - POST ?force=1 : force la régénération même si déjà sauvegardé
    """
    import json, os, base64, urllib.request, urllib.error

    document = get_object_or_404(Document, id=doc_id)

    # ── GET ou POST sans force → retourner le rapport sauvegardé si présent ──
    force = request.GET.get('force') == '1'
    if not force and document.rapport_ia_json:
        try:
            return JsonResponse({'success': True, 'rapport': json.loads(document.rapport_ia_json), 'cached': True})
        except Exception:
            pass  # JSON corrompu → on régénère

    if request.method not in ('POST', 'GET'):
        return JsonResponse({'error': 'Méthode invalide'}, status=405)

    ANTHROPIC_API_KEY = os.environ.get('ANTHROPIC_API_KEY', '')
    if not ANTHROPIC_API_KEY:
        return JsonResponse({'error': 'Clé API Anthropic manquante (ANTHROPIC_API_KEY)'}, status=500)

    # ── 1. Lire les fichiers multi-upload ─────────────────────────────────────
    pdf_b64 = None
    pdf_b64_list = []

    for doc_file in document.fichiers.all()[:3]:

        file_path = doc_file.fichier.path

        # Vérifie que le fichier est bien un PDF
        if not file_path.lower().endswith(".pdf"):
            print("Fichier ignoré (pas un PDF):", file_path)
            continue

        try:
            with open(file_path, "rb") as f:
                pdf_bytes = f.read()

            # Vérifie que le fichier commence bien par %PDF
            if not pdf_bytes.startswith(b"%PDF"):
                print("Fichier invalide (pas un vrai PDF):", file_path)
                continue

            pdf_b64 = base64.b64encode(pdf_bytes).decode("utf-8")
            pdf_b64_list.append(pdf_b64)

        except Exception as e:
            print("Erreur lecture PDF:", e)
    

    # Fallback sur l'ancien champ upload
    if not pdf_b64_list:
        try:
            if document.upload and document.upload.name:
                with open(document.upload.path, "rb") as f:
                    pdf_bytes = f.read()
                    pdf_b64 = base64.b64encode(pdf_bytes).decode("utf-8")
                    pdf_b64_list.append(pdf_b64)
        except Exception as e:
            print(f"PDF upload indisponible : {e}")

    pdf_b64 = pdf_b64_list[0] if pdf_b64_list else None

    # ── 2. Contexte commun ────────────────────────────────────────────────────
    type_analyse = getattr(document, 'type_analyse', 'energie') or 'energie'
    norme = document.norme
    pays_map = {'FR': 'France', 'BE': 'Belgique', 'CH': 'Suisse', 'CA': 'Canada', 'LU': 'Luxembourg'}
    pays_label = pays_map.get(document.pays, document.pays)
    batiment_label = document.get_building_type_display()
    zone = document.climate_zone or 'H2'
    ref = f"DOC-{document.id:04d}"
    surface = getattr(document, 'surface_totale', None)
    annee = getattr(document, 'annee_construction', None)
    logements = getattr(document, 'nombre_logements', None)

    # ── Seuils PCA internes ─────────────────────────────────────
    PCA_SEUILS = {
        "age_toiture_max": 30,
        "age_chauffage_max": 25,
        "humidite_mur_max": 5,
        "annee_amiante": 1997,
        "surface_max": 100000,
        "logements_max": 1000
    }

    pca_seuils_str = f"""
    Seuils techniques internes (PCA) :
    - Âge max toiture recommandé : {PCA_SEUILS['age_toiture_max']} ans
    - Âge max système chauffage : {PCA_SEUILS['age_chauffage_max']} ans
    - Humidité mur tolérée : {PCA_SEUILS['humidite_mur_max']} %
    - Risque amiante si bâtiment construit avant : {PCA_SEUILS['annee_amiante']}
    - Surface bâtiment considérée atypique au-delà de : {PCA_SEUILS['surface_max']} m²
    - Nombre logements élevé au-delà de : {PCA_SEUILS['logements_max']}
    """

    infos_batiment = f"""- Type : {batiment_label}
- Pays / Zone : {pays_label} — Zone climatique {zone}
{"- Surface totale : " + str(surface) + " m²" if surface else ""}
{"- Année de construction : " + str(annee) if annee else ""}
{"- Nombre de logements : " + str(logements) if logements else ""}"""

    SEUILS_LABELS = {
        'RT2012': "Bbio ≤ 60 | Cep ≤ 50 kWh ep/m².an | Tic ≤ 27°C | Étanchéité ≤ 0,6 m³/h.m²",
        'RE2020': "Cep,nr ≤ 100 kWh/m².an | Ic énergie ≤ 160 kgCO2/m².an | DH ≤ 1250 (zone H2)",
        'PEB': "Espec ≤ 100 kWh/m².an | U mur ≤ 0,24 | U toit ≤ 0,20 | U plancher ≤ 0,30 W/m².K",
        'MINERGIE': "Qh ≤ 60 kWh/m².an | Qtot ≤ 38 kWh/m².an | n50 ≤ 0,6 h⁻¹",
        'SIA380': "Qh ≤ 90 kWh/m².an selon SIA 380/1",
        'CNEB2015': "EI ≤ 170 kWh/m².an | U mur ≤ 0,24 | U toit ≤ 0,18 | U fenêtre ≤ 1,8 W/m².K",
        'CNEB2020': "EI ≤ 150 kWh/m².an | U mur ≤ 0,21 | U toit ≤ 0,16 | U fenêtre ≤ 1,6 W/m².K",
        'LENOZ': "EP ≤ 90 kWh/m².an | Ew ≤ 100 | U mur ≤ 0,22 | U toit ≤ 0,17 W/m².K",
    }

    champs_norme = {
        'RT2012': [
            ('rt2012_bbio', 'Bbio', ''), ('rt2012_cep', 'Cep', 'kWh ep/m².an'),
            ('rt2012_tic', 'Tic', '°C'), ('rt2012_airtightness', 'Étanchéité', 'm³/h.m²'),
            ('rt2012_enr', 'ENR', ''),
        ],
        'RE2020': [
            ('re2020_energy_efficiency', 'Cep,nr', 'kWh/m².an'),
            ('re2020_carbon_emissions', 'Ic énergie CO₂', 'kgCO2eq/m².an'),
            ('re2020_thermal_comfort', 'DH (confort été)', 'DH'),
        ],
        'PEB': [
            ('peb_espec', 'Espec', 'kWh/m².an'), ('peb_ew', 'Ew', ''),
            ('peb_u_mur', 'U mur', 'W/m².K'), ('peb_u_toit', 'U toit', 'W/m².K'),
            ('peb_u_plancher', 'U plancher', 'W/m².K'),
        ],
        'MINERGIE': [
            ('minergie_qh', 'Qh', 'kWh/m².an'), ('minergie_qtot', 'Qtot', 'kWh/m².an'),
            ('minergie_n50', 'n50', 'h⁻¹'),
        ],
        'SIA380': [('sia380_qh', 'Qh', 'kWh/m².an')],
        'CNEB2015': [
            ('cneb_ei', 'Intensité énergétique', 'kWh/m².an'),
            ('cneb_u_mur', 'U mur', 'W/m².K'), ('cneb_u_toit', 'U toit', 'W/m².K'),
            ('cneb_u_fenetre', 'U fenêtre', 'W/m².K'), ('cneb_infiltration', 'Infiltration', 'L/s.m²'),
        ],
        'CNEB2020': [
            ('cneb_ei', 'Intensité énergétique', 'kWh/m².an'),
            ('cneb_u_mur', 'U mur', 'W/m².K'), ('cneb_u_toit', 'U toit', 'W/m².K'),
            ('cneb_u_fenetre', 'U fenêtre', 'W/m².K'), ('cneb_infiltration', 'Infiltration', 'L/s.m²'),
        ],
        'LENOZ': [
            ('lenoz_ep', 'Énergie primaire', 'kWh/m².an'), ('lenoz_ew', 'Ew', ''),
            ('lenoz_u_mur', 'U mur', 'W/m².K'), ('lenoz_u_toit', 'U toit', 'W/m².K'),
        ],
    }

    valeurs_connues = {}
    for field, label, unit in champs_norme.get(norme, []):
        val = getattr(document, field, None)
        if val is not None:
            valeurs_connues[label] = f"{val} {unit}".strip()
    valeurs_str = '\n'.join([f"  - {k} : {v}" for k, v in valeurs_connues.items()]) or "  (aucune valeur encore saisie)"

    source_donnees = f"{len(pdf_b64_list)} fichier(s) PDF joint(s) + les valeurs extraites ci-dessous" if pdf_b64_list else "les valeurs extraites ci-dessous (PDF non disponible sur le serveur)"

    # ── 3. Prompt selon type_analyse ─────────────────────────────────────────

    if type_analyse == 'pca':
        # ── PCA : Pré-analyse technique (état du bâtiment, travaux) ──────────
        system_prompt = f"""Tu es ConformExpert, un expert en pathologie du bâtiment et diagnostic technique immobilier.
Tu réalises des pré-analyses techniques (PCA - Property Condition Assessment) à partir de documents fournis par le client (plans, photos, rapports de diagnostic, DDT, carnet d'entretien, etc.).

Contexte du dossier :
- Référence : {ref}
- Projet : {document.name}
- Client : {document.client_name or 'Non renseigné'}
- Type d'analyse : Pré-analyse technique (PCA)
- Informations du bâtiment :
{infos_batiment}
- Source des données : {source_donnees}
- Référentiel technique interne (PCA) :
{pca_seuils_str}

Tu dois générer un rapport PCA structuré et professionnel.
Réponds UNIQUEMENT en JSON valide, sans markdown, sans explication, sans balises.

Structure JSON attendue :
{{
  "verdict": "Bon état général" | "État moyen — travaux à prévoir" | "État dégradé — intervention urgente" | "Données insuffisantes",
  "score_global": 72,
  "resume_executif": "Paragraphe de 3-5 phrases résumant l'état général du bâtiment et les principaux enjeux.",
  "etat_technique": [
    {{
      "composant": "Toiture",
      "etat": "Bon" | "Moyen" | "Mauvais",
      "observation": "Description précise de l'état observé ou estimé.",
      "risque": "faible" | "modéré" | "élevé"
    }}
  ],
  "travaux": [
    {{
      "horizon": "Immédiat" | "1-3 ans" | "3-5 ans" | "5-10 ans",
      "titre": "Intitulé des travaux",
      "description": "Description des travaux à réaliser.",
      "cout_estime": "15 000 — 25 000 €",
      "priorite": "URGENT" | "IMPORTANT" | "PLANIFIABLE"
    }}
  ],
  "enveloppe": {{
    "synthese": "Analyse de l'enveloppe : façades, toiture, menuiseries, étanchéité.",
    "points_attention": ["Point 1", "Point 2"]
  }},
  "systemes": {{
    "synthese": "Analyse des systèmes : chauffage, plomberie, électricité, ventilation.",
    "points_attention": ["Point 1", "Point 2"]
  }},
  "risques": [
    {{
      "titre": "Titre du risque identifié",
      "description": "Description du risque.",
      "gravite": "faible" | "modéré" | "élevé",
      "action": "Action recommandée."
    }}
  ],
  "points_forts": ["Point fort 1", "Point fort 2"],
  "enveloppe_budgetaire": {{
    "court_terme": "0 — 5 000 €",
    "moyen_terme": "20 000 — 40 000 €",
    "long_terme": "50 000 — 80 000 €",
    "total_estime": "70 000 — 125 000 €"
  }},
  "mentions_legales": "Ce rapport est établi sur la base des documents fournis et constitue une pré-analyse documentaire indépendante. Il ne se substitue pas à un diagnostic technique complet réalisé par un expert certifié sur site."
}}

Base ton analyse sur les documents fournis. Si des éléments ne sont pas documentés, indique-le dans les observations mais génère quand même une estimation professionnelle basée sur le type et l'âge du bâtiment.
Sois précis, factuel, professionnel. Le rapport doit être utile à un investisseur ou propriétaire."""

    elif type_analyse == 'complet':
        # ── COMPLET : Énergie + PCA combinés ─────────────────────────────────
        seuils_str = SEUILS_LABELS.get(norme, "Voir réglementation applicable")
        system_prompt = f"""Tu es ConformExpert, un expert en réglementation thermique ET en diagnostic technique du bâtiment.
Tu réalises des analyses complètes combinant la conformité énergétique réglementaire et la pré-analyse technique (PCA).

Contexte du dossier :
- Référence : {ref}
- Projet : {document.name}
- Client : {document.client_name or 'Non renseigné'}
- Type d'analyse : Analyse complète (Énergie + Technique)
- Norme applicable : {norme}
- Informations du bâtiment :
{infos_batiment}
- Source des données : {source_donnees}
- Valeurs thermiques extraites :
{valeurs_str}
- Seuils réglementaires {norme} :
  {seuils_str}

Tu dois générer un rapport complet combinant conformité thermique ET état technique.
Réponds UNIQUEMENT en JSON valide, sans markdown, sans explication, sans balises.

Structure JSON attendue :
{{
  "verdict_energie": "Conforme" | "Non Conforme" | "Données insuffisantes",
  "verdict_technique": "Bon état général" | "État moyen — travaux à prévoir" | "État dégradé — intervention urgente" | "Données insuffisantes",
  "score_global": 68,
  "resume_executif": "Paragraphe de 4-6 phrases résumant les conclusions énergétiques ET techniques.",
  "criteres": [
    {{
      "nom": "Nom du critère thermique",
      "valeur": 72.0,
      "seuil": 50.0,
      "unite": "kWh ep/m².an",
      "conforme": false,
      "ecart_pct": 44.0,
      "commentaire": "Explication courte."
    }}
  ],
  "etat_technique": [
    {{
      "composant": "Toiture",
      "etat": "Bon" | "Moyen" | "Mauvais",
      "observation": "Description précise.",
      "risque": "faible" | "modéré" | "élevé"
    }}
  ],
  "travaux": [
    {{
      "horizon": "Immédiat" | "1-3 ans" | "3-5 ans" | "5-10 ans",
      "titre": "Intitulé des travaux",
      "description": "Description.",
      "cout_estime": "15 000 — 25 000 €",
      "priorite": "URGENT" | "IMPORTANT" | "PLANIFIABLE",
      "impact_energetique": "Impact sur la performance énergétique si applicable, sinon null"
    }}
  ],
  "non_conformites": [
    {{
      "critere": "Nom",
      "gravite": "bloquant" | "majeur" | "mineur",
      "description": "Description du problème.",
      "action": "Action corrective.",
      "delai": "2 à 6 semaines",
      "cout_estime": "8 000 — 15 000 €"
    }}
  ],
  "recommandations": [
    {{
      "priorite": "URGENT" | "RECOMMANDÉ" | "OPTIONNEL",
      "titre": "Titre",
      "description": "Description détaillée.",
      "impact_reglementaire": "Impact sur la conformité énergétique.",
      "delai": "2 à 6 semaines"
    }}
  ],
  "enveloppe": {{
    "synthese": "Analyse de l'enveloppe : performance thermique + état physique.",
    "points_attention": ["Point 1", "Point 2"]
  }},
  "systemes_energetiques": {{
    "synthese": "Analyse des systèmes CVC, ECS, état et performance.",
    "equipements": [
      {{"poste": "Chauffage", "equipement": "PAC air-eau", "performance": "COP 3,24", "evaluation": "Performant"}}
    ]
  }},
  "risques": [
    {{
      "titre": "Titre du risque",
      "description": "Description.",
      "gravite": "faible" | "modéré" | "élevé",
      "action": "Action recommandée."
    }}
  ],
  "points_forts": ["Point fort 1", "Point fort 2"],
  "enveloppe_budgetaire": {{
    "travaux_conformite": "15 000 — 30 000 €",
    "travaux_techniques": "25 000 — 50 000 €",
    "total_estime": "40 000 — 80 000 €"
  }},
  "contexte_reglementaire": "Paragraphe expliquant la réglementation {norme} applicable.",
  "mentions_legales": "Ce rapport est établi sur la base des documents fournis et constitue une analyse documentaire indépendante. Il ne se substitue pas à une attestation officielle de conformité ni à un diagnostic technique complet réalisé sur site."
}}

Si une valeur thermique n'est pas disponible pour un critère, omets ce critère.
Sois précis, factuel, professionnel."""

    else:
        # ── ÉNERGIE : prompt actuel amélioré ──────────────────────────────────
        seuils_str = SEUILS_LABELS.get(norme, "Voir réglementation applicable")
        system_prompt = f"""Tu es ConformExpert, un expert en réglementation thermique et énergétique des bâtiments.
Tu analyses des documents techniques (notices thermiques, attestations, CCTP, études STD) et tu génères des rapports de conformité professionnels, précis et adaptés à la réglementation applicable.

Contexte du dossier :
- Référence : {ref}
- Projet : {document.name}
- Client : {document.client_name or 'Non renseigné'}
- Type d'analyse : Pré-analyse énergétique
- Norme applicable : {norme}
- Informations du bâtiment :
{infos_batiment}
- Source des données : {source_donnees}
- Valeurs extraites :
{valeurs_str}
- Seuils réglementaires {norme} :
  {seuils_str}

Tu dois générer un rapport structuré complet.
Réponds UNIQUEMENT en JSON valide, sans markdown, sans explication, sans balises.

Structure JSON attendue :
{{
  "verdict": "Conforme" | "Non Conforme" | "Données insuffisantes",
  "score_global": 78,
  "resume_executif": "Paragraphe de 3-5 phrases résumant les conclusions principales.",
  "criteres": [
    {{
      "nom": "Nom du critère",
      "valeur": 72.0,
      "seuil": 50.0,
      "unite": "kWh ep/m².an",
      "conforme": false,
      "ecart_pct": 44.0,
      "commentaire": "Explication courte de la situation."
    }}
  ],
  "points_forts": ["Point fort 1", "Point fort 2"],
  "non_conformites": [
    {{
      "critere": "Nom",
      "gravite": "bloquant" | "majeur" | "mineur",
      "description": "Description du problème.",
      "action": "Action corrective recommandée.",
      "delai": "2 à 6 semaines",
      "cout_estime": "8 000 — 15 000 €"
    }}
  ],
  "recommandations": [
    {{
      "priorite": "URGENT" | "RECOMMANDÉ" | "OPTIONNEL",
      "titre": "Titre de la recommandation",
      "description": "Description détaillée de l'action à mener.",
      "impact_reglementaire": "Impact sur le critère concerné.",
      "delai": "2 à 6 semaines"
    }}
  ],
  "analyse_enveloppe": {{
    "synthese": "Paragraphe sur l'enveloppe thermique.",
    "points_attention": ["Point 1", "Point 2"]
  }},
  "systemes_energetiques": {{
    "synthese": "Paragraphe sur les systèmes CVC, ECS, éclairage.",
    "equipements": [
      {{"poste": "Chauffage", "equipement": "PAC air-eau", "performance": "COP 3,24", "evaluation": "Performant"}}
    ]
  }},
  "impact_financier": {{
    "cout_non_conformite": "Estimation du surcoût lié aux non-conformités si applicable.",
    "economies_potentielles": "Économies annuelles estimées après mise en conformité.",
    "retour_investissement": "Délai de retour sur investissement estimé."
  }},
  "contexte_reglementaire": "Paragraphe expliquant la réglementation {norme} applicable à ce projet.",
  "mentions_legales": "Ce rapport est établi sur la base des documents fournis et constitue une analyse documentaire indépendante. Il ne se substitue pas à une attestation officielle de conformité."
}}

Si une valeur n'est pas disponible pour un critère, omets ce critère du tableau.
Sois précis, factuel, professionnel. Adapte le niveau de détail à la norme {norme}."""


    # Observations expert
    observations_expert = document.admin_notes if document.admin_notes else "Aucune observation expert fournie."

    # Données factures énergie
    factures_data = []
    try:

        for f in document.factures.all():

            d = f.analyse_json or {}

            factures_data.append({
                "energie": f.type_energie,
                "periode_debut": d.get("periode_debut"),
                "periode_fin": d.get("periode_fin"),
                "consommation": d.get("consommation"),
                "montant_ttc": d.get("montant_ttc"),
                "analyse_ok": f.analyse_ok
            })

    except Exception as e:
        print("Erreur lecture factures:", e)

    factures_str = json.dumps(factures_data, ensure_ascii=False)

    # Données OpenStudio
    openstudio_files = document.fichiers.filter(type_fichier__startswith="openstudio")

    openstudio_data = []

    for f in openstudio_files:

        try:
            with open(f.fichier.path, "r", encoding="utf-8", errors="ignore") as file:

                contenu = file.read()

            openstudio_data.append({
                "nom": f.nom,
                "contenu": contenu[:12000]
            })

        except Exception as e:
            print("Erreur OpenStudio:", e)

    openstudio_str = json.dumps(openstudio_data, ensure_ascii=False)

    # ── 4. Message Claude ─────────────────────────────────────────────────────
    user_content = []
    headers_extra = {}

    if pdf_b64_list:
        for b64 in pdf_b64_list:
            user_content.append({
                "type": "document",
                "source": {"type": "base64", "media_type": "application/pdf", "data": b64}
            })
        headers_extra = {"anthropic-beta": "pdfs-2024-09-25"}
        nb = len(pdf_b64_list)
        user_content.append({
        "type": "text",
        "text": f"""
        Tu es un ingénieur expert en performance énergétique des bâtiments.

        Tu réalises une pré-analyse énergétique professionnelle basée sur :
        - les données réglementaires
        - les observations techniques
        - les factures énergétiques réelles
        - les résultats de simulation énergétique OpenStudio

        Ton objectif est d’identifier :
        - la conformité réglementaire
        - les écarts entre simulation et consommation réelle
        - les risques énergétiques
        - les pistes d'amélioration.

        ---

        INFORMATIONS BÂTIMENT

        {infos_batiment}

        ---

        OBSERVATIONS EXPERT

        {observations_expert}

        Ces observations peuvent contenir :
        - défauts d’isolation
        - problèmes d’étanchéité
        - systèmes énergétiques observés
        - travaux récents

        Utilise ces informations pour enrichir ton analyse.

        ---

        FACTURES ÉNERGÉTIQUES

        {factures_str}

        Ces factures représentent la consommation réelle du bâtiment.

        Analyse :
        - la cohérence des consommations
        - les niveaux de consommation
        - les anomalies éventuelles.

        ---

        SIMULATION ÉNERGÉTIQUE OPENSTUDIO

        {openstudio_str}

        Ces données proviennent d’une simulation énergétique du bâtiment.

        Analyse :
        - la consommation simulée
        - les performances de l’enveloppe
        - les systèmes énergétiques simulés.

        ---

        MISSION D’ANALYSE

        1. Vérifier la conformité réglementaire selon la norme du projet.
        2. Comparer les consommations réelles (factures) avec les consommations simulées (OpenStudio).
        3. Identifier les écarts énergétiques éventuels.
        4. Proposer des explications techniques possibles :
           - isolation insuffisante
           - infiltration d’air
           - systèmes énergétiques inefficaces
           - comportement des occupants
        5. Identifier les points forts énergétiques du bâtiment.
        6. Formuler des recommandations d'amélioration réalistes.

        ---

        STRUCTURE DU RAPPORT

        Le rapport doit être structuré de la manière suivante :

        1. Résumé exécutif  
        Présenter une synthèse claire de la performance énergétique du bâtiment, du niveau de conformité réglementaire et des principaux constats.

        2. Vérification réglementaire  
        Analyser chaque critère réglementaire applicable à la norme du projet et indiquer :
        - la valeur observée
        - le seuil réglementaire
        - le niveau de conformité.

        3. Analyse des performances énergétiques  
        Évaluer la performance globale du bâtiment en tenant compte :
        - des données techniques
        - des observations expert
        - des simulations énergétiques OpenStudio.

        4. Comparaison simulation / consommation réelle  
        Comparer les consommations issues des factures avec les consommations simulées.  
        Identifier les écarts éventuels et proposer des explications techniques possibles.

        5. Analyse de l’enveloppe thermique  
        Analyser les performances des murs, toiture, planchers, fenêtres et l’étanchéité à l’air.

        6. Analyse des systèmes énergétiques  
        Évaluer les systèmes de chauffage, ventilation, climatisation et production d’eau chaude si les données sont disponibles.

        7. Points forts du bâtiment  
        Identifier les éléments positifs contribuant à la performance énergétique.

        8. Points de vigilance  
        Identifier les éléments pouvant dégrader la performance énergétique ou réduire la marge de conformité.

        9. Recommandations techniques  
        Proposer des améliorations réalistes permettant d’améliorer la performance énergétique du bâtiment.

        10. Contexte réglementaire  
        Rappeler brièvement les exigences de la norme énergétique applicable au projet.

        ---

        IMPORTANT

        - Ne jamais inventer de données.
        - Si certaines informations sont manquantes, le mentionner.
        - Utiliser uniquement les données fournies dans le dossier.

        ---

        Génère ensuite le rapport complet en respectant le format JSON attendu par l'application.
        """
        })
    else:
        user_content.append({
            "type": "text",
            "text": f"Le PDF original n'est pas disponible. Génère le rapport JSON complet pour le dossier {ref} (type : {type_analyse}) en te basant exclusivement sur les informations fournies dans le contexte."
        })

    # ── 5. Appel API Claude ───────────────────────────────────────────────────
    try:
        payload = json.dumps({
            "model": "claude-sonnet-4-5",
            "max_tokens": 8000,
            "system": system_prompt,
            "messages": [{"role": "user", "content": user_content}]
        }).encode('utf-8')

        headers = {
            "Content-Type": "application/json",
            "x-api-key": ANTHROPIC_API_KEY,
            "anthropic-version": "2023-06-01",
        }
        headers.update(headers_extra)

        req = urllib.request.Request(
            "https://api.anthropic.com/v1/messages",
            data=payload, headers=headers, method="POST"
        )
        with urllib.request.urlopen(req, timeout=120) as resp:
            result = json.loads(resp.read().decode('utf-8'))
            raw = result['content'][0]['text'].strip().replace('```json', '').replace('```', '').strip()
            rapport = json.loads(raw)

            # Sauvegarder en BDD
            document.rapport_ia_json = json.dumps(rapport, ensure_ascii=False)
            document.save(update_fields=['rapport_ia_json'])

            return JsonResponse({'success': True, 'rapport': rapport, 'cached': False})

    except urllib.error.HTTPError as e:
        body = e.read().decode('utf-8')
        print(f"CLAUDE API ERROR {e.code}: {body}")
        return JsonResponse({'error': f'Erreur API Claude ({e.code}) : {body[:300]}'}, status=500)
    except json.JSONDecodeError as e:
        print(f"JSON PARSE ERROR: {e}")
        return JsonResponse({'error': f'Erreur parsing JSON : {str(e)}'}, status=500)
    except Exception as e:
        print(f"GENERER_RAPPORT_IA ERROR: {e}")
        return JsonResponse({'error': str(e)}, status=500)


# ══════════════════════════════════════════════════════════════════
#  FACTURES ÉNERGIE — Analyse par IA
# ══════════════════════════════════════════════════════════════════

_PROMPT_FACTURE = """
Tu es un expert en analyse de factures d'énergie (électricité et gaz naturel).
Analyse attentivement cette facture et extrais toutes les données disponibles.

Réponds UNIQUEMENT avec un objet JSON valide, sans texte avant ni après, sans balises markdown.
Schéma exact :

{
  "fournisseur": "nom du fournisseur (ex: Hydro-Québec, Énergir, EDF...)",
  "type_energie": "electricite" ou "gaz",
  "periode_debut": "YYYY-MM-DD",
  "periode_fin": "YYYY-MM-DD",
  "nb_jours": 30,
  "consommation": 1250.5,
  "unite": "kWh",
  "montant_ht": 145.20,
  "montant_ttc": 162.50,
  "devise": "CAD",
  "tarif": "nom du tarif (ex: Tarif D, G, DM...)",
  "puissance_souscrite_kw": null,
  "numero_client": null,
  "numero_compteur": null,
  "adresse_consommation": null,
  "cout_par_kwh": 0.115,
  "notes": "toute observation pertinente"
}

Si une valeur est absente, utilise null.
Pour cout_par_kwh : calcule-le si possible (montant_ht / consommation).
Pour le gaz : convertis en kWh équivalent si possible (1 m³ ≈ 10.55 kWh).
"""


def _analyser_facture_ia(fichier_path):
    """Envoie un PDF de facture à Claude et retourne le dict extrait."""
    import json, base64, re as _re
    import anthropic
    client = anthropic.Anthropic()
    with open(fichier_path, 'rb') as f:
        pdf_b64 = base64.standard_b64encode(f.read()).decode('utf-8')
    resp = client.messages.create(
        model="claude-opus-4-5",
        max_tokens=1200,
        messages=[{
            "role": "user",
            "content": [
                {"type": "document", "source": {"type": "base64", "media_type": "application/pdf", "data": pdf_b64}},
                {"type": "text", "text": _PROMPT_FACTURE},
            ],
        }]
    )
    raw = resp.content[0].text.strip()
    raw = _re.sub(r'^```(?:json)?\s*', '', raw)
    raw = _re.sub(r'\s*```$', '', raw)
    return json.loads(raw)


def upload_facture(request, doc_id):
    """Upload d'une facture PDF pour un dossier."""
    if not request.user.is_authenticated:
        return JsonResponse({'success': False, 'error': 'Non authentifié — rechargez la page'}, status=401)
    if request.method != 'POST':
        return JsonResponse({'success': False, 'error': 'Méthode non autorisée'})
    try:
        document = get_object_or_404(Document, id=doc_id)
        fichier = request.FILES.get('fichier')
        if not fichier:
            return JsonResponse({'success': False, 'error': 'Aucun fichier reçu'})
        if not fichier.name.lower().endswith('.pdf'):
            return JsonResponse({'success': False, 'error': 'Seuls les PDF sont acceptés'})
        type_energie = request.POST.get('type_energie', 'electricite')
        facture = FactureEnergie.objects.create(
            document=document,
            fichier=fichier,
            nom=fichier.name,
            type_energie=type_energie,
        )
        return JsonResponse({'success': True, 'facture_id': facture.id, 'nom': facture.nom})
    except Exception as e:
        err = str(e)
        if 'no such table' in err or 'does not exist' in err:
            return JsonResponse({'success': False, 'error': 'Migration manquante — lancez : python manage.py makemigrations && python manage.py migrate'})
        return JsonResponse({'success': False, 'error': err})


def analyser_facture(request, facture_id):
    """Analyse IA d'une seule facture."""
    if not request.user.is_authenticated:
        return JsonResponse({'success': False, 'error': 'Non authentifié'}, status=401)
    if request.method != 'POST':
        return JsonResponse({'success': False, 'error': 'Méthode non autorisée'})
    facture = get_object_or_404(FactureEnergie, id=facture_id)
    try:
        donnees = _analyser_facture_ia(facture.fichier.path)
        facture.analyse_json  = donnees
        facture.analyse_ok    = True
        facture.analyse_error = ''
        facture.save()
        return JsonResponse({'success': True, 'donnees': donnees})
    except Exception as e:
        facture.analyse_error = str(e)
        facture.analyse_ok    = False
        facture.save()
        return JsonResponse({'success': False, 'error': str(e)})


def analyser_toutes_factures(request, doc_id):
    """Analyse IA de toutes les factures non encore analysées d'un dossier."""
    if not request.user.is_authenticated:
        return JsonResponse({'success': False, 'error': 'Non authentifié'}, status=401)
    if request.method != 'POST':
        return JsonResponse({'success': False, 'error': 'Méthode non autorisée'})
    document = get_object_or_404(Document, id=doc_id)
    factures = document.factures.filter(analyse_ok=False)
    resultats = []
    for facture in factures:
        try:
            donnees = _analyser_facture_ia(facture.fichier.path)
            facture.analyse_json  = donnees
            facture.analyse_ok    = True
            facture.analyse_error = ''
            facture.save()
            resultats.append({'id': facture.id, 'nom': facture.nom, 'ok': True})
        except Exception as e:
            facture.analyse_error = str(e)
            facture.analyse_ok    = False
            facture.save()
            resultats.append({'id': facture.id, 'nom': facture.nom, 'ok': False, 'error': str(e)})
    return JsonResponse({'success': True, 'resultats': resultats})


def supprimer_facture(request, facture_id):
    """Suppression d'une facture et de son fichier."""
    if not request.user.is_authenticated:
        return JsonResponse({'success': False, 'error': 'Non authentifié'}, status=401)
    if request.method != 'POST':
        return JsonResponse({'success': False, 'error': 'Méthode non autorisée'})
    facture = get_object_or_404(FactureEnergie, id=facture_id)
    try:
        facture.fichier.delete(save=False)
        facture.delete()
        return JsonResponse({'success': True})
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)})


def get_donnees_factures(request, doc_id):
    """Retourne les données agrégées des factures analysées — public (via token) ou admin."""
    import json as _json
    try:
        document = get_object_or_404(Document, id=doc_id)
        factures = document.factures.filter(analyse_ok=True).order_by('uploaded_at')
    except Exception as e:
        # Table FactureEnergie inexistante (migration manquante)
        return JsonResponse({'success': False, 'error': f'Migration manquante : {str(e)}', 'mois': [], 'nb_factures': 0})
    mois = []
    for f in factures:
        d = f.analyse_json or {}
        if d.get('consommation') is not None:
            mois.append({
                'periode_debut':  d.get('periode_debut'),
                'periode_fin':    d.get('periode_fin'),
                'consommation':   d.get('consommation'),
                'unite':          d.get('unite', 'kWh'),
                'montant_ttc':    d.get('montant_ttc'),
                'cout_par_kwh':   d.get('cout_par_kwh'),
                'type_energie':   f.type_energie,
                'fournisseur':    d.get('fournisseur'),
                'devise':         d.get('devise', 'CAD'),
                'nom':            f.nom,
            })
    conso_totale = sum(m['consommation'] for m in mois if m['consommation'])
    cout_total   = sum(m['montant_ttc']  for m in mois if m['montant_ttc'])
    cout_moyen   = round(cout_total / conso_totale, 4) if conso_totale else None
    pic          = max((m['consommation'] for m in mois if m['consommation']), default=None)
    return JsonResponse({
        'success':        True,
        'mois':           mois,
        'conso_totale':   round(conso_totale, 1),
        'cout_total':     round(cout_total, 2),
        'cout_moyen_kwh': cout_moyen,
        'pic_mensuel':    pic,
        'nb_factures':    len(mois),
    })


def rapport_ia_client(request, token):
    """Page publique rapport IA — accessible via lien de suivi, sans login."""

    import json as _json

    document = get_object_or_404(Document, tracking_token=token, status='termine')

    rapport = None

    # si un rapport IA existe déjà
    if document.rapport_ia_json:
        try:
            rapport = _json.loads(document.rapport_ia_json)
        except Exception:
            rapport = None

    # si c'est un PCA sans rapport IA
    if document.type_analyse == "pca" and not rapport:
        rapport = analyse_pca(document)

    # Données factures côté client
    import json as _json2
    factures_data = []
    if document.type_analyse in ('energie', 'complet'):
        for f in document.factures.filter(analyse_ok=True).order_by('uploaded_at'):
            d = f.analyse_json or {}
            if d.get('consommation') is not None:
                factures_data.append({
                    'periode_debut': d.get('periode_debut'),
                    'periode_fin':   d.get('periode_fin'),
                    'consommation':  d.get('consommation'),
                    'unite':         d.get('unite', 'kWh'),
                    'montant_ttc':   d.get('montant_ttc'),
                    'cout_par_kwh':  d.get('cout_par_kwh'),
                    'type_energie':  f.type_energie,
                    'devise':        d.get('devise', 'CAD'),
                })

    return render(request, "main/rapport_ia_client.html", {
        "document":      document,
        "rapport":       rapport,
        "factures_data": _json2.dumps(factures_data, ensure_ascii=False),
        "has_factures":  len(factures_data) > 0,
    })



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
