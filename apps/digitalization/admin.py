# -*- coding: utf-8 -*-
from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.contrib.auth.models import User
from django.utils.translation import gettext_lazy as _
from modeltranslation.admin import TranslationAdmin

from .models import Herbarium, HerbariumMember
from ..home.models import Profile


@admin.register(Herbarium)
class HerbariumAdmin(TranslationAdmin):
    list_display = (['id', 'name', 'institution_code', 'collection_code'])


# The classes are defined to integer the units in the django user form
class HerbariumMemberInline(admin.StackedInline):
    model = HerbariumMember
    verbose_name = _('Herbarium')
    verbose_name_plural = _('Herbariums')


class PreferenceInline(admin.StackedInline):
    model = Profile
    verbose_name = _('Profile')
    verbose_name_plural = _('Profiles')


# Define a new User admin that integers the classes to link units and programs to the user admin
class UserAdmin(BaseUserAdmin):
    inlines = [HerbariumMemberInline, PreferenceInline]


# Re-register UserAdmin
admin.site.unregister(User)
admin.site.register(User, UserAdmin)
