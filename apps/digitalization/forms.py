from django import forms

from .models import PriorityVouchersFile, Herbarium, ColorProfileFile, VoucherImported, GalleryImage, Licence


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
    class Meta:
        model = VoucherImported
        fields = (
            'other_catalog_numbers',
            'catalog_number',
            'recorded_by',
            'record_number',
            'organism_remarks',
            'scientific_name',
            'locality',
            'verbatim_elevation',
            'georeferenced_date',
            'decimal_latitude',
            'decimal_longitude',
            'identified_by',
            'identified_date',
            'image',
            'image_resized_10',
            'image_resized_60',
            'image_public',
            'image_public_resized_60',
            'priority'
        )
        widgets = {
            'other_catalog_numbers': forms.TextInput(attrs={'class': "form-control", 'readonly': 'true'}),
            'catalog_number': forms.TextInput(attrs={'class': "form-control", 'readonly': 'true'}),
            'recorded_by': forms.TextInput(attrs={'class': "form-control"}),
            'record_number': forms.TextInput(attrs={'class': "form-control"}),
            'organism_remarks': forms.Textarea(attrs={'class': "form-control", 'rows': "5"}),
            'scientific_name': forms.Select(attrs={'class': "form-control"}),
            'locality': forms.TextInput(attrs={'class': "form-control"}),
            'verbatim_elevation': forms.TextInput(attrs={'class': "form-control", 'type': 'number'}),
            'georeferenced_date': forms.DateTimeInput(attrs={'class': 'form-control datetimepicker-input'}),
            'decimal_latitude': forms.TextInput(attrs={'class': "form-control"}),
            'decimal_longitude': forms.TextInput(attrs={'class': "form-control"}),
            'identified_by': forms.TextInput(attrs={'class': "form-control"}),
            'identified_date': forms.DateTimeInput(attrs={'class': 'form-control datetimepicker-input'}),
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
            'scientific_name',
            'image',
            'taken_by',
            'licence',
            'specimen',
        )
        widgets = {
            'scientific_name': forms.TextInput(attrs={'class': "form-control", 'readonly': 'true'}),
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
            'short_name',
        }
        widgets = {
            'name': forms.TextInput(attrs={'class': "form-control"}),
            'link': forms.TextInput(attrs={'class': "form-control"}),
            'short_name': forms.TextInput(attrs={'class': "form-control"}),
        }
