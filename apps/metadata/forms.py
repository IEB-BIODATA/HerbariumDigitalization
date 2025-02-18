from django import forms

from apps.metadata.models import GeographicCoverage


class GeographicCoverageForm(forms.ModelForm):
    class Meta:
        model = GeographicCoverage
        fields = '__all__'
