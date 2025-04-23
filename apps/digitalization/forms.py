from typing import Dict

from django import forms
from django.contrib.contenttypes.models import ContentType
from django.forms import inlineformset_factory
from django.utils.safestring import mark_safe
from django.utils.translation import gettext_lazy as _

from .models import Herbarium, ProtectedArea, TypeStatus, TYPIFICATION
from .models import PriorityVouchersFile, ColorProfileFile, GeneratedPage
from .models import VoucherImported, GalleryImage, Licence
from ..catalog.models import Species, Synonymy, ScientificName
from ..home.forms import GeographicFieldForm


class PriorityVoucherForm(forms.ModelForm):

    def __init__(self, current_user, *args, **kwargs):
        super(PriorityVoucherForm, self).__init__(*args, **kwargs)
        self.fields['herbarium'].queryset = Herbarium.objects.filter(herbariummember__user=current_user)

    class Meta:
        model = PriorityVouchersFile
        fields = ('herbarium', 'file', )
        widgets = {
            "herbarium": forms.Select(attrs={'class': 'form-control', 'required': 'true'}),
            "file": forms.FileInput(
                attrs={
                    'title': 'Archivo Vouchers Priorizados',
                    'class': 'form-control',
                    'accept': '.xlsx',
                    'required': 'true'
                }),
        }


class GeneratedPageForm(forms.ModelForm):

    def __init__(self, current_user, *args, **kwargs):
        super(GeneratedPageForm, self).__init__(*args, **kwargs)
        self.fields['herbarium'].queryset = Herbarium.objects.filter(herbariummember__user=current_user)

    class Meta:
        model = GeneratedPage
        fields = ('herbarium', )
        widgets = {
            "herbarium": forms.Select(attrs={'class': 'form-control', 'required': 'true'}),
        }


class LoadColorProfileForm(forms.ModelForm):
    class Meta:
        model = ColorProfileFile
        fields = ('file',)
        widgets = {
            "file": forms.ClearableFileInput(
                attrs={
                    'title': 'Archivo Vouchers Priorizados',
                    'class': 'form-control',
                    'accept': '.dcp',
                    'required': 'true'}
            )
        }


class VoucherImportedForm(forms.ModelForm):
    def __init__(self, *args, **kwargs):
        super(VoucherImportedForm, self).__init__(*args, **kwargs)

    class Meta:
        model = VoucherImported
        fields = (
            'catalog_number',
            'other_catalog_numbers',
            'record_number',
            'recorded_by',
            'scientific_name',
            'locality',
            'verbatim_elevation',
            'georeferenced_date',
            'identified_by',
            'date_identified',
            'organism_remarks',
            'priority',
            'image_resized_60',
            'decimal_latitude',
            'decimal_longitude',
        )
        widgets = {
            'catalog_number': forms.TextInput(attrs={'class': "form-control", 'readonly': 'true'}),
            'other_catalog_numbers': forms.TextInput(attrs={'class': "form-control", 'readonly': 'true'}),
            'record_number': forms.TextInput(attrs={'class': "form-control"}),
            'recorded_by': forms.TextInput(attrs={'class': "form-control"}),
            'scientific_name': forms.Select(attrs={'class': "form-control"}),
            'locality': forms.TextInput(attrs={'class': "form-control"}),
            'verbatim_elevation': forms.TextInput(attrs={'class': "form-control", 'type': 'number'}),
            'georeferenced_date': forms.DateInput(attrs={'class': 'form-control datepicker-input'}),
            'identified_by': forms.TextInput(attrs={'class': "form-control"}),
            'date_identified': forms.DateTimeInput(attrs={'class': 'form-control datepicker-input'}),
            'organism_remarks': forms.Textarea(attrs={'class': "form-control", 'rows': "5"}),
            'priority': forms.TextInput(attrs={'class': "form-control", 'type': 'number'}),
            'image_resized_60': forms.TextInput(attrs={'class': "form-control", 'readonly': 'true'}),
            'decimal_latitude': forms.TextInput(attrs={'class': "form-control"}),
            'decimal_longitude': forms.TextInput(attrs={'class': "form-control"}),
        }


