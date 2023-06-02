from django import forms
from .models import Division, Class_name, Order, Family, Genus, Species, Synonymy, Binnacle, CommonName


class DivisionForm(forms.ModelForm):
    class Meta:
        model = Division
        fields = (
            'name',
            'kingdom',
        )

        widgets = {
            'name': forms.TextInput(attrs={'required': True, 'class': "form-control"}),
            'kingdom': forms.Select(attrs={'required': True, 'class': "form-control"}),
        }


class ClassForm(forms.ModelForm):
    class Meta:
        model = Class_name
        fields = (
            'name',
            'division',
        )

        widgets = {
            'name': forms.TextInput(attrs={'required': True, 'class': "form-control"}),
            'division': forms.Select(attrs={'required': True, 'class': "form-control"}),
        }


class OrderForm(forms.ModelForm):
    class Meta:
        model = Order
        fields = (
            'name',
            'class_name',
        )

        widgets = {
            'name': forms.TextInput(attrs={'required': True, 'class': "form-control"}),
            'class_name': forms.Select(attrs={'required': True, 'class': "form-control"}),
        }


class FamilyForm(forms.ModelForm):
    class Meta:
        model = Family
        fields = (
            'name',
            'order',
        )

        widgets = {
            'name': forms.TextInput(attrs={'required': True, 'class': "form-control"}),
            'order': forms.Select(attrs={'required': True, 'class': "form-control"}),
        }


class GenusForm(forms.ModelForm):
    class Meta:
        model = Genus
        fields = (
            'name',
            'family',
        )

        widgets = {
            'name': forms.TextInput(attrs={'required': True, 'class': "form-control"}),
            'family': forms.Select(attrs={'required': True, 'class': "form-control"}),
        }


class BinnacleForm(forms.ModelForm):
    class Meta:
        model = Binnacle
        fields = (
            'type_update',
            'model',
            'description',
            'note',
        )

        widgets = {
            'type_update': forms.TextInput(attrs={'required': True, 'class': "form-control", 'readonly': 'true'}),
            'model': forms.TextInput(attrs={'required': True, 'class': "form-control", 'readonly': 'true'}),
            'description': forms.TextInput(attrs={'required': True, 'class': "form-control", 'readonly': 'true'}),
            'note': forms.TextInput(attrs={'required': True, 'class': "form-control"}),
        }


