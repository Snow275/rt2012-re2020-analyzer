from django.shortcuts import render, redirect, get_object_or_404
from django.http import HttpResponse, FileResponse, JsonResponse
from .models import Document
from .forms import DocumentForm, ContactForm
from rest_framework.decorators import api_view
from rest_framework.response import Response
from rest_framework import status
from .serializers import DocumentSerializer, AnalysisSerializer
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
from django.contrib import messages
import io
import csv
import chardet
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas

def home(request):
    documents = Document.objects.all()
    return render(request, 'main/home.html', {'documents': documents})

def contact(request):
    if request.method == 'POST':
        form = ContactForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, 'Contact info successfully saved.')
            return redirect('contact_success')
    else:
        form = ContactForm()
    return render(request, 'main/contact.html', {'form': form})

def faq(request):
    return render(request, 'main/faq.html')

def import_document(request):
    if request.method == 'POST':
        form = DocumentForm(request.POST, request.FILES)
        if form.is_valid():
            document = form.save()  # Save the document to get a file path from the model's file field automatically
            data = read_document(document.upload.path) 
            if data:
                analyze_document(document, data)  # Analyse des données extraites
                document.save()  # Sauvegarde des modifications apportées au document après l'analyse
                messages.success(request, 'Document successfully analyzed.')
                return redirect('results')  # Redirection vers la page des résultats
            else:
                messages.error(request, "No valid data found in file.")
        else:
            messages.error(request, "Form is not valid.")
    else:
        form = DocumentForm()
    return render(request, 'main/import.html', {'form': form})


def analyze_document(document, data):
    data = read_document(document.upload.path)
    save_analysis_results(document, data)
    document.name = data.get('energy_efficiency', 0.0)
    document.name = data.get('thermal_comfort', 0.0)
    document.name = data.get('carbon_emissions', 0.0)
    document.name = data.get('water_management', 0.0)
    document.name = data.get('indoor_air_quality', 0.0)
    document.save()

def save_analysis_results(document, data):
    requirements = fetch_requirements()
    compliance = check_compliance(data, requirements)
    # Update document fields for RE2020 and RT2012 analysis
    update_document_fields(document, data, compliance)

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


def check_compliance(data, requirements):
    return {
        'energy_efficiency': data.get('energy_efficiency', 0.0) >= requirements['energy_efficiency'],
        'thermal_comfort': data.get('thermal_comfort', 0.0) >= requirements['thermal_comfort'],
        'carbon_emissions': data.get('carbon_emissions', 0.0) <= requirements['carbon_emissions'],
        'water_management': data.get('water_management', 0.0) >= requirements['water_management'],
        'indoor_air_quality': data.get('indoor_air_quality', 0.0) >= requirements['indoor_air_quality'],
    }

def update_document_fields(document, data, compliance):
    # Assigning both the fetched data values and the compliance check
    for field, value in data.items():
        setattr(document, field, value)
    for field, is_compliant in compliance.items():
        setattr(document, f"{field}_compliance", is_compliant)

def results(request):
    documents = Document.objects.all()

    re2020_requirements = fetch_re2020_requirements()
    rt2012_requirements = fetch_rt2012_requirements()

    return render(request, 'main/results.html', {
        'documents': documents,
        're2020_requirements': re2020_requirements,
        'rt2012_requirements': rt2012_requirements,
    })


def read_document(upload_path):
    try:
        with open(upload_path, 'rb') as file:
            raw_data = file.read()
            encoding = chardet.detect(raw_data)['encoding']

        with open(upload_path, 'r', encoding=encoding) as file:
            reader = csv.DictReader(file)

            for row in reader:
                print("Colonnes détectées :", row.keys())  # DEBUG

                return {
                    'energy_efficiency': float(row.get('Efficacité énergétique', 0)),
                    'thermal_comfort': float(row.get('Confort thermique', 0)),
                    'carbon_emissions': float(row.get('Émissions de carbone', 0)),
                    'water_management': float(row.get("Gestion de l'eau", 0)),
                    'indoor_air_quality': float(row.get("Qualité de l'air intérieur", 0)),
                }

        return {}

    except Exception as e:
        print("Erreur lecture fichier:", e)
        return {}

