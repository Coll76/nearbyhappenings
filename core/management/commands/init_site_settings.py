# In core/management/commands/init_site_settings.py

from django.core.management.base import BaseCommand
from core.models import SiteSetting

class Command(BaseCommand):
    help = 'Initialize site settings'

    def handle(self, *args, **options):
        settings, created = SiteSetting.objects.get_or_create(pk=1)
        
        if created:
            self.stdout.write(self.style.SUCCESS('Successfully created site settings'))
        else:
            self.stdout.write(self.style.SUCCESS('Site settings already exist'))
