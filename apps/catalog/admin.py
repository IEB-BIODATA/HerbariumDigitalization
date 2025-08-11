from django.contrib import admin
from django.contrib.admin import ModelAdmin
from leaflet.admin import LeafletGeoAdmin
from modeltranslation.admin import TranslationAdmin

from .forms import RegionForm
from .models import PlantHabit, EnvironmentalHabit, Status, Cycle, Region, ConservationStatus, Habit, TaxonRank, \
    References, Author

ATTRIBUTE_LIST_DISPLAY = (['id', 'name', 'created_by', 'created_at', 'updated_at'])


class AttributeAdmin(TranslationAdmin):
    list_display = ATTRIBUTE_LIST_DISPLAY
    search_fields = ['name']

    def save_model(self, request, obj, form, change):
        obj.created_by = request.user
        obj.save()


@admin.register(PlantHabit)
class PlantHabitAdmin(AttributeAdmin):
    pass


@admin.register(EnvironmentalHabit)
class EnvHabitAdmin(AttributeAdmin):
    pass


@admin.register(Habit)
class HabitAdmin(AttributeAdmin):
    list_display = AttributeAdmin.list_display + ["plant_habit", "env_habit"]


@admin.register(Status)
class StatusAdmin(AttributeAdmin):
    pass


@admin.register(Cycle)
class CycleAdmin(AttributeAdmin):
    pass


@admin.register(TaxonRank)
class TaxonRankAdmin(AttributeAdmin):
    pass


@admin.register(Region)
class RegionAdmin(LeafletGeoAdmin, AttributeAdmin):
    form = RegionForm
    exclude = ('geometry', )


@admin.register(ConservationStatus)
class ConservationStatusAdmin(AttributeAdmin):
    pass

@admin.register(Author)
class AuthorAdmin(ModelAdmin):
    pass


@admin.register(References)
class ReferencesAdmin(ModelAdmin):
    pass
