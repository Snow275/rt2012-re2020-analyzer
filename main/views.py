from django.shortcuts import render, redirect, get_object_or_404
from django.http import HttpResponse, FileResponse
from django.contrib import messages
from django.views.decorators.csrf import csrf_exempt
from rest_framework.decorators import api_view
from rest_framework.response import Response
from rest_framework import status
from .models import Document
from .forms import DocumentForm, ContactForm
from .serializers import DocumentSerializer
import io
import csv
import chardet
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas


# =========================
# REGULATION REQUIREMENTS
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
# BASIC PAGES
# =========================

def home(request):
    documents = Document.objects.all()
    return render(request, 'main/home.html', {'documents': documents})


def contact(request):
    if request.method == 'POST':
        form = ContactForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, "Contact saved successfully.")
            return redirect('home')
    else:
        form = ContactForm()

    return render(request, 'main/contact.html', {'form': form})


def faq(request):
    return render(request, 'main/faq.html')


# =========================
# DOCUMENT IMPORT
# =========================

def import_document(request):
    if request.method == 'POST':
        form = DocumentForm(request.POST, request.FILES)

        if form.is_valid():
            document = form.save()

            data = read_document(document.upload.path)

            if data:
                analyze_document(document, data)
                messages.success(request, "Document analyzed successfully.")
                return redirect('results')
            else:
                messages.error(request, "No valid data found in file.")

    else:
        form = DocumentForm()

    return render(request, 'main/import.html', {'form': form})


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
        print("File read error:", e)
        return {}


def analyze_document(document, data):

    # Save document values
    document.re2020_energy_efficiency = data['energy_efficiency']
    document.re2020_thermal_comfort = data['thermal_comfort']
    document.re2020_carbon_emissions = data['carbon_emissions']
    document.re2020_water_management = data['water_management']
    document.re2020_indoor_air_quality = data['indoor_air_quality']

    document.rt2012_energy_efficiency = data['energy_efficiency']
    document.rt2012_thermal_comfort = data['thermal_comfort']
    document.rt2012_carbon_emissions = data['carbon_emissions']
    document.rt2012_water_management = data['water_management']
    document.rt2012_indoor_air_quality = data['indoor_air_quality']

    document.save()


# =========================
# RESULTS PAGE
# =========================

def results(request):
    documents = Document.objects.all()

    return render(request, 'main/results.html', {
        'documents': documents,
        're2020': fetch_re2020_requirements(),
        'rt2012': fetch_rt2012_requirements(),
    })


def history(request):
    documents = Document.objects.all()
    return render(request, 'main/history.html', {'documents': documents})


def settings(request):
    return render(request, 'main/settings.html')


# =========================
# PDF REPORT
# =========================

def download_report(request, document_id):
    document = get_object_or_404(Document, id=document_id)

    buffer = io.BytesIO()
    p = canvas.Canvas(buffer, pagesize=letter)
    p.setFont("Helvetica", 12)

    p.drawString(100, 800, f"Analysis Report for {document.name}")
    p.drawString(100, 780, f"Date: {document.upload_date}")

    y = 750

    details = [
        ("RE2020 Energy Efficiency", document.re2020_energy_efficiency),
        ("RE2020 Thermal Comfort", document.re2020_thermal_comfort),
        ("RE2020 Carbon Emissions", document.re2020_carbon_emissions),
        ("RE2020 Water Management", document.re2020_water_management),
        ("RE2020 Indoor Air Quality", document.re2020_indoor_air_quality),
    ]

    for label, value in details:
        p.drawString(100, y, f"{label}: {value}")
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
        serializer = DocumentSerializer(document)
        return Response(serializer.data)
    except Document.DoesNotExist:
        return Response(status=status.HTTP_404_NOT_FOUND)
