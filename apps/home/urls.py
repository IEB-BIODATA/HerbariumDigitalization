# -*- coding: utf-8 -*-

from . import views
from django.urls import re_path

urlpatterns = [
    re_path(r'^$', views.index, name='index'),
    re_path(r'^preference/$', views.preference, name='preference'),
    re_path(r'^get_progress/(?P<task_id>[\w-]+)/$', views.get_progress, name='get_progress'),
    re_path(r'^get_task_log/(?P<task_id>[\w-]+)/$', views.get_task_log, name='get_task_log'),
    re_path(r'^test/$', views.test_view, name='test_view'),
    re_path(r'^generate_dwc_catalog/$', views.generate_dwc_catalog, name='generate_dwc_catalog'),
    re_path(r'^download_dwc_archive/$', views.download_dwc_archive, name='download_dwc_archive'),
    re_path(r'^download_dwc_catalog/$', views.download_dwc_catalog, name='download_dwc_catalog'),
]
