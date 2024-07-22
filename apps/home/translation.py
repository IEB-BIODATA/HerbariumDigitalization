from modeltranslation.translator import register, TranslationOptions

from apps.home.models import Alert


@register(Alert)
class AlertTranslationOptions(TranslationOptions):
    fields = ('message', )
