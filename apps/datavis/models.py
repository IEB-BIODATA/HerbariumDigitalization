from django.db import models

class DataVisualization(models.Model):
    name = models.SlugField(max_length=500, unique=True)
    data = models.JSONField(default=dict, blank=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.name