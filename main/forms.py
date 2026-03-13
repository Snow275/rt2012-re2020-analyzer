from django import forms
from .models import Document


class DocumentForm(forms.ModelForm):

    # ── Zone climatique avec groupes par pays ─────────────────────────────────
    climate_zone = forms.ChoiceField(
        label='Zone climatique',
        choices=[
            ('', 'Sélectionner…'),
            ('🇫🇷 France', (
                ('H1', 'H1 — Nord / altitude (climat froid)'),
                ('H2', 'H2 — Centre / Ouest (climat tempéré)'),
                ('H3', 'H3 — Sud / littoral méditerranéen'),
            )),
            ('🇧🇪 Belgique', (
                ('BE-I',   'Zone I — Côtière (Ostende, Bruges)'),
                ('BE-II',  'Zone II — Centrale (Bruxelles, Liège)'),
                ('BE-III', 'Zone III — Ardennaise (altitude > 300 m)'),
            )),
            ('🇨🇭 Suisse', (
                ('CH-I',   'Zone I — Genève / Tessin (doux)'),
                ('CH-II',  'Zone II — Plateau (Berne, Zurich)'),
                ('CH-III', 'Zone III — Préalpes'),
                ('CH-IV',  'Zone IV — Alpes (altitude > 800 m)'),
                ('CH-V',   'Zone V — Haute montagne (> 1500 m)'),
                ('CH-VI',  'Zone VI — Très haute altitude (> 2000 m)'),
            )),
            ('🇨🇦 Canada', (
                ('CA-4', 'Zone 4 — Vancouver / Victoria (côte Pacifique)'),
                ('CA-5', 'Zone 5 — Toronto / Montréal'),
                ('CA-6', 'Zone 6 — Ottawa / Québec'),
                ('CA-7', 'Zone 7a — Winnipeg / Edmonton'),
                ('CA-7b','Zone 7b — Territoires du Nord'),
                ('CA-8', 'Zone 8 — Grand Nord / Territoires'),
            )),
            ('🇱🇺 Luxembourg', (
                ('LU-A', 'Zone A — Vallée de la Moselle (doux)'),
                ('LU-B', 'Zone B — Plateau central (Oesling)'),
            )),
        ]
    )

    # ── Norme applicable avec groupes par pays ────────────────────────────────
    norme = forms.ChoiceField(
        label='Norme applicable',
        choices=[
            ('', 'Sélectionner…'),
            ('🇫🇷 France', (
                ('RE2020', 'RE2020 — Réglementation Environnementale 2020'),
                ('RT2012', 'RT2012 — Réglementation Thermique 2012'),
            )),
            ('🇧🇪 Belgique', (
                ('PEB', 'PEB — Performance Énergétique des Bâtiments'),
            )),
            ('🇨🇭 Suisse', (
                ('MINERGIE', 'Minergie'),
                ('SIA380',   'SIA 380/1 — Besoin de chaleur'),
            )),
            ('🇨🇦 Canada', (
                ('CNEB2020', 'CNEB 2020 — Code National Énergie Bâtiments'),
                ('CNEB2015', 'CNEB 2015'),
            )),
            ('🇱🇺 Luxembourg', (
                ('LENOZ', 'LENOZ — Label énergétique'),
            )),
        ]
    )

    upload = forms.FileField(
        required=False,
        widget=forms.ClearableFileInput(attrs={'accept': '.pdf,.doc,.docx,.dwg,.xls,.xlsx'})
    )

    class Meta:
        model = Document
        fields = [
            'name',
            'client_name',
            'client_email',
            'building_type',
            'pays',
            'climate_zone',
            'norme',
            'surface_totale',
            'annee_construction',
            'nombre_logements',
            'upload'
        ]
        
        labels = {
            'name': 'Nom du projet',
            'client_name': 'Votre nom',
            'client_email': 'Votre email',
            'building_type': 'Type de bâtiment',
            'pays': 'Pays',
            'upload': 'Document principal',
        }
        widgets = {
            'name': forms.TextInput(attrs={'placeholder': 'Ex: Résidence Les Acacias — Lot B'}),
            'client_name': forms.TextInput(attrs={'placeholder': 'Jean Dupont'}),
            'client_email': forms.EmailInput(attrs={'placeholder': 'jean@cabinet.fr'}),
            'upload': forms.ClearableFileInput(attrs={'accept': '.pdf,.doc,.docx,.dwg,.xls,.xlsx'}),
        }

    def clean_upload(self):
        upload = self.cleaned_data.get('upload')
        if upload:
            ext = upload.name.split('.')[-1].lower()
            if ext not in ['pdf', 'doc', 'docx']:
                raise forms.ValidationError("Formats acceptés : PDF, Word (.doc, .docx).")
            if upload.size > 20 * 1024 * 1024:
                raise forms.ValidationError("Le fichier ne doit pas dépasser 20 Mo.")
        return upload


class ContactForm(forms.Form):
    name = forms.CharField(
        max_length=100,
        label="Nom complet",
        widget=forms.TextInput(attrs={'placeholder': 'Jean Dupont'})
    )
    email = forms.EmailField(
        label="Email",
        widget=forms.EmailInput(attrs={'placeholder': 'jean@cabinet.fr'})
    )
    phone = forms.CharField(
        max_length=20,
        required=False,
        label="Téléphone",
        widget=forms.TextInput(attrs={'placeholder': '06 12 34 56 78'})
    )
    profile = forms.ChoiceField(
        label="Profil",
        choices=[
            ('', 'Sélectionner…'),
            ('architecte', "Architecte / Bureau d'études"),
            ('promoteur', "Promoteur / Maître d'ouvrage"),
            ('agent', 'Agent immobilier'),
            ('particulier', 'Particulier'),
            ('autre', 'Autre'),
        ]
    )
    message = forms.CharField(
        label="Message",
        widget=forms.Textarea(attrs={'placeholder': 'Décrivez votre projet…', 'rows': 4})
    )
