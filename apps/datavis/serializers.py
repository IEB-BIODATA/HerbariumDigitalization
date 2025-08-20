from rest_framework import serializers
from .models import DataVisualization

class DataVisualizationSerializer(serializers.ModelSerializer):
    class Meta:
        model = DataVisualization
        fields = ['id', 'name', 'data', 'updated_at']
