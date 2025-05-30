"""intranet URL Configuration

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/4.1/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.conf.urls import include
from django.urls import re_path
from drf_spectacular.views import SpectacularAPIView, SpectacularSwaggerView, SpectacularRedocView

urlpatterns = [
    re_path(r'^', include('apps.api.urls'),),
    re_path(r'^schema/$', SpectacularAPIView.as_view(), name='schema'),
    # Optional UI:
    re_path(r'^swagger-ui/', SpectacularSwaggerView.as_view(url_name='schema'), name='swagger-ui'),
    re_path(r'^redoc/', SpectacularRedocView.as_view(url_name='schema'), name='redoc'),
]
