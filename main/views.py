import io
import csv
import chardet
from django.shortcuts import render, redirect, get_object_or_404
from django.http import HttpResponse, FileResponse
from django.contrib import messages
from django.views.decorators.csrf import csrf_exempt

from rest_framework.decorators import api_view
from rest_framework.response import Response
from rest_framework import status

from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas

from .models import Document
from .forms import DocumentForm, ContactForm
from .serializers import DocumentSerializer

# --- VUES GÉNÉRALES ---

def home(request):
    documents = Document.objects.all()
    return render(request, 'main/home.html', {'documents': documents})

def contact(request):
    if request.method == 'POST':
        form = ContactForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, 'Informations de contact enregistrées.')
            return redirect('contact_success')
    else:
        form = ContactForm()
    return render(request, 'main/contact.html', {'form': form})

def faq(request):
    return render(request, 'main/faq.html')

def history(request):
    documents = Document.objects.all()
    return render(request, 'main/history.html', {'documents': documents})

def settings(request):
    return render(request, 'main/settings.html')

# --- IMPORT ET ANALYSE ---

def import_document(request):
    if request.method == 'POST':
        form = DocumentForm(request.POST, request.FILES)
        if form.is_valid():
            document = form.save()
            data = read_document(document.upload.path)
            if data:
                analyze_document(document, data)
                messages.success(request, 'Document analysé avec succès.')
                return redirect('results')
            else:
                messages.error(request, "Aucune donnée valide trouvée dans le fichier.")
        else:
            messages.error(request, "Le formulaire n'est pas valide.")
    else:
        form = DocumentForm()
    return render(request, 'main/import.html', {'form': form})

def read_document(upload_path):
    """Lit le CSV et mappe les colonnes FR vers les clés Anglaises utilisées par le code"""
    try:
        with open(upload_path, 'rb') as file:
            raw_data = file.read()
            encoding = chardet.detect(raw_data)['encoding']
        
        with open(upload_path, 'r', encoding=encoding) as file:
            reader = csv.DictReader(file)
            for row in reader:
                # Fonction utilitaire pour nettoyer les nombres (virgule -> point)
                def clean_float(val):
                    try:
                        return float(str(val).replace(',', '.'))
                    except (ValueError, TypeError):
                        return 0.0

                return {
                    'energy_efficiency': clean_float(row.get('Efficacité énergétique', 0)),
                    'thermal_comfort': clean_float(row.get('Confort thermique', 0)),
                    'carbon_emissions': clean_float(row.get('Émissions de carbone', 0)),
                    'water_management': clean_float(row.get("Gestion de l'eau", 0)),
                    'indoor_air_quality': clean_float(row.get("Qualité de l'air intérieur", 0)),
                }
        return {}
    except Exception as e:
        print(f"Erreur lecture fichier: {e}")
        return {}

def analyze_document(document, data):
    """Enregistre les données dans les champs spécifiques RE2020 et RT2012 du modèle"""
    # Données RE2020
    document.re2020_energy_efficiency = data.get('energy_efficiency', 0.0)
    document.re2020_thermal_comfort = data.get('thermal_comfort', 0.0)
    document.re2020_carbon_emissions = data.get('carbon_emissions', 0.0)
    document.re2020_water_management = data.get('water_management', 0.0)
    document.re2020_indoor_air_quality = data.get('indoor_air_quality', 0.0)
    
    # Données RT2012 (On utilise les mêmes pour l'instant selon votre logique)
    document.rt2012_energy_efficiency = data.get('energy_efficiency', 0.0)
    document.rt2012_thermal_comfort = data.get('thermal_comfort', 0.0)
    document.rt2012_carbon_emissions = data.get('carbon_emissions', 0.0)
    document.rt2012_water_management = data.get('water_management', 0.0)
    document.rt2012_indoor_air_quality = data.get('indoor_air_quality', 0.0)
    
    document.save()

# --- RÉSULTATS ET RAPPORTS ---

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
        'energy_efficiency': 50.0,
        'thermal_comfort': 22.0,
        'carbon_emissions': 35.0,
        'water_management': 120.0,
        'indoor_air_quality': 800.0,
    }

def results(request):
    documents = Document.objects.all()
    return render(request, 'main/results.html', {
        'documents': documents,
        're2020_requirements': fetch_re2020_requirements(),
        'rt2012_requirements': fetch_rt2012_requirements(),
    })

def download_report(request, document_id):
    document = get_object_or_404(Document, id=document_id)
    buffer = generate_report(document)
    return FileResponse(buffer, as_attachment=True, filename=f"report_{document.name}.pdf")

def generate_report(document):
    buffer = io.BytesIO()
    p = canvas.Canvas(buffer, pagesize=letter)
    p.setFont("Helvetica", 12)
    p.drawString(100, 800, f"Rapport d'analyse pour {document.name}")
    p.drawString(100, 780, f"Date de l'analyse: {document.upload_date.strftime('%d %b %Y')}")
    y = 760
    
    # Utilisation des nouveaux noms de champs du modèle
    details = [
        ("Efficacité énergétique (RE2020)", document.re2020_energy_efficiency),
        ("Confort thermique (RE2020)", document.re2020_thermal_comfort),
        ("Émissions de carbone (RE2020)", document.re2020_carbon_emissions),
        ("Gestion de l'eau (RE2020)", document.re2020_water_management),
        ("Qualité de l'air intérieur (RE2020)", document.re2020_indoor_air_quality),
    ]
    
    for label, value in details:
        p.drawString(100, y, f"{label}: {value}")
        y -= 20
    
    p.showPage()
    p.save()
    buffer.seek(0)
    return buffer

# --- ACTIONS ET API ---

def update_re2020(request):
    if request.method == 'POST':
        messages.success(request, 'Les paramètres RE2020 ont été mis à jour.')
    else:
        messages.error(request, 'Méthode de requête invalide.')
    return redirect('settings')

def delete_document(request, doc_id):
    if request.method == 'POST':
        document = get_object_or_404(Document, id=doc_id)
        document.delete()
        messages.success(request, 'Document supprimé.')
    return redirect('history')

@csrf_exempt
@api_view(['GET'])
def api_report(request, pk):
    try:
        document = Document.objects.get(pk=pk)
        buffer = generate_report(document)
        response = HttpResponse(buffer, content_type='application/pdf')
        response['Content-Disposition'] = f'attachment; filename="report_{document.name}.pdf"'
        return response
    except Document.DoesNotExist:
        return Response(status=status.HTTP_404_NOT_FOUND)

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
