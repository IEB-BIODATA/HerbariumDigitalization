from modeltranslation.translator import register, TranslationOptions

from .models import PlantHabit, EnvironmentalHabit, Status, Cycle, Region, ConservationStatus, CommonName, CatalogView, \
    RegionDistributionView, FinderView, Binnacle, Habit, TaxonRank


@register(PlantHabit)
class PlanHabitTranslationOptions(TranslationOptions):
    fields = ('name',)


@register(EnvironmentalHabit)
class EnvHabitTranslationOptions(TranslationOptions):
    fields = ('name',)


@register(Habit)
class HabitTranslationOptions(TranslationOptions):
    fields = ('name',)


@register(Status)
class StatusTranslationOptions(TranslationOptions):
    fields = ('name',)


@register(Cycle)
class CycleTranslationOptions(TranslationOptions):
    fields = ('name',)


@register(TaxonRank)
class TaxonRankTranslationOptions(TranslationOptions):
    fields = ('name',)


@register(Region)
class RegionTranslationOptions(TranslationOptions):
    fields = ('name',)


@register(ConservationStatus)
class ConservationStatusOptions(TranslationOptions):
    fields = ('name',)


@register(CommonName)
class CommonNameTranslationOptions(TranslationOptions):
    fields = ('name',)


@register(CatalogView)
class CatalogViewTranslationOptions(TranslationOptions):
    fields = ('status',)


@register(RegionDistributionView)
class RegionViewTranslationOptions(TranslationOptions):
    fields = ('region_name',)


@register(FinderView)
class FinderViewTranslationOptions(TranslationOptions):
    fields = ('name',)


@register(Binnacle)
class BinnacleTranslationOptions(TranslationOptions):
    fields = ('type_update', 'model', 'description', 'note')
