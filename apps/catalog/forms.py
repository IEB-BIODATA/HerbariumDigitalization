import logging

from django import forms
from django.core.exceptions import ValidationError
from django.forms import TextInput
from django.utils.safestring import mark_safe
from django.utils.translation import gettext_lazy as _

from .models import Division, ClassName, Order, Family, Genus, Species, Synonymy, Binnacle, CommonName, Region, \
    References, Author
from ..home.forms import GeographicFieldForm


class TaxonomicForm(forms.ModelForm):
    def __init__(self, *args, **kwargs):
        super(TaxonomicForm, self).__init__(*args, **kwargs)
        self.fields['references'].choices = [("", _("(Add new reference)"))] + list(self.fields['references'].choices)


class DivisionForm(TaxonomicForm):
    class Meta:
        model = Division
        fields = (
            'name',
            'kingdom',
            'references',
        )

        widgets = {
            'name': forms.TextInput(attrs={'required': True, 'class': "form-control"}),
            'kingdom': forms.Select(attrs={'required': True, 'class': "form-control"}),
            'references': forms.SelectMultiple(attrs={'class': "selectpicker", "multiple data-live-search": "true",
                                                      "multiple data-multiple-separator": ','}),
        }


class ClassForm(TaxonomicForm):
    class Meta:
        model = ClassName
        fields = (
            'name',
            'division',
            'references',
        )

        widgets = {
            'name': forms.TextInput(attrs={'required': True, 'class': "form-control"}),
            'division': forms.Select(attrs={'required': True, 'class': "form-control"}),
            'references': forms.SelectMultiple(attrs={'class': "selectpicker", "multiple data-live-search": "true",
                                                      "multiple data-multiple-separator": ','}),
        }


class OrderForm(TaxonomicForm):
    class Meta:
        model = Order
        fields = (
            'name',
            'classname',
            'references',
        )

        widgets = {
            'name': forms.TextInput(attrs={'required': True, 'class': "form-control"}),
            'classname': forms.Select(attrs={'required': True, 'class': "form-control"}),
            'references': forms.SelectMultiple(attrs={'class': "selectpicker", "multiple data-live-search": "true",
                                                      "multiple data-multiple-separator": ','}),
        }


class FamilyForm(TaxonomicForm):
    class Meta:
        model = Family
        fields = (
            'name',
            'order',
            'references',
        )

        widgets = {
            'name': forms.TextInput(attrs={'required': True, 'class': "form-control"}),
            'order': forms.Select(attrs={'required': True, 'class': "form-control"}),
            'references': forms.SelectMultiple(attrs={'class': "selectpicker", "multiple data-live-search": "true",
                                                      "multiple data-multiple-separator": ','}),
        }


