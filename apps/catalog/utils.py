from django.utils.translation import gettext_lazy as _
from typing import List

from apps.catalog.models import Species, Habit, EnvironmentalHabit


def get_habit(species: Species) -> str:
    plant_habit = species.plant_habit.all()
    env_habit = species.env_habit.all()
    if env_habit.count() == 0:
        env_habit = [EnvironmentalHabit.objects.get(pk=0)]
    habits = Habit.objects.filter(
        plant_habit__in=plant_habit,
        env_habit__in=env_habit
    )
    return _(' or ').join([habit.name for habit in habits])


def get_cycle(species: Species) -> str:
    return _(' or ').join([cycle.name for cycle in species.cycle.all()])


def get_conservation_state(species: Species) -> List[str]:
    return [f"{state.name} ({state.key})" for state in species.conservation_state.all()]