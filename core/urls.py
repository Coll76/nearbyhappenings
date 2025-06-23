# In core/urls.py

from django.urls import path
from .views import SiteSettingsView

urlpatterns = [
    path('settings/', SiteSettingsView.as_view(), name='site-settings'),
]
