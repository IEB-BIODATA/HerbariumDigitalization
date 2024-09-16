import logging

from copy import deepcopy

from django.contrib.contenttypes.models import ContentType
from django.utils.translation import gettext_lazy as _
from typing import List

from apps.catalog.models import Species, Habit


def get_habit(species: Species) -> str:
    plant_habit = species.plant_habit.all()
    env_habit = species.env_habit.all()
    if env_habit.count() == 0:
        habits = plant_habit
    else:
        habits = Habit.objects.filter(
            plant_habit__in=plant_habit,
            env_habit__in=env_habit
        )
    return _(' or ').join([habit.name for habit in habits])


def get_cycle(species: Species) -> str:
    return _(' or ').join([cycle.name for cycle in species.cycle.all()])


def get_conservation_status(species: Species) -> List[str]:
    return [f"{state.name} ({state.key})" for state in species.conservation_status.all()]


def get_children(species: Species) -> List[Species]:
    children = [species]
    new_children = Species.objects.filter(
        parent_content_type=ContentType.objects.get_for_model(Species),
        parent_taxon_id=species.unique_taxon_id
    )
    while len(new_children) > 0:
        children += new_children.all()
        grand_children = list()
        for new_child in new_children.all():
            grand_children += Species.objects.filter(
                parent_content_type=ContentType.objects.get_for_model(Species),
                parent_taxon_id=new_child.unique_taxon_id
            ).all()
        new_children = deepcopy(grand_children)
    return children
