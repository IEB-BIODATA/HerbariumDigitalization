from django import forms
from django.core.exceptions import ValidationError
from django.utils.translation import gettext_lazy as _

from .models import Division, ClassName, Order, Family, Genus, Species, Synonymy, Binnacle, CommonName


class DivisionForm(forms.ModelForm):
    class Meta:
        model = Division
        fields = (
            'name',
            'kingdom',
        )

        labels = {
            'name': _('Name'),
            'kingdom': _('Kingdom'),
        }

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

        labels = {
            'name': _('Name'),
            'division': _('Division'),
        }

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

        labels = {
            'name': _('Name'),
            'class_name': _('Class'),
        }

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

        labels = {
            'name': _('Name'),
            'order': _('Order'),
        }

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

        labels = {
            'name': _('Name'),
            'family': _('Family'),
        }

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

        labels = {
            'type_update': _('Type'),
            'model': _('Modelo'),
            'description': _('Description'),
            'note': _('Note'),
        }

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
            'id_taxa', 'scientific_name', 'scientific_name_full',
            'genus', 'specific_epithet', 'scientific_name_authorship',
            'subspecies', 'ssp_authorship',
            'variety', 'variety_authorship',
            'form', 'form_authorship',
            'in_argentina', 'in_bolivia', 'in_peru',
            'plant_habit', 'env_habit', 'cycle', 'status',
            'minimum_height', 'maximum_height',
            'synonyms', 'common_names', 'region',
            'notes', 'publication', 'volume', 'pages',
            'type_id',
            'conservation_state', 'determined', 'id_mma',
        )

        labels = {
            'genus': _('Genus'),
            'specific_epithet': _('Specific Epithet'),
            'scientific_name_authorship': _('Author'),
            'subspecies': _('Subspecies'),
            'ssp_authorship': _('Subspecies Author'),
            'variety': _('Variety'),
            'variety_authorship': _('Variety Author'),
            'form': _('Form'),
            'form_authorship': _('Form Author'),
            'plant_habit': _('Habit'),
            'env_habit': _('Life form'),
            'cycle': _('Life Cycle'),
            'status': _('Origin'),
            'in_argentina': _('In Argentina'),
            'in_bolivia': _('In Bolivia'),
            'in_peru': _('In Peru'),
            'maximum_height': _('Maximum Height'),
            'minimum_height': _('Minimum Height'),
            'notes': _('Notes'),
            'publication': _('Publication'),
            'volume': _('Volume'),
            'pages': _('Pages'),
            'type_id': _('Type ID'),
            'common_names': _('Common Names'),
            'synonyms': _('Synonyms'),
            'region': _('Region Distribution'),
            'conservation_state': _('Conservation State'),
            'determined': _('Determined?'),
            'id_mma': _('MMA ID'),
        }

        widgets = {
            'id_taxa': forms.HiddenInput(),
            'genus': forms.Select(attrs={'class': "form-control"}),
            'scientific_name': forms.HiddenInput(),
            'scientific_name_full': forms.HiddenInput(),
            'scientific_name_db': forms.HiddenInput(),
            'specific_epithet': forms.TextInput(attrs={'class': "form-control"}),
            'scientific_name_authorship': forms.TextInput(attrs={'class': "form-control"}),
            'subspecies': forms.TextInput(attrs={'class': "form-control"}),
            'ssp_authorship': forms.TextInput(attrs={'class': "form-control"}),
            'variety': forms.TextInput(attrs={'class': "form-control"}),
            'variety_authorship': forms.TextInput(attrs={'class': "form-control"}),
            'form': forms.TextInput(attrs={'class': "form-control"}),
            'form_authorship': forms.TextInput(attrs={'class': "form-control"}),
            'in_argentina': forms.CheckboxInput(attrs={'class': "form-check-input"}),
            'in_bolivia': forms.CheckboxInput(attrs={'class': "form-check-input"}),
            'in_peru': forms.CheckboxInput(attrs={'class': "form-check-input"}),
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
            'minimum_height': forms.TextInput(attrs={'class': "form-control", 'type': 'number'}),
            'maximum_height': forms.TextInput(attrs={'class': "form-control", 'type': 'number'}),
            'synonyms': forms.SelectMultiple(attrs={'class': "selectpicker", 'multiple data-live-search': 'true',
                                                    'multiple data-multiple-separator': ','}),
            'common_names': forms.SelectMultiple(attrs={'class': "selectpicker", 'multiple data-live-search': 'true',
                                                        'multiple data-multiple-separator': ','}),
            'region': forms.SelectMultiple(
                attrs={'class': "selectpicker", 'multiple data-live-search': 'true',
                       'multiple data-multiple-separator': ','}),
            'notes': forms.Textarea(attrs={'class': "form-control", 'rows': 3, 'cols': 5}),
            'publication': forms.TextInput(attrs={'class': "form-control"}),
            'volume': forms.TextInput(attrs={'class': "form-control"}),
            'pages': forms.TextInput(attrs={'class': "form-control"}),
            'type_id': forms.TextInput(attrs={'class': "form-control"}),
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

    def clean_specific_epithet(self):
        specific_epithet = self.cleaned_data["specific_epithet"]
        if specific_epithet is None:
            raise ValidationError("Epíteto es requerido")
        return specific_epithet

    def clean_ssp_authorship(self):
        subspecies_authors = self.cleaned_data["ssp_authorship"]
        if "specific_epithet" in self.cleaned_data:
            specific_epithet = self.cleaned_data["specific_epithet"]
        else:
            return subspecies_authors
        subspecies = self.cleaned_data["subspecies"]
        if subspecies is not None and subspecies_authors is None and not (
                specific_epithet == subspecies
        ):
            raise ValidationError("Completar autor(es) de subspecies")
        return subspecies_authors

    def clean_variety_authorship(self):
        variety_authors = self.cleaned_data["variety_authorship"]
        if "specific_epithet" in self.cleaned_data:
            specific_epithet = self.cleaned_data["specific_epithet"]
        else:
            return variety_authors
        subspecies = self.cleaned_data["subspecies"]
        variety = self.cleaned_data["variety"]
        if variety is not None and variety_authors is None and not (
                specific_epithet == variety or subspecies == variety
        ):
            raise ValidationError("Completar autor(es) de variedad")
        return variety_authors

    def clean_form_authorship(self):
        form_authors = self.cleaned_data["form_authorship"]
        if "specific_epithet" in self.cleaned_data:
            specific_epithet = self.cleaned_data["specific_epithet"]
        else:
            return form_authors
        subspecies = self.cleaned_data["subspecies"]
        variety = self.cleaned_data["variety"]
        form = self.cleaned_data["form"]
        if form is not None and form_authors is None and not (
                specific_epithet == form or subspecies == form or variety == form
        ):
            raise ValidationError("Completar autor(es) de forma")
        return form_authors


class SynonymyForm(forms.ModelForm):
    class Meta:
        model = Synonymy
        fields = (
            'scientific_name',
            'scientific_name_full',
            'scientific_name_db',
            'genus',
            'specific_epithet',
            'scientific_name_authorship',
            'subspecies',
            'ssp_authorship',
            'variety',
            'variety_authorship',
            'form',
            'form_authorship',
        )

        labels = {
            'scientific_name': _('Scientific Name'),
            'scientific_name_full': _('Complete Scientific Name'),
            'scientific_name_db': _('Database Scientific Name'),
            'genus': _('Genus'),
            'specific_epithet': _('Specific Epithet'),
            'scientific_name_authorship': _('Author'),
            'subspecies': _('Subspecies'),
            'ssp_authorship': _('Subspecies Author'),
            'variety': _('Variety'),
            'variety_authorship': _('Variety Author'),
            'form': _('Form'),
            'form_authorship': _('Form Author'),
        }

        widgets = {
            'scientific_name': forms.HiddenInput(),
            'scientific_name_full': forms.HiddenInput(),
            'scientific_name_db': forms.HiddenInput(),
            'genus': forms.TextInput(attrs={'class': "form-control"}),
            'specific_epithet': forms.TextInput(attrs={'class': "form-control"}),
            'scientific_name_authorship': forms.TextInput(attrs={'class': "form-control"}),
            'subspecies': forms.TextInput(attrs={'class': "form-control"}),
            'ssp_authorship': forms.TextInput(attrs={'class': "form-control"}),
            'variety': forms.TextInput(attrs={'class': "form-control"}),
            'variety_authorship': forms.TextInput(attrs={'class': "form-control"}),
            'form': forms.TextInput(attrs={'class': "form-control"}),
            'form_authorship': forms.TextInput(attrs={'class': "form-control"}),
        }


class CommonNameForm(forms.ModelForm):
    class Meta:
        model = CommonName
        fields = (
            'name',
        )

        labels = {
            'name': _('Name'),
        }

        widgets = {
            'name': forms.TextInput(attrs={'required': True, 'class': "form-control"}),
        }
