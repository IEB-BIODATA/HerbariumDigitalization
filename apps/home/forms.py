import logging

from django import forms
from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
from django.contrib.gis import forms as gis_forms
from django.utils.translation import gettext_lazy as _
from leaflet.forms.widgets import LeafletWidget

from apps.home.models import Profile
from intranet.utils import get_geometry


class ProfileForm(forms.ModelForm):

    class Meta:
        model = Profile
        fields = (
            'language',
            'theme',
        )

        labels = {
            'language': _("Language"),
            'theme': _("Theme")
        }

        widgets = {
            'language': forms.Select(attrs={'class': 'form-control'}),
            'theme': forms.Select(attrs={'class': 'form-control'}),
        }


class UserForm(forms.ModelForm):

    old_password = forms.CharField(
        label=_("Old Password"),
        required=False,
        widget=forms.PasswordInput(attrs={'class': 'form-control'}, render_value=False)
    )
    new_password = forms.CharField(
        label=_("New Password"),
        required=False,
        widget=forms.PasswordInput(attrs={'class': 'form-control'}, render_value=True)
    )
    validate_password = forms.CharField(
        label=_("Validate Password"),
        required=False,
        widget=forms.PasswordInput(attrs={'class': 'form-control'}, render_value=True)
    )

    class Meta:
        model = User
        fields = (
            'username',
            'first_name',
            'last_name',
            'email',
            'old_password',
            'new_password',
            'validate_password',
            'password',
        )

        labels = {
            'username': _("User Name"),
            'first_name': _("First Name"),
            'last_name': _("Last Name"),
            'email': _("Email"),
        }

        widgets = {
            'username': forms.TextInput(attrs={'class': 'form-control'}),
            'first_name': forms.TextInput(attrs={'class': 'form-control'}),
            'last_name': forms.TextInput(attrs={'class': 'form-control'}),
            'email': forms.TextInput(attrs={'class': 'form-control'}),
            'password': forms.HiddenInput(),
        }

    def clean_old_password(self):
        new_password = self.data.get("new_password", "")
        old_password = self.cleaned_data.get("old_password", "")
        if len(new_password) != 0 and len(old_password) == 0:
            raise ValidationError("To reset password you must validate your old password")
        if len(new_password) != 0 and not self.instance.check_password(old_password):
            raise ValidationError("Wrong password")
        return old_password

    def clean_validate_password(self):
        new_password = self.data.get("new_password", "")
        retry_password = self.cleaned_data.get("validate_password", "")
        if len(new_password) != 0 and len(retry_password) == 0:
            raise ValidationError("To reset password you must confirm it")
        if new_password != retry_password:
            raise ValidationError("Password must match")
        return retry_password


class GeographicFieldForm(forms.ModelForm):
    geometry_file = forms.FileField(label=_('Geometry File'), required=False)
    geometry_selection = gis_forms.GeometryField(label=_('Geometry'), widget=LeafletWidget, required=False)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.initial['geometry_selection'] = kwargs['instance'].geometry
        return

    def save(self, commit=True):
        model = super().save(commit)
        geometry_file = self.cleaned_data['geometry_file']
        if geometry_file is not None:
            model.geometry = get_geometry(geometry_file)
        else:
            geometry_selection = self.cleaned_data['geometry_selection']
            model.geometry = geometry_selection
        return model

    def clean_geometry_selection(self):
        geometry_file = self.cleaned_data.get('geometry_file', None)
        geometry_selection = self.cleaned_data['geometry_selection']
        if geometry_file is None and geometry_selection is None:
            raise ValidationError(_('Geometry is required'))
        return geometry_selection

    class Meta:
        abstract = True
