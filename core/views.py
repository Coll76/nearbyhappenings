from django.shortcuts import render
# In core/views.py

from rest_framework import generics, permissions
from rest_framework.response import Response
from .models import SiteSetting
from .serializers import SiteSettingSerializer

class IsSuperUser(permissions.BasePermission):
    """Permission to only allow superusers"""
    def has_permission(self, request, view):
        return request.user.is_authenticated and request.user.is_superuser

class SiteSettingsView(generics.RetrieveUpdateAPIView):
    queryset = SiteSetting.objects.all()
    serializer_class = SiteSettingSerializer
    permission_classes = [IsSuperUser]
    
    def get_object(self):
        return SiteSetting.get_settings()
