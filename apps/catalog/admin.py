from django.contrib import admin
from import_export.admin import ImportExportModelAdmin
from .models import Species, Synonymy, Kingdom, Division, ClassName, Order, Family, Genus, Region, \
    Status, CommonName, ConservationState, Binnacle
from .resources import SpeciesAdminResource


@admin.register(Kingdom)
class KingdomAdmin(ImportExportModelAdmin):
    list_display = (['name', 'created_by', 'created_at', 'updated_at'])
    search_fields = ['name']


@admin.register(Division)
class DivisionAdmin(ImportExportModelAdmin):
    list_display = (['name', 'kingdom', 'created_by', 'created_at', 'updated_at'])
    search_fields = ['name']


@admin.register(ClassName)
class ClassNameAdmin(ImportExportModelAdmin):
    list_display = (['name', 'division', 'created_by', 'created_at', 'updated_at'])
    search_fields = ['name']


@admin.register(Order)
class OrderAdmin(ImportExportModelAdmin):
    list_display = (['name', 'class_name', 'created_by', 'created_at', 'updated_at'])
    search_fields = ['name']


@admin.register(Family)
class FamilyAdmin(ImportExportModelAdmin):
    list_display = (['name', 'order', 'created_by', 'created_at', 'updated_at'])
    search_fields = ['name']


@admin.register(Genus)
class GenusAdmin(ImportExportModelAdmin):
    list_display = (['name', 'family', 'created_by', 'created_at', 'updated_at'])
    search_fields = ['name']


@admin.register(Species)
class SpeciesAdmin(ImportExportModelAdmin):
    resource_class = SpeciesAdminResource
    list_display = (['id', 'id_taxa', 'scientificName', 'genus', 'created_by', 'created_at', 'updated_at'])
    search_fields = ['scientificName']


@admin.register(Synonymy)
class SynonymyAdmin(ImportExportModelAdmin):
    list_display = (['scientificName', 'created_by', 'created_at', 'updated_at'])
    search_fields = ['scientificName']


@admin.register(Region)
class RegionAdmin(ImportExportModelAdmin):
    list_display = (['name', 'created_by', 'created_at', 'updated_at'])
    search_fields = ['name']


@admin.register(Status)
class StatusAdmin(ImportExportModelAdmin):
    list_display = (['name', 'created_by', 'created_at', 'updated_at'])
    search_fields = ['name']


@admin.register(CommonName)
class CommonNameAdmin(ImportExportModelAdmin):
    list_display = (['name', 'created_by', 'created_at', 'updated_at'])
    search_fields = ['name']


@admin.register(ConservationState)
class ConservationStateAdmin(ImportExportModelAdmin):
    list_display = (['name', 'key', 'created_by', 'created_at', 'updated_at'])
    search_fields = ['name']


@admin.register(Binnacle)
class BinnacleAdmin(ImportExportModelAdmin):
    list_display = (['id', 'type_update', 'model', 'description', 'created_by', 'created_at', 'updated_at'])
    search_fields = ['type_update']
