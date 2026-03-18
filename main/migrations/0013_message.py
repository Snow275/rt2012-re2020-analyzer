from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('main', '0012_sync_state'),
    ]

    operations = [
        migrations.CreateModel(
            name='Message',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('auteur', models.CharField(choices=[('admin', 'ConformExpert'), ('client', 'Client')], default='admin', max_length=10)),
                ('contenu', models.TextField()),
                ('fichier', models.FileField(blank=True, null=True, upload_to='messages/')),
                ('fichier_nom', models.CharField(blank=True, default='', max_length=255)),
                ('lu_admin', models.BooleanField(default=False)),
                ('lu_client', models.BooleanField(default=False)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('document', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='messages', to='main.document')),
            ],
            options={
                'verbose_name': 'Message',
                'verbose_name_plural': 'Messages',
                'ordering': ['created_at'],
            },
        ),
    ]
