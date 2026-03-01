from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('main', '0001_initial'),
    ]

    operations = [
        migrations.CreateModel(
            name='Devis',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('client_nom', models.CharField(max_length=255)),
                ('client_email', models.EmailField(max_length=254)),
                ('client_phone', models.CharField(blank=True, default='', max_length=30)),
                ('projet_nom', models.CharField(blank=True, default='', max_length=255)),
                ('type_batiment', models.CharField(choices=[('maison', 'Maison individuelle'), ('collectif', 'Logement collectif'), ('tertiaire', 'Bâtiment tertiaire'), ('autre', 'Autre')], default='maison', max_length=20)),
                ('norme', models.CharField(choices=[('RT2012', 'RT2012'), ('RE2020', 'RE2020'), ('Les deux', 'Les deux')], default='RE2020', max_length=20)),
                ('montant', models.DecimalField(blank=True, decimal_places=2, max_digits=8, null=True)),
                ('statut', models.CharField(choices=[('en_attente', 'En attente'), ('accepte', 'Accepté'), ('refuse', 'Refusé'), ('facture', 'Facturé')], default='en_attente', max_length=20)),
                ('notes', models.TextField(blank=True, default='')),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('document', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='devis', to='main.document')),
            ],
            options={
                'verbose_name': 'Devis',
                'verbose_name_plural': 'Devis',
                'ordering': ['-created_at'],
            },
        ),
    ]