class TypeStatusForm(forms.ModelForm):
    taxon_id = forms.ChoiceField(
        label=_("Attached Taxon"),
        choices=[],
        widget=forms.Select(attrs={
            'class': 'form-control',
            'data-live-search': 'true',
        }),
        required=True,
    )

    def __init__(self, voucher, *args, **kwargs):
        super(TypeStatusForm, self).__init__(*args, **kwargs)
        self.taxon_content_type: ContentType
        self.attached_taxon: ScientificName
        species = voucher.scientific_name
        synonyms = species.synonyms.all()
        self.fields['taxon_id'].choices = [
            (species.unique_taxon_id, species.scientific_name)
        ] + [
            (x.unique_taxon_id, x.scientific_name) for x in synonyms
        ]


    def clean(self) -> Dict:
        cleaned_data = super().clean()
        taxon_id = cleaned_data.get("taxon_id")
        try:
            self.attached_taxon = Species.objects.get(unique_taxon_id=taxon_id)
            self.taxon_content_type = ContentType.objects.get_for_model(Species)
        except Species.DoesNotExist:
            try:
                self.attached_taxon = Synonymy.objects.get(unique_taxon_id=taxon_id)
                self.taxon_content_type = ContentType.objects.get_for_model(Synonymy)
            except Synonymy.DoesNotExist:
                self.add_error(
                    "taxon_id",
                    _("No taxon with that id")
                )
        return cleaned_data

    def save(self, *args, **kwargs) -> Species:
        sp = super().save(commit=False)
        sp.taxon_content_type = self.taxon_content_type
        sp.taxon_id = self.attached_taxon.unique_taxon_id
        if kwargs.get("commit", True):
            return sp.save(*args, **kwargs)
        else:
            return sp

    class Meta:
        model = TypeStatus
        fields = (
            'type',
            'taxon_id',
        )

        widgets = {
            'type': forms.Select(attrs={'class': 'form-control'}, choices=TYPIFICATION),
        }

class TypeStatusFormSet(forms.BaseInlineFormSet):
    def __init__(self, *args, **kwargs):
        super(TypeStatusFormSet, self).__init__(*args, **kwargs)
        self.voucher = self.instance
        if self.instance is not None:
            self.queryset = self.instance.typestatus_set.all()

    def get_form_kwargs(self, index):
        kwargs = super(TypeStatusFormSet, self).get_form_kwargs(index)
        kwargs["voucher"] = self.voucher
        return kwargs


class GalleryImageForm(forms.ModelForm):
    def __init__(self, *args, **kwargs):
        super(GalleryImageForm, self).__init__(*args, **kwargs)
        self.fields['licence'].choices = list(
            self.fields['licence'].choices) + [("", _("(Add new licence)"))]

    class Meta:
        model = GalleryImage
        fields = (
            'image',
            'taken_by',
            'licence',
            'specimen',
        )

        widgets = {
            'image': forms.FileInput(attrs={'class': 'form-control'}),
            'taken_by': forms.TextInput(attrs={'class': 'form-control'}),
            'licence': forms.Select(attrs={'class': 'form-control'}),
            'specimen': forms.TextInput(attrs={'class': 'form-control'}),
        }


class LicenceForm(forms.ModelForm):

    class Meta:
        model = Licence
        fields = {
            'name',
            'link',
            'short_name',
        }

        widgets = {
            'name': forms.TextInput(attrs={'class': "form-control"}),
            'link': forms.TextInput(attrs={'class': "form-control"}),
            'short_name': forms.TextInput(attrs={'class': "form-control"}),
        }


class ProtectedAreaForm(GeographicFieldForm):

    class Meta:
        model = ProtectedArea
        fields = '__all__'