class GenusForm(TaxonomicForm):
    class Meta:
        model = Genus
        fields = (
            'name',
            'family',
            'references',
        )

        widgets = {
            'name': forms.TextInput(attrs={'required': True, 'class': "form-control"}),
            'family': forms.Select(attrs={'required': True, 'class': "form-control"}),
            'references': forms.SelectMultiple(attrs={'class': "selectpicker", "multiple data-live-search": "true",
                                                      "multiple data-multiple-separator": ','}),
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


class SpeciesForm(TaxonomicForm):
    synonyms = forms.ModelMultipleChoiceField(
        queryset=Synonymy.objects.all(),
        widget=forms.SelectMultiple(attrs={
            'class': "selectpicker",
            'multiple data-live-search': 'true',
            'multiple data-multiple-separator': ','}
        ),
        required=False
    )

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
            'common_names', 'region',
            'notes', 'type_id', 'references',
            'conservation_status', 'determined', 'id_mma',
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
            'common_names': forms.SelectMultiple(attrs={'class': "selectpicker", 'multiple data-live-search': 'true',
                                                        'multiple data-multiple-separator': ','}),
            'region': forms.SelectMultiple(
                attrs={'class': "selectpicker", 'multiple data-live-search': 'true',
                       'multiple data-multiple-separator': ','}),
            'notes': forms.Textarea(attrs={'class': "form-control", 'rows': 3, 'cols': 5}),
            'type_id': forms.TextInput(attrs={'class': "form-control"}),
            'references': forms.SelectMultiple(attrs={'class': "selectpicker", "multiple data-live-search": "true",
                       "multiple data-multiple-separator": ','}),
            'conservation_status': forms.SelectMultiple(
                attrs={'class': "selectpicker", "multiple data-live-search": "true",
                       "multiple data-multiple-separator": ','}),
            'determined': forms.CheckboxInput(attrs={'class': "form-check-input"}),
            'id_mma': forms.TextInput(attrs={'class': "form-control"}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if self.instance and self.instance.pk:
            self.fields["synonyms"].initial = self.instance.synonyms.all()

    def save(self, commit=True):
        instance = super(SpeciesForm, self).save(commit=False)
        if commit:
            instance.save()
            instance.save_m2m()
            self.instance.synonyms.set(self.cleaned_data["synonyms"])
        return instance

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


class SynonymyForm(TaxonomicForm):
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
            'references',
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
            'references': forms.SelectMultiple(attrs={'class': "selectpicker", "multiple data-live-search": "true",
                                                      "multiple data-multiple-separator": ','}),
        }


class CommonNameForm(forms.ModelForm):
    class Meta:
        model = CommonName
        fields = (
            'name',
            'language',
        )

        labels = {
            'name': _('Name'),
            'language': _('Language'),
        }

        widgets = {
            'name': forms.TextInput(attrs={'required': True, 'class': "form-control"}),
            'language': forms.Select(attrs={'class': 'form-control'}),
        }


class RegionForm(GeographicFieldForm):
    class Meta:
        model = Region
        fields = '__all__'


class AuthorWidget(forms.MultiWidget):
    def __init__(self, attrs=None, **kwargs):
        self.reference = kwargs.pop('reference', None)
        self.author = kwargs.pop('author', None)
        widgets = [
            TextInput(attrs={"class": "autocomplete-author-first-name form-control"}),
            TextInput(attrs={"class": "autocomplete-author-last-name form-control"}),
        ]
        super(AuthorWidget, self).__init__(widgets, attrs)

    def decompress(self, value):
        if value:
            return value.split("\t")
        return None

    def compress(self, value):
        if value:
            return f"{value[0]}\t{value[1]}"
        return None

    def render(self, name, value, attrs=None, renderer=None):
        attrs_1 = {} if attrs is None else attrs.copy()
        attrs_2 = {} if attrs is None else attrs.copy()
        attrs_1["id"] = attrs_1["id"] + "_first_name"
        attrs_1["id"] = attrs_1["id"] + "_last_name"
        if "required" in attrs_2:
            del attrs_2["required"]
        if value is None:
            value = [None, None]

        first_name_widget = self.widgets[0].render(f"{name}_first_name", value[0], attrs_1)
        last_name_widget = self.widgets[1].render(f"{name}_last_name", value[1], attrs_2)

        delete_msg = _("Delete author")
        action = ""
        if self.reference is not None and self.author is not None:
            action = f" onclick=\"deleteAuthor({self.reference}, {self.author}, event\" "

        delete_button = f"<button type='button' class='btn btn-danger remove-author' {action}> {delete_msg}</button>"

        return mark_safe(f"""
            <div class="author-fields">
                <div class="row">
                    <div class="col-md-4">{first_name_widget}</div>
                    <div class="col-md-4">{last_name_widget}</div>
                    <div class="col-md-4">{delete_button}</div>
                </div>
            </div>
        """)


class AuthorField(forms.Field):
    widget = AuthorWidget

    def clean(self, value):
        value = super(AuthorField, self).clean(value)
        return value


class AuthorForm(forms.ModelForm):
    author_field = AuthorField(label=_("Author"))
    def __init__(self, *args, **kwargs):
        reference = kwargs.pop('reference', None)
        super(AuthorForm, self).__init__(*args, **kwargs)
        if self.instance.pk is not None:
            self.initial["author_field"] = [self.instance.first_name, self.instance.last_name]
        if reference is not None:
            self.fields["author_field"].widget = AuthorWidget(reference=reference, author=self.instance.pk)

    class Meta:
        model = Author
        fields = ['author_field', ]


class ReferenceForm(forms.ModelForm):
    class Meta:
        model = References
        fields = (
            'title', 'journal', 'volume', 'issue', 'first_page', 'last_page', 'year'
        )

        widgets = {
            'title': forms.TextInput(attrs={'class': "form-control"}),
            'journal': forms.TextInput(attrs={'class': "form-control"}),
            'volume': forms.NumberInput(attrs={'class': "form-control"}),
            'issue': forms.NumberInput(attrs={'class': "form-control"}),
            'first_page': forms.NumberInput(attrs={'class': "form-control"}),
            'last_page': forms.NumberInput(attrs={'class': "form-control"}),
            'year': forms.NumberInput(attrs={'class': "form-control"}),
        }
