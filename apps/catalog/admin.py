from django.contrib import admin
from modeltranslation.admin import TranslationAdmin

from .models import PlantHabit, EnvironmentalHabit, Status, Cycle, Region, ConservationState, Habit

ATTRIBUTE_LIST_DISPLAY = (['id', 'name', 'created_by', 'created_at', 'updated_at'])


class AttributeAdmin(TranslationAdmin):
    list_display = ATTRIBUTE_LIST_DISPLAY
    search_fields = ['name']


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


@admin.register(Region)
class RegionAdmin(AttributeAdmin):
    pass


@admin.register(ConservationState)
class ConservationStateAdmin(AttributeAdmin):
    pass
