from django.contrib import admin

# In core/admin.py

from django.contrib import admin
from .models import SiteSetting

@admin.register(SiteSetting)
class SiteSettingAdmin(admin.ModelAdmin):
    fieldsets = (
        ('Service Fee Settings', {
            'fields': ('service_fee_enabled', 'service_fee_percentage')
        }),
        ('General Settings', {
            'fields': ('site_name', 'contact_email')
        }),
    )
    
    def has_add_permission(self, request):
        # Prevent creating multiple settings objects
        return SiteSetting.objects.count() == 0
        
    def has_delete_permission(self, request, obj=None):
        # Prevent deleting the settings object
        return False
