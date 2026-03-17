from django.db import migrations, models, models


class Migration(migrations.Migration):

    dependencies = [
        ('main', '0009_add_dpe_extraction_fields'),
    ]

    operations = [
        migrations.CreateModel(
            name='SiteSettings',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('maintenance_mode', models.BooleanField(
                    default=False,
                    verbose_name='Mode maintenance',
                    help_text='Activer pour afficher la page de maintenance à tous les visiteurs (sauf admins).',
                )),
                ('maintenance_message', models.TextField(
                    blank=True,
                    default='Nous effectuons des mises à jour pour améliorer votre expérience. Nous serons de retour très bientôt.',
                    verbose_name='Message affiché',
                )),
                ('maintenance_title', models.CharField(
                    max_length=200,
                    blank=True,
                    default='Site en maintenance',
                    verbose_name='Titre affiché',
                )),
            ],
            options={
                'verbose_name': 'Paramètres du site',
                'verbose_name_plural': 'Paramètres du site',
            },
        ),
    ]
