from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('main', '0013_message'),
    ]

    operations = [
        migrations.CreateModel(
            name='Avis',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('token', models.CharField(editable=False, max_length=64, unique=True)),
                ('note', models.PositiveSmallIntegerField(
                    blank=True,
                    null=True,
                    choices=[
                        (1, '1 étoile'),
                        (2, '2 étoiles'),
                        (3, '3 étoiles'),
                        (4, '4 étoiles'),
                        (5, '5 étoiles'),
                    ],
                )),
                ('commentaire', models.TextField(blank=True, default='')),
                ('client_nom', models.CharField(blank=True, default='', max_length=255)),
                ('certifie', models.BooleanField(default=False)),
                ('email_envoye', models.BooleanField(default=False)),
                ('soumis_le', models.DateTimeField(blank=True, null=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('document', models.OneToOneField(
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name='avis',
                    to='main.document',
                )),
            ],
            options={
                'verbose_name': 'Avis client',
                'verbose_name_plural': 'Avis clients',
                'ordering': ['-soumis_le'],
            },
        ),
    ]
