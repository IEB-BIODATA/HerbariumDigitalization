# -*- coding: utf-8 -*-

from . import views
from django.urls import re_path

urlpatterns = [
    re_path(r'^$', views.index, name='index'),
    re_path(r'^test/$', views.test_view, name='test_view'),
]
