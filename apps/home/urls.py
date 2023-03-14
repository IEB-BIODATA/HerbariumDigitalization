# -*- coding: utf-8 -*-

from . import views
from django.urls import re_path

urlpatterns = [
    re_path(r'^$', views.index, name='index'),
]
