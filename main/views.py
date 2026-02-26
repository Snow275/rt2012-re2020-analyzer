from django.shortcuts import render, redirect, get_object_or_404
from django.http import HttpResponse, FileResponse, JsonResponse
from .models import Document
from .forms import DocumentForm, ContactForm
from rest_framework.decorators import api_view
from rest_framework.response import Response
from rest_framework import status
from .serializers import DocumentSerializer, AnalysisSerializer
from django.views.decorators.csrf import csrf_exempt
from django.contrib import messages
import csv
import chardet
import PyPDF2
import re
from .pdf_utils import generate_report


def extract_text_from_pdf(upload_path):

    text = ""

    with open(upload_path, "rb") as file:
        reader = PyPDF2.PdfReader(file)
        for page in reader.pages:
            extracted = page.extract_text()
            if extracted:
                text += extracted

    return text

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
    if request.method == "POST":
        form = DocumentForm(request.POST, request.FILES)
        if form.is_valid():
            document = form.save()

            upload_path = document.upload.path

            text = extract_text_from_pdf(upload_path)
            data = parse_pdf_text(text)

            analyze_document(document, data)

            return redirect("results")
    else:
        form = DocumentForm()

    return render(request, "main/import.html", {"form": form})
    

def parse_pdf_text(text):
    data = {}

    # Séparer les sections
    re2020_section = ""
    rt2012_section = ""

    if "RE2020" in text and "RT2012" in text:
        re2020_section = text.split("RE2020")[1].split("RT2012")[0]
        rt2012_section = text.split("RT2012")[1]

    # ----- RE2020 -----
    cep = re.search(r'Cep\s*=\s*(\d+)', re2020_section)
    if cep:
        data['energy_efficiency'] = float(cep.group(1))

    dh = re.search(r'DH\s*=\s*(\d+)', re2020_section)
    if dh:
        data['thermal_comfort'] = float(dh.group(1))

    ic = re.search(r'Ic energie\s*=\s*(\d+)', re2020_section)
    if ic:
        data['carbon_emissions'] = float(ic.group(1))

    eau = re.search(r'Eau\s*=\s*(\d+)', re2020_section)
    if eau:
        data['water_management'] = float(eau.group(1))

    qai = re.search(r'Qai\s*=\s*(\d+)', re2020_section)
    if qai:
        data['indoor_air_quality'] = float(qai.group(1))

    # ----- RT2012 -----
    bbio = re.search(r'Bbio\s*=\s*(\d+)', rt2012_section)
    if bbio:
        data['bbio'] = float(bbio.group(1))

    cep_rt = re.search(r'Cep\s*=\s*(\d+)', rt2012_section)
    if cep_rt:
        data['cep_rt'] = float(cep_rt.group(1))

    tic = re.search(r'Tic\s*=\s*(\d+)', rt2012_section)
    if tic:
        data['tic'] = float(tic.group(1))

    airtightness = re.search(r'Etancheite\s*=\s*([\d\.]+)', rt2012_section)
    if airtightness:
        data['airtightness'] = float(airtightness.group(1))

    enr = re.search(r'Enr\s*=\s*([\d\.]+)', rt2012_section)
    if enr:
        data['enr'] = float(enr.group(1))

    return data
    

def analyze_document(document, data):
    
    document.re2020_energy_efficiency = data.get('energy_efficiency', 0.0)
    document.re2020_thermal_comfort = data.get('thermal_comfort', 0.0)
    document.re2020_carbon_emissions = data.get('carbon_emissions', 0.0)
    document.re2020_water_management = data.get('water_management', 0.0)
    document.re2020_indoor_air_quality = data.get('indoor_air_quality', 0.0)

    document.rt2012_bbio = data.get('bbio', 0.0)
    document.rt2012_cep = data.get('cep_rt', 0.0)
    document.rt2012_tic = data.get('tic', 0.0)
    document.rt2012_airtightness = data.get('airtightness', 0.0)
    document.rt2012_enr = data.get('enr', 0.0)

    document.save()


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


def results(request):
    documents = Document.objects.all()
    return render(request, 'main/results.html', {
        'documents': documents,
        're2020_requirements': fetch_re2020_requirements(),
        'rt2012_requirements': fetch_rt2012_requirements(),
    })


def read_document(upload_path):
    try:
        with open(upload_path, 'rb') as file:
            raw_data = file.read()
            encoding = chardet.detect(raw_data)['encoding']
        
        with open(upload_path, 'r', encoding=encoding) as file:
            reader = csv.DictReader(file)
            for row in reader:
                # On mappe les colonnes du CSV vers les clés attendues par analyze_document
                return {
                    'energy_efficiency': float(row.get('Efficacité énergétique', 0).replace(',', '.')),
                    'thermal_comfort': float(row.get('Confort thermique', 0).replace(',', '.')),
                    'carbon_emissions': float(row.get('Émissions de carbone', 0).replace(',', '.')),
                    'water_management': float(row.get("Gestion de l'eau", 0).replace(',', '.')),
                    'indoor_air_quality': float(row.get("Qualité de l'air intérieur", 0).replace(',', '.')),
                }
        return {}
    except Exception as e:
        print("Erreur lecture fichier:", e)
        return {}


def update_re2020(request):
    if request.method == 'POST':
        messages.success(request, 'Les paramètres RE2020 ont été mis à jour avec succès.')
    else:
        messages.error(request, 'Méthode de requête invalide.')
    return redirect('settings')


def delete_document(request, doc_id):
    if request.method == 'POST':
        document = get_object_or_404(Document, id=doc_id)
        document.delete()
    return redirect('history')


def download_report(request, document_id):
    document = get_object_or_404(Document, id=document_id)
    file_path = generate_report(document)
    return FileResponse(open(file_path, 'rb'), as_attachment=True, filename=f"report_{document.name}.pdf")


@csrf_exempt
@api_view(['GET'])
def api_report(request, pk):
    try:
        document = Document.objects.get(pk=pk)
        file_path = generate_report(document)
        response = HttpResponse(open(file_path, 'rb'), content_type='application/pdf')
        response['Content-Disposition'] = f'attachment; filename="report_{document.name}.pdf"'
        return response
    except Document.DoesNotExist:
        return Response(status=status.HTTP_404_NOT_FOUND)


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
        serializer = DocumentSerializer(data=request.data)
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
    documents = Document.objects.all()
    serializer = DocumentSerializer(documents, many=True)
    return Response(serializer.data)
