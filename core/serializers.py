# In core/serializers.py

from rest_framework import serializers
from .models import SiteSetting

class SiteSettingSerializer(serializers.ModelSerializer):
    class Meta:
        model = SiteSetting
        fields = ['service_fee_enabled', 'service_fee_percentage', 'site_name', 'contact_email']
