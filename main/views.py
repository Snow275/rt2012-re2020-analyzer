from django.shortcuts import render, redirect, get_object_or_404
from django.http import HttpResponse, FileResponse
from django.contrib import messages
from django.views.decorators.csrf import csrf_exempt

from rest_framework.decorators import api_view
from rest_framework.response import Response
from rest_framework import status

from .models import Document
from .forms import DocumentForm, ContactForm
from .serializers import DocumentSerializer, AnalysisSerializer

import io
import csv
import chardet
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas


# =========================
# PAGES CLASSIQUES
# =========================

def home(request):
    documents = Document.objects.all()
    return render(request, 'main/home.html', {'documents': documents})


def contact(request):
    if request.method == 'POST':
        form = ContactForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, 'Contact info successfully saved.')
            return redirect('home')
    else:
        form = ContactForm()

    return render(request, 'main/contact.html', {'form': form})


def faq(request):
    return render(request, 'main/faq.html')


# =========================
# IMPORT + ANALYSE
# =========================

def import_document(request):
    if request.method == 'POST':
        form = DocumentForm(request.POST, request.FILES)
        if form.is_valid():
            document = form.save()

            data = read_document(document.upload.path)

            if data:
                analyze_document(document, data)
                messages.success(request, "Document analysé avec succès.")
                return redirect('results')
            else:
                messages.error(request, "Aucune donnée valide trouvée.")

        else:
            messages.error(request, "Formulaire invalide.")
    else:
        form = DocumentForm()

    return render(request, 'main/import.html', {'form': form})


def analyze_document(document, data):

    # RE2020
    document.re2020_energy_efficiency = data.get('energy_efficiency', 0.0)
    document.re2020_thermal_comfort = data.get('thermal_comfort', 0.0)
    document.re2020_carbon_emissions = data.get('carbon_emissions', 0.0)
    document.re2020_water_management = data.get('water_management', 0.0)
    document.re2020_indoor_air_quality = data.get('indoor_air_quality', 0.0)

    # RT2012
    document.rt2012_energy_efficiency = data.get('energy_efficiency', 0.0)
    document.rt2012_thermal_comfort = data.get('thermal_comfort', 0.0)
    document.rt2012_carbon_emissions = data.get('carbon_emissions', 0.0)
    document.rt2012_water_management = data.get('water_management', 0.0)
    document.rt2012_indoor_air_quality = data.get('indoor_air_quality', 0.0)

    document.save()


# =========================
# VALEURS RÉGLEMENTAIRES
# =========================

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


# =========================
# PAGE RÉSULTATS
# =========================

def results(request):
    documents = Document.objects.all()

    re2020_requirements = fetch_re2020_requirements()
    rt2012_requirements = fetch_rt2012_requirements()

    return render(request, 'main/results.html', {
        'documents': documents,
        're2020_requirements': re2020_requirements,
        'rt2012_requirements': rt2012_requirements,
    })


# =========================
# LECTURE CSV
# =========================

def read_document(upload_path):
    try:
        with open(upload_path, 'rb') as file:
            raw_data = file.read()
            encoding = chardet.detect(raw_data)['encoding']

        with open(upload_path, 'r', encoding=encoding) as file:
            reader = csv.DictReader(file)

            for row in reader:
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


# =========================
# HISTORIQUE
# =========================

def history(request):
    documents = Document.objects.all()
    return render(request, 'main/history.html', {'documents': documents})


def delete_document(request, doc_id):
    if request.method == 'POST':
        document = get_object_or_404(Document, id=doc_id)
        document.delete()
    return redirect('history')


# =========================
# PDF REPORT
# =========================

def download_report(request, document_id):
    document = get_object_or_404(Document, id=document_id)

    buffer = io.BytesIO()
    p = canvas.Canvas(buffer, pagesize=letter)
    p.setFont("Helvetica", 12)

    p.drawString(100, 800, f"Rapport d'analyse pour {document.name}")
    p.drawString(100, 780, f"Date : {document.upload_date.strftime('%d %b %Y')}")

    y = 750

    details = [
        ("RE2020 - Efficacité énergétique", document.re2020_energy_efficiency),
        ("RE2020 - Confort thermique", document.re2020_thermal_comfort),
        ("RE2020 - Émissions carbone", document.re2020_carbon_emissions),
        ("RT2012 - Efficacité énergétique", document.rt2012_energy_efficiency),
        ("RT2012 - Confort thermique", document.rt2012_thermal_comfort),
    ]

    for label, value in details:
        p.drawString(100, y, f"{label} : {value}")
        y -= 20

    p.showPage()
    p.save()

    buffer.seek(0)
    return FileResponse(buffer, as_attachment=True, filename=f"report_{document.name}.pdf")


# =========================
# API
# =========================

@csrf_exempt
@api_view(['GET'])
def api_document_list(request):
    documents = Document.objects.all()
    serializer = DocumentSerializer(documents, many=True)
    return Response(serializer.data)


@csrf_exempt
@api_view(['GET'])
def api_document_detail(request, pk):
    try:
        document = Document.objects.get(pk=pk)
    except Document.DoesNotExist:
        return Response(status=status.HTTP_404_NOT_FOUND)

    serializer = DocumentSerializer(document)
    return Response(serializer.data)
