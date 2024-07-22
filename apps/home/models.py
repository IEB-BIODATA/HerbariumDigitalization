import datetime

from ckeditor.fields import RichTextField
from django.conf import settings
from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone
from django.utils.translation import gettext_lazy as _

THEMES = [
    ("light", _("Light")),
]


class Profile(models.Model):
    user = models.OneToOneField(User, on_delete=models.PROTECT)
    language = models.CharField(verbose_name=_("Language"), choices=settings.LANGUAGES, max_length=5, default="es", blank=False, null=True)
    theme = models.CharField(verbose_name=_("Theme"), choices=THEMES, max_length=16, default="light", null=True, blank=True)

    class Meta:
        verbose_name = _('Profile')
        verbose_name_plural = _('Profiles')


class Alert(models.Model):
    message = RichTextField(verbose_name=_("Message"), )
    active = models.BooleanField(verbose_name=_("Active"), default=True)
    created_by = models.ForeignKey(User, verbose_name=_("Created by"), on_delete=models.PROTECT)
    created_at = models.DateTimeField(verbose_name=_("Created at"), auto_now_add=True)

    class Meta:
        verbose_name = _('Alert')
        verbose_name_plural = _('Alerts')

    def __str__(self):
        return f"{self._meta.verbose_name}: `{self.message[0:20]}`"