def update_re2020(request):
    if request.method == 'POST':
        # Si la méthode de la requête est POST, afficher un message de succès
        messages.success(request, 'Les paramètres RE2020 ont été mis à jour avec succès.')
        # Rediriger vers la page des paramètres
        return redirect('settings')
    else:
        # Si la méthode de la requête n'est pas POST, afficher un message d'erreur
        messages.error(request, 'Méthode de requête invalide.')
        # Rediriger vers la page des paramètres
        return redirect('settings')

    
def delete_document(request, doc_id):
    if request.method == 'POST':
        document = get_object_or_404(Document, id=doc_id)
        document.delete()  # This deletes the document
        return redirect('history')  # Redirect to the history page or wherever appropriate
    return redirect('history')  # Handle case where someone navigates directly to the URL

def download_report(request, document_id):
    document = get_object_or_404(Document, id=document_id)
    buffer = io.BytesIO()
    p = canvas.Canvas(buffer, pagesize=letter)
    p.setFont("Helvetica", 12)

    # Document details
    p.drawString(100, 800, f"Rapport d'analyse pour {document.name}")
    p.drawString(100, 780, f"Date de l'analyse: {document.upload_date.strftime('%d %b %Y')}")

    # Document analysis results
    y = 760
    details = [
        ("Efficacité énergétique (RE2020)", document.re2020_energy_efficiency),
        ("Confort thermique (RE2020)", document.re2020_thermal_comfort),
        ("Émissions de carbone (RE2020)", document.re2020_carbon_emissions),
        ("Gestion de l'eau (RE2020)", document.re2020_water_management),
        ("Qualité de l'air intérieur (RE2020)", document.re2020_indoor_air_quality),
        # Add RT2012 details if needed
    ]

    for label, value in details:
        p.drawString(100, y, f"{label}: {value}")
        y -= 20

    p.showPage()
    p.save()
    buffer.seek(0)
    return FileResponse(buffer, as_attachment=True, filename=f"report_{document.name}.pdf")

def generate_report(document):
    buffer = io.BytesIO()
    p = canvas.Canvas(buffer, pagesize=letter)
    p.setFont("Helvetica", 12)
    p.drawString(100, 750, f"Rapport d'analyse pour {document.name}")
    p.drawString(100, 730, f"Date de l'analyse : {document.upload_date}")

    if document.analysis_result:
        y = 700
        for key, value in document.analysis_result.items():
            p.drawString(100, y, f"{key.replace('_', ' ').capitalize()}:")
            p.drawString(300, y, f"Valeur : {value['value']} / Exigence : {value['requirement']}")
            compliance_text = "Conforme" if value['compliance'] else "Non conforme"
            p.drawString(500, y, compliance_text)
            y -= 20
    else:
        p.drawString(100, 700, "Aucun résultat d'analyse disponible.")

    p.showPage()
    p.save()

    buffer.seek(0)
    return buffer

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

def results(request):
    documents = Document.objects.all()
    return render(request, 'main/results.html', {'documents': documents})

def history(request):
    documents = Document.objects.all()
    return render(request, 'main/history.html', {'documents': documents})

def settings(request):
    return render(request, 'main/settings.html')

@csrf_exempt
@api_view(['GET', 'POST'])
def api_document_list(request):
    if request.method == 'GET':
        documents = Document.objects.all()
        serializer = DocumentSerializer(documents, many=True)
        return Response(serializer.data)
    elif request.method == 'POST':
        data = JSONParser().parse(request)
        serializer = DocumentSerializer(data=data)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

@csrf_exempt
@api_view(['GET'])
def api_document_detail(request, pk):
    try:
        document = Document.objects.get(pk=pk)
    except Document.DoesNotExist:
        return Response(status=status.HTTP_404_NOT_FOUND)

    if request.method == 'GET':
        serializer = DocumentSerializer(document)
        return Response(serializer.data)

