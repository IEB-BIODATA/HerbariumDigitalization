# -*- coding: utf-8 -*-
from django.contrib import admin
from .models import Herbarium, BiodataCode, GeneratedPage, HerbariumMember, PriorityVouchersFile, VoucherImported, \
    ColorProfileFile
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.contrib.auth.models import User
from import_export.admin import ImportExportModelAdmin
from .resources import VoucherImportedAdminResource


@admin.register(Herbarium)
class HerbariumAdmin(admin.ModelAdmin):
    list_display = (['name', 'institution_code', 'collection_code'])


@admin.register(BiodataCode)
class BiodataCodeAdmin(admin.ModelAdmin):
    list_display = (
    ['code', 'catalogNumber', 'herbarium', 'created_by', 'created_at', 'qr_generated', 'page', 'voucher_state'])
    search_fields = ['catalogNumber', ]


@admin.register(GeneratedPage)
class GeneratedPageAdmin(admin.ModelAdmin):
    list_display = (['name', 'herbarium', 'terminated', 'created_by', 'created_at'])


# Se define la clase para integrar las unidades en el formulario de usuario django
class HerbariumMemberInline(admin.StackedInline):
    model = HerbariumMember
    verbose_name = 'Herbario'
    verbose_name_plural = 'Herbarios'


@admin.register(PriorityVouchersFile)
class PriorityVouchersFileAdmin(admin.ModelAdmin):
    list_display = (['id', 'file', 'herbarium', 'created_by', 'created_at'])


@admin.register(VoucherImported)
class VoucherImportedAdmin(ImportExportModelAdmin):
    resource_class = VoucherImportedAdminResource
    list_display = (['herbarium', 'catalogNumber', 'scientificName', 'vouchers_file'])
    search_fields = ['catalogNumber', ]


@admin.register(ColorProfileFile)
class ColorProfileFileAdmin(admin.ModelAdmin):
    list_display = (['file', 'created_by', 'created_at'])


# Define a new User admin que integra las clases para vincular unidades y programas en el admin del usuario
class UserAdmin(BaseUserAdmin):
    inlines = ([HerbariumMemberInline])


# Re-register UserAdmin
admin.site.unregister(User)
admin.site.register(User, UserAdmin)
