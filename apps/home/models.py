from django.conf import settings
from django.db import models
from django.contrib.auth.models import User
from django.utils.translation import gettext_lazy as _

THEMES = [
    ("light", _("Light")),
]


class Profile(models.Model):
    user = models.OneToOneField(User, on_delete=models.PROTECT)
    language = models.CharField(choices=settings.LANGUAGES, max_length=5, default="es", blank=False, null=True)
    theme = models.CharField(choices=THEMES, max_length=16, default="light", null=True, blank=True)
