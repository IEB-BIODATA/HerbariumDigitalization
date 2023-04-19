from django import forms
from .models import PriorityVouchersFile, Herbarium, ColorProfileFile, VoucherImported, GalleryImage, Licence
from ..catalog.models import Species


class LoadPriorityVoucherForm(forms.ModelForm):

    def __init__(self, current_user, *args, **kwargs):
        super(LoadPriorityVoucherForm, self).__init__(*args, **kwargs)
        self.fields['herbarium'].queryset = Herbarium.objects.filter(herbariummember__user=current_user)

    class Meta:
        model = PriorityVouchersFile
        fields = ('herbarium', 'file',)
        widgets = {
            "herbarium": forms.Select(attrs={'class': 'form-control', 'required': 'true'}),
            "file": forms.ClearableFileInput(
                attrs={'title': 'Archivo Vouchers Priorizados', 'class': 'form-control', 'accept': '.xlsx',
                       'required': 'true'})
        }


class LoadColorProfileForm(forms.ModelForm):
    class Meta:
        model = ColorProfileFile
        fields = ('file',)
        widgets = {
            "file": forms.ClearableFileInput(
                attrs={'title': 'Archivo Vouchers Priorizados', 'class': 'form-control', 'accept': '.dcp',
                       'required': 'true'})
        }


class VoucherImportedForm(forms.ModelForm):
    class Meta:
        model = VoucherImported
        fields = (
            'otherCatalogNumbers',
            'catalogNumber',
            'recordedBy',
            'recordNumber',
            'organismRemarks',
            'scientificName',
            'locality',
            'verbatimElevation',
            'georeferencedDate',
            'decimalLatitude',
            'decimalLongitude',
            'identifiedBy',
            'dateIdentified',
            'image',
            'image_resized_10',
            'image_resized_60',
            'image_public',
            'image_public_resized_60',
            'priority'
        )
        widgets = {
            'otherCatalogNumbers': forms.TextInput(attrs={'class': "form-control", 'readonly': 'true'}),
            'catalogNumber': forms.TextInput(attrs={'class': "form-control", 'readonly': 'true'}),
            'recordedBy': forms.TextInput(attrs={'class': "form-control"}),
            'recordNumber': forms.TextInput(attrs={'class': "form-control"}),
            'organismRemarks': forms.Textarea(attrs={'class': "form-control", 'rows': "5"}),
            'scientificName': forms.Select(attrs={'class': "form-control"}),
            'locality': forms.TextInput(attrs={'class': "form-control"}),
            'verbatimElevation': forms.TextInput(attrs={'class': "form-control", 'type': 'number'}),
            'georeferencedDate': forms.DateTimeInput(attrs={'class': 'form-control datetimepicker-input'}),
            'decimalLatitude': forms.TextInput(attrs={'class': "form-control"}),
            'decimalLongitude': forms.TextInput(attrs={'class': "form-control"}),
            'identifiedBy': forms.TextInput(attrs={'class': "form-control"}),
            'dateIdentified': forms.DateTimeInput(attrs={'class': 'form-control datetimepicker-input'}),
            'image': forms.TextInput(attrs={'class': "form-control", 'readonly': 'true'}),
            'image_resized_60': forms.TextInput(attrs={'class': "form-control", 'readonly': 'true'}),
            'priority': forms.TextInput(attrs={'class': "form-control", 'type': 'number'}),
        }


class GalleryImageForm(forms.ModelForm):

    def __init__(self, *args, **kwargs):
        super(GalleryImageForm, self).__init__(*args, **kwargs)
        self.fields['licence'].choices = list(
            self.fields['licence'].choices) + [("", "(Añadir nueva licencia)")]

    class Meta:
        model = GalleryImage
        fields = (
            'scientificName',
            'image',
            'taken_by',
            'licence',
            'specimen',
        )
        widgets = {
            'scientificName': forms.TextInput(attrs={'class': "form-control", 'readonly': 'true'}),
            'image': forms.FileInput(attrs={'class': "form-control"}),
            'taken_by': forms.TextInput(attrs={'class': "form-control"}),
            'licence': forms.Select(attrs={'class': "form-control"}),
            'specimen': forms.TextInput(attrs={'class': "form-control"}),
        }


class LicenceForm(forms.ModelForm):

    class Meta:
        model = Licence
        fields = {
            'name',
            'link',
        }
        widgets = {
            'name': forms.TextInput(attrs={'class': "form-control"}),
            'link': forms.TextInput(attrs={'class': "form-control"}),
        }
