from modeltranslation.translator import register, TranslationOptions

from .models import Herbarium, GeneratedPage, Licence, Area, ProtectedArea, TemporalArea


@register(GeneratedPage)
class PageTranslationOptions(TranslationOptions):
    fields = ('name',)


@register(Licence)
class LicenceTranslationOptions(TranslationOptions):
    fields = ('name',)


@register(Area)
class AreasTranslationOptions(TranslationOptions):
    fields = ('name',)


@register(ProtectedArea)
class ProtectedAreaOptions(TranslationOptions):
    fields = ('category',)


@register(TemporalArea)
class TemporalAreaTranslationOptions(TranslationOptions):
    pass
