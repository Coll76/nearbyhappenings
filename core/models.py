from django.db import models

# Create a new file: core/models.py (or add to an existing appropriate app)

from django.db import models
from django.conf import settings

class SiteSetting(models.Model):
    """Global site settings controllable by superadmin"""
    
    # Service fee settings
    service_fee_enabled = models.BooleanField(default=False)
    service_fee_percentage = models.DecimalField(
        max_digits=5, decimal_places=2, default=15.00,
        help_text="Percentage of ticket price charged as service fee"
    )
    
    # Reserved for future settings
    site_name = models.CharField(max_length=100, default="Nearby Happenings")
    contact_email = models.EmailField(default="support@nearbyhappenings.com")
    
    # Add other global settings as needed
    
    class Meta:
        verbose_name = "Site Setting"
        verbose_name_plural = "Site Settings"
    
    @classmethod
    def get_settings(cls):
        """Get or create site settings"""
        settings, created = cls.objects.get_or_create(pk=1)
        return settings
