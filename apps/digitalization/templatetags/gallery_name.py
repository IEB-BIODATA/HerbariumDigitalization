from django import template

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
    return name.replace("gallery/", "")
