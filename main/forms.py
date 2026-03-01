from django import forms
from .models import Document


class DocumentForm(forms.ModelForm):
    class Meta:
        model = Document
        fields = ['name', 'client_name', 'client_email', 'upload']
        labels = {
            'name': 'Nom du projet',
            'client_name': 'Votre nom',
            'client_email': 'Votre email',
            'upload': 'Document (PDF)',
        }
        widgets = {
            'name': forms.TextInput(attrs={'placeholder': 'Ex: Résidence Les Acacias — Lot B'}),
            'client_name': forms.TextInput(attrs={'placeholder': 'Jean Dupont'}),
            'client_email': forms.EmailInput(attrs={'placeholder': 'jean@cabinet.fr'}),
        }

    def clean_upload(self):
        upload = self.cleaned_data.get('upload')
        if upload:
            ext = upload.name.split('.')[-1].lower()
            if ext not in ['pdf']:
                raise forms.ValidationError("Seuls les fichiers PDF sont acceptés.")
            if upload.size > 20 * 1024 * 1024:  # 20MB
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
            ('architecte', 'Architecte / Bureau d\'études'),
            ('promoteur', 'Promoteur / Maître d\'ouvrage'),
            ('agent', 'Agent immobilier'),
            ('particulier', 'Particulier'),
            ('autre', 'Autre'),
        ]
    )
    message = forms.CharField(
        label="Message",
        widget=forms.Textarea(attrs={'placeholder': 'Décrivez votre projet…', 'rows': 4})
    )
