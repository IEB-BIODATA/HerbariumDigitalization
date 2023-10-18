import logging
from typing import List
from django import template
from django.db.models import QuerySet

register = template.Library()


@register.filter
def join_with_or(obj_list: List[QuerySet]) -> str:
    """
    Generates a string joining all elements on a list

    Parameters
    ----------
    obj_list : List[QuerySet]
        List of query set to be join on template

    Returns
    -------
    str
        Joined string
    """
    return " o ".join(
        [obj.name for obj in obj_list]
    )
