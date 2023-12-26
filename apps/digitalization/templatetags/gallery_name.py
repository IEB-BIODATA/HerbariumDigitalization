import logging

from django import template

from apps.digitalization.storage_backends import PublicMediaStorage

register = template.Library()


@register.filter
def replace_gallery_name(name: str) -> str:
    """
    Replaces gallery filename deleting the `gallery/` path

    Parameters
    ----------
    name : str
        Original filename of gallery

    Returns
    -------
    str
        Filename modified
    """
    base_url = PublicMediaStorage().url("")
    return name.replace(f"{base_url}gallery/", "")
