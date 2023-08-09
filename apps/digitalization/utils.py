from urllib.request import urlopen

from django.conf import settings
from django.contrib.staticfiles import finders

from apps.digitalization.storage_backends import StaticStorage


def get_static_file(file_path: str) -> str:
    if settings.DEBUG:
        return finders.find(file_path)
    else:
        storage = StaticStorage()
        return urlopen(storage.url(file_path))