@csrf_exempt
@api_view(['GET'])
def api_results(request):
    analyses = Analysis.objects.all()
    serializer = AnalysisSerializer(analyses, many=True)
    return Response(serializer.data)

@csrf_exempt
@api_view(['GET'])
def api_history(request):
    documents = Document.objects.all()
    serializer = DocumentSerializer(documents, many=True)
    return Response(serializer.data)

   
def delete_document(request, doc_id):
    if request.method == 'POST':
        document = get_object_or_404(Document, id=doc_id)
        document.delete()  # This deletes the document
        return redirect('history')  # Redirect to the history page or wherever appropriate
    return redirect('history')  # Handle case where someone navigates directly to the URL

def download_report(request, document_id):
    document = get_object_or_404(Document, id=document_id)
    buffer = io.BytesIO()
    p = canvas.Canvas(buffer, pagesize=letter)
    p.setFont("Helvetica", 12)

    # Document details
    p.drawString(100, 800, f"Rapport d'analyse pour {document.name}")
    p.drawString(100, 780, f"Date de l'analyse: {document.upload_date.strftime('%d %b %Y')}")

    # Document analysis results
    y = 760
    details = [
        ("Efficacité énergétique (RE2020)", document.re2020_energy_efficiency),
        ("Confort thermique (RE2020)", document.re2020_thermal_comfort),
        ("Émissions de carbone (RE2020)", document.re2020_carbon_emissions),
        ("Gestion de l'eau (RE2020)", document.re2020_water_management),
        ("Qualité de l'air intérieur (RE2020)", document.re2020_indoor_air_quality),
        # Add RT2012 details if needed
    ]

    for label, value in details:
        p.drawString(100, y, f"{label}: {value}")
        y -= 20

    p.showPage()
    p.save()
    buffer.seek(0)
    return FileResponse(buffer, as_attachment=True, filename=f"report_{document.name}.pdf")

def generate_report(document):
    buffer = io.BytesIO()
    p = canvas.Canvas(buffer, pagesize=letter)
    p.setFont("Helvetica", 12)

    p.drawString(100, 750, f"Rapport d'analyse pour {document.name}")
    p.drawString(100, 730, f"Date de l'analyse : {document.upload_date}")

    if document.analysis_result:
        y = 700
        for key, value in document.analysis_result.items():
            p.drawString(100, y, f"{key.replace('_', ' ').capitalize()}:")
            p.drawString(300, y, f"Valeur : {value['value']} / Exigence : {value['requirement']}")
            compliance_text = "Conforme" if value['compliance'] else "Non conforme"
            p.drawString(500, y, compliance_text)
            y -= 20
    else:
        p.drawString(100, 700, "Aucun résultat d'analyse disponible.")

    p.showPage()
    p.save()

    buffer.seek(0)
    return buffer

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

def results(request):
    documents = Document.objects.all()
    return render(request, 'main/results.html', {'documents': documents})

def history(request):
    documents = Document.objects.all()
    return render(request, 'main/history.html', {'documents': documents})

def settings(request):
    return render(request, 'main/settings.html')

@csrf_exempt
@api_view(['GET', 'POST'])
def api_document_list(request):
    if request.method == 'GET':
        documents = Document.objects.all()
        serializer = DocumentSerializer(documents, many=True)
        return Response(serializer.data)
    elif request.method == 'POST':
        data = JSONParser().parse(request)
        serializer = DocumentSerializer(data=data)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

@csrf_exempt
@api_view(['GET'])
def api_document_detail(request, pk):
    try:
        document = Document.objects.get(pk=pk)
    except Document.DoesNotExist:
        return Response(status=status.HTTP_404_NOT_FOUND)

    if request.method == 'GET':
        serializer = DocumentSerializer(document)
        return Response(serializer.data)

@csrf_exempt
@api_view(['GET'])
def api_results(request):
    analyses = Analysis.objects.all()
    serializer = AnalysisSerializer(analyses, many=True)
    return Response(serializer.data)

@csrf_exempt
@api_view(['GET'])
def api_history(request):
    documents = Document.objects.all()
    serializer = DocumentSerializer(documents, many=True)
    return Response(serializer.data)
