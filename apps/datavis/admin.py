from django.contrib import admin
from django.contrib.admin import ModelAdmin
from .models import DataVisualization

@admin.register(DataVisualization)
class DataVisualizationAdmin(ModelAdmin):
    list_display = (['id', 'name', 'data'])

