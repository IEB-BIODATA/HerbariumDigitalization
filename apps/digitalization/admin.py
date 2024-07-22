# -*- coding: utf-8 -*-
import logging

from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.contrib.auth.models import User
from django.utils.safestring import mark_safe
from leaflet.admin import LeafletGeoAdmin
from modeltranslation.admin import TranslationAdmin

from .forms import ProtectedAreaForm
from .models import Herbarium, HerbariumMember, ProtectedArea
from ..home.models import Profile


@admin.register(Herbarium)
class HerbariumAdmin(TranslationAdmin):
    list_display = (['id', 'name', 'institution_code', 'collection_code'])

    def save_model(self, request, obj, form, change):
        obj.created_by = request.user
        obj.save()


# The classes are defined to integer the units in the django user form
class HerbariumMemberInline(admin.StackedInline):
    model = HerbariumMember


class PreferenceInline(admin.StackedInline):
    model = Profile


# Define a new User admin that integers the classes to link units and programs to the user admin
class UserAdmin(BaseUserAdmin):
    list_display = BaseUserAdmin.list_display + ('herbariums', )
    list_filter = BaseUserAdmin.list_filter + ('herbariummember__herbarium',)
    inlines = [HerbariumMemberInline, PreferenceInline]

    def herbariums(self, obj):
        logging.debug(obj)
        logging.debug(obj.herbariummember)
        return mark_safe("<br>".join([m.name for m in obj.herbariummember.herbarium.all()]))


class AreaAdmin(LeafletGeoAdmin, TranslationAdmin):
    list_display = (['id', 'name'])


@admin.register(ProtectedArea)
class ProtectedAreaAdmin(AreaAdmin):
    form = ProtectedAreaForm
    exclude = ('created_by', 'geometry')
    list_display = AreaAdmin.list_display + [
        'mma_code', 'designation_type',
        'category', 'iucn_management_category',
    ]

    def save_model(self, request, obj, form, change):
        obj.created_by = request.user
        obj.save()


# Re-register UserAdmin
admin.site.unregister(User)
admin.site.register(User, UserAdmin)
