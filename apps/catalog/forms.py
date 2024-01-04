from django import forms
from django.core.exceptions import ValidationError
from django.utils.translation import gettext_lazy as _
from leaflet.forms.widgets import LeafletWidget
from modeltranslation.forms import TranslationModelForm

from .models import Division, ClassName, Order, Family, Genus, Species, Synonymy, Binnacle, CommonName, Region
from ..home.forms import GeographicFieldForm


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
        genus = self.cleaned_data['genus']
        if genus is None:
            raise ValidationError(_('Genus is required'))
        return genus

    def clean_specific_epithet(self):
        specific_epithet = self.cleaned_data['specific_epithet']
        if specific_epithet is None:
            raise ValidationError(_('Epithet is required'))
        return specific_epithet

    def clean_ssp_authorship(self):
        subspecies_authors = self.cleaned_data['ssp_authorship']
        if 'specific_epithet' in self.cleaned_data:
            specific_epithet = self.cleaned_data['specific_epithet']
        else:
            return subspecies_authors
        subspecies = self.cleaned_data['subspecies']
        if subspecies is not None and subspecies_authors is None and not (
                specific_epithet == subspecies
        ):
            raise ValidationError(_('Subspecies authorship is required'))
        return subspecies_authors

    def clean_variety_authorship(self):
        variety_authors = self.cleaned_data['variety_authorship']
        if 'specific_epithet' in self.cleaned_data:
            specific_epithet = self.cleaned_data['specific_epithet']
        else:
            return variety_authors
        subspecies = self.cleaned_data['subspecies']
        variety = self.cleaned_data['variety']
        if variety is not None and variety_authors is None and not (
                specific_epithet == variety or subspecies == variety
        ):
            raise ValidationError(_('Variety authorship is required'))
        return variety_authors

    def clean_form_authorship(self):
        form_authors = self.cleaned_data['form_authorship']
        if 'specific_epithet' in self.cleaned_data:
            specific_epithet = self.cleaned_data['specific_epithet']
        else:
            return form_authors
        subspecies = self.cleaned_data['subspecies']
        variety = self.cleaned_data['variety']
        form = self.cleaned_data['form']
        if form is not None and form_authors is None and not (
                specific_epithet == form or subspecies == form or variety == form
        ):
            raise ValidationError(_('Form authorship is required'))
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
            'name_es', 'name_en'
        )

        labels = {
            'name_es': _('Spanish name'),
            'name_en': _('English name')
        }

        widgets = {
            'name_es': forms.TextInput(attrs={'required': True, 'class': "form-control"}),
            'name_en': forms.TextInput(attrs={'required': True, 'class': "form-control"}),
        }


class RegionForm(GeographicFieldForm):
    class Meta:
        model = Region
        fields = '__all__'
