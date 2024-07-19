# -*- coding: utf-8 -*-
from django.contrib import admin
from django.utils.translation import gettext_lazy as _, ngettext_lazy

from apps.home.forms import AlertForm
from apps.home.models import Alert


@admin.register(Alert)
class AlertAdmin(admin.ModelAdmin):
    form = AlertForm
    def alert_message(self, obj):
        return str(obj)

    alert_message.short_description = _('Message')
    list_display = (['alert_message', 'created_by', 'created_at', 'active'])

    def save_model(self, request, obj, form, change):
        obj.created_by = request.user
        obj.save()