class SpeciesForm(forms.ModelForm):
    class Meta:
        model = Species
        fields = (
            'id_taxa',
            'genus',
            'scientificName',
            'scientificNameFull',
            'specificEpithet',
            'scientificNameAuthorship',
            'subespecie',
            'autoresSsp',
            'variedad',
            'autoresVariedad',
            'forma',
            'autoresForma',
            'enArgentina',
            'enBolivia',
            'enPeru',
            'plant_habit',
            'env_habit',
            'cycle',
            'status',
            'alturaMinima',
            'alturaMaxima',
            'synonymys',
            'common_names',
            'region',
            'notas',
            'publicacion',
            'volumen',
            'paginas',
            'id_tipo',
            'conservation_state',
            'determined',
            'id_mma',
        )

        widgets = {
            'id_taxa': forms.HiddenInput(),
            'genus': forms.Select(attrs={'class': "form-control"}),
            'scientificName': forms.HiddenInput(),
            'scientificNameFull': forms.HiddenInput(),
            'scientificNameDB': forms.HiddenInput(),
            'specificEpithet': forms.TextInput(attrs={'class': "form-control"}),
            'scientificNameAuthorship': forms.TextInput(attrs={'class': "form-control"}),
            'subespecie': forms.TextInput(attrs={'class': "form-control"}),
            'autoresSsp': forms.TextInput(attrs={'class': "form-control"}),
            'variedad': forms.TextInput(attrs={'class': "form-control"}),
            'autoresVariedad': forms.TextInput(attrs={'class': "form-control"}),
            'forma': forms.TextInput(attrs={'class': "form-control"}),
            'autoresForma': forms.TextInput(attrs={'class': "form-control"}),
            'enArgentina': forms.CheckboxInput(attrs={'class': "form-check-input"}),
            'enBolivia': forms.CheckboxInput(attrs={'class': "form-check-input"}),
            'enPeru': forms.CheckboxInput(attrs={'class': "form-check-input"}),
            'plant_habit': forms.SelectMultiple(
                attrs={'class': "selectpicker", 'multiple data-live-search': 'true',
                       'multiple data-multiple-separator': ' o '}),
            'env_habit': forms.SelectMultiple(
                attrs={'class': "selectpicker", 'multiple data-live-search': 'true',
                       'multiple data-multiple-separator': ' o '}),
            'cycle': forms.SelectMultiple(
                attrs={'class': "selectpicker", 'multiple data-live-search': 'true',
                       'multiple data-multiple-separator': ' o '}),
            'status': forms.Select(attrs={'class': "form-control"}),
            'alturaMinima': forms.TextInput(attrs={'class': "form-control", 'type': 'number'}),
            'alturaMaxima': forms.TextInput(attrs={'class': "form-control", 'type': 'number'}),
            'synonymys': forms.SelectMultiple(attrs={'class': "selectpicker", 'multiple data-live-search': 'true',
                                                     'multiple data-multiple-separator': ','}),
            'common_names': forms.SelectMultiple(attrs={'class': "selectpicker", 'multiple data-live-search': 'true',
                                                        'multiple data-multiple-separator': ','}),
            'region': forms.SelectMultiple(
                attrs={'class': "selectpicker", 'multiple data-live-search': 'true',
                       'multiple data-multiple-separator': ','}),
            'notas': forms.Textarea(attrs={'class': "form-control", 'rows': 3, 'cols': 5}),
            'publicacion': forms.TextInput(attrs={'class': "form-control"}),
            'volumen': forms.TextInput(attrs={'class': "form-control"}),
            'paginas': forms.TextInput(attrs={'class': "form-control"}),
            'id_tipo': forms.TextInput(attrs={'class': "form-control"}),
            'conservation_state': forms.SelectMultiple(
                attrs={'class': "selectpicker", 'multiple data-live-search': 'true',
                       'multiple data-multiple-separator': ','}),
            'determined': forms.CheckboxInput(attrs={'class': "form-check-input"}),
            'id_mma': forms.TextInput(attrs={'class': "form-control"}),
        }


class SynonymyForm(forms.ModelForm):
    class Meta:
        model = Synonymy
        fields = (
            'scientificName',
            'scientificNameFull',
            'scientificNameDB',
            'genus',
            'specificEpithet',
            'scientificNameAuthorship',
            'subespecie',
            'autoresSsp',
            'variedad',
            'autoresVariedad',
            'forma',
            'autoresForma',
        )

        widgets = {
            'scientificName': forms.HiddenInput(),
            'scientificNameFull': forms.HiddenInput(),
            'scientificNameDB': forms.HiddenInput(),
            'genus': forms.TextInput(attrs={'class': "form-control"}),
            'specificEpithet': forms.TextInput(attrs={'class': "form-control"}),
            'scientificNameAuthorship': forms.TextInput(attrs={'class': "form-control"}),
            'subespecie': forms.TextInput(attrs={'class': "form-control"}),
            'autoresSsp': forms.TextInput(attrs={'class': "form-control"}),
            'variedad': forms.TextInput(attrs={'class': "form-control"}),
            'autoresVariedad': forms.TextInput(attrs={'class': "form-control"}),
            'forma': forms.TextInput(attrs={'class': "form-control"}),
            'autoresForma': forms.TextInput(attrs={'class': "form-control"}),
        }


class CommonNameForm(forms.ModelForm):
    class Meta:
        model = CommonName
        fields = (
            'name',
        )

        widgets = {
            'name': forms.TextInput(attrs={'required': True, 'class': "form-control"}),
        }
