"""
Crée le superuser admin si il n'existe pas encore.
Appelé automatiquement au déploiement via les variables d'env :
  DJANGO_SUPERUSER_USERNAME
  DJANGO_SUPERUSER_PASSWORD
  DJANGO_SUPERUSER_EMAIL
"""
import os
from django.core.management.base import BaseCommand
from django.contrib.auth.models import User


class Command(BaseCommand):
    help = "Crée le superuser si il n'existe pas"

    def handle(self, *args, **kwargs):
        username = os.environ.get('DJANGO_SUPERUSER_USERNAME', 'admin')
        password = os.environ.get('DJANGO_SUPERUSER_PASSWORD')
        email    = os.environ.get('DJANGO_SUPERUSER_EMAIL', '')

        if not password:
            self.stdout.write(self.style.WARNING(
                'DJANGO_SUPERUSER_PASSWORD non défini — superuser non créé.'
            ))
            return

        if User.objects.filter(username=username).exists():
            self.stdout.write(f'Superuser "{username}" existe déjà.')
            return

        User.objects.create_superuser(username=username, password=password, email=email)
        self.stdout.write(self.style.SUCCESS(f'Superuser "{username}" créé.'))
