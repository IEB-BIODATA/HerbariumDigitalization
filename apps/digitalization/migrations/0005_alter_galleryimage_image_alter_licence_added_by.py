# Generated by Django 4.1.7 on 2023-04-19 15:28

import apps.digitalization.storage_backends
from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('digitalization', '0004_bannerimage'),
    ]

    operations = [
        migrations.AlterField(
            model_name='galleryimage',
            name='image',
            field=models.ImageField(storage=apps.digitalization.storage_backends.PublicMediaStorage(), upload_to='gallery'),
        ),
        migrations.AlterField(
            model_name='licence',
            name='added_by',
            field=models.ForeignKey(default=1, editable=False, null=True, on_delete=django.db.models.deletion.SET_NULL, to=settings.AUTH_USER_MODEL),
        ),
    ]