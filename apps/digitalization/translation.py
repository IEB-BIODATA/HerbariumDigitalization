from modeltranslation.translator import register, TranslationOptions

from .models import Herbarium, GeneratedPage, Licence, Areas


@register(Herbarium)
class HerbariumTranslationOptions(TranslationOptions):
    fields = ('name',)


@register(GeneratedPage)
class PageTranslationOptions(TranslationOptions):
    fields = ('name',)


@register(Licence)
class LicenceTranslationOptions(TranslationOptions):
    fields = ('name',)


@register(Areas)
class AreasTranslationOptions(TranslationOptions):
    fields = ('name',)
