import logging

from django import forms
from django.core.exceptions import ValidationError

from .models import Division, ClassName, Order, Family, Genus, Species, Synonymy, Binnacle, CommonName


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
        model = ClassName
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
            'id_taxa', 'scientificName', 'scientificNameFull',
            'genus', 'specificEpithet', 'scientificNameAuthorship',
            'subespecie', 'autoresSsp',
            'variedad', 'autoresVariedad',
            'forma', 'autoresForma',
            'enArgentina', 'enBolivia', 'enPeru',
            'plant_habit', 'env_habit', 'cycle', 'status',
            'alturaMinima', 'alturaMaxima',
            'synonymys', 'common_names', 'region',
            'notas', 'publicacion', 'volumen', 'paginas',
            'id_tipo',
            'conservation_state', 'determined', 'id_mma',
        )

        labels = {
            'genus': 'Género',
            'specificEpithet': 'Epíteto específico',
            'scientificNameAuthorship': 'Autor(es)',
            'subespecie': 'Subespecie',
            'autoresSsp': 'Autor(es) subespecie',
            'variedad': 'Variedad',
            'autoresVariedad': 'Autor(es) variedad',
            'forma': 'Forma',
            'autoresForma': 'Autor(es) forma',
            'plant_habit': 'Hábito',
            'env_habit': 'Forma de vida',
            'cycle': 'Ciclo de vida',
            'status': 'Origen',
            'enArgentina': 'En Argentica',
            'enBolivia': 'En Bolivia',
            'enPeru': 'En Perú',
            'alturaMaxima': 'Altura Máxima',
            'alturaMinima': 'Altura Mínima',
            'notas': 'Notas',
            'publicacion': 'Publicación',
            'volumen': 'Volumen',
            'paginas': 'Páginas',
            'id_tipo': 'ID Tipo',
            'common_names': 'Nombres Comunes',
            'synonymys': 'Sinónimos',
            'region': 'Distribución Regional',
            'conservation_state': 'Estado de Conservación',
            'determined': '¿Terminal?',
            'id_mma': 'ID MMA',
        }

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

    def clean_genus(self):
        genus = self.cleaned_data["genus"]
        if genus is None:
            raise ValidationError("Género es requerido")
        return genus

    def clean_specificEpithet(self):
        specific_epithet = self.cleaned_data["specificEpithet"]
        if specific_epithet is None:
            raise ValidationError("Epíteto es requerido")
        return specific_epithet

    def clean_autoresSsp(self):
        subspecies_authors = self.cleaned_data["autoresSsp"]
        if "specificEpithet" in self.cleaned_data:
            specific_epithet = self.cleaned_data["specificEpithet"]
        else:
            return subspecies_authors
        subspecies = self.cleaned_data["subespecie"]
        if subspecies is not None and subspecies_authors is None and not (
                specific_epithet == subspecies
        ):
            raise ValidationError("Completar autor(es) de subespecie")
        return subspecies_authors

    def clean_autoresVariedad(self):
        variety_authors = self.cleaned_data["autoresVariedad"]
        if "specificEpithet" in self.cleaned_data:
            specific_epithet = self.cleaned_data["specificEpithet"]
        else:
            return variety_authors
        subspecies = self.cleaned_data["subespecie"]
        variety = self.cleaned_data["variedad"]
        if variety is not None and variety_authors is None and not (
                specific_epithet == variety or subspecies == variety
        ):
            raise ValidationError("Completar autor(es) de variedad")
        return variety_authors

    def clean_autoresForma(self):
        form_authors = self.cleaned_data["autoresForma"]
        if "specificEpithet" in self.cleaned_data:
            specific_epithet = self.cleaned_data["specificEpithet"]
        else:
            return form_authors
        subspecies = self.cleaned_data["subespecie"]
        variety = self.cleaned_data["variedad"]
        form = self.cleaned_data["forma"]
        if form is not None and form_authors is None and not (
                specific_epithet == form or subspecies == form or variety == form
        ):
            raise ValidationError("Completar autor(es) de forma")
        return form_authors


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
