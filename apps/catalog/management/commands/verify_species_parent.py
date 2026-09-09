from typing import List

from django.contrib.contenttypes.models import ContentType
from django.core.management.base import BaseCommand

from apps.catalog.models import Species, SpeciesQuerySet


def check_parent(possible_parent: SpeciesQuerySet, taxa: SpeciesQuerySet, command: "Command", new_parents: dict):
    command.stdout.write(command.style.HTTP_INFO(f'Checking {taxa.first().taxon_rank.name}'))
    for obj in taxa:
        parent = possible_parent.filter(genus=obj.genus, specific_epithet=obj.specific_epithet).all()
        if len(parent) == 0:
            command.stderr.write(command.style.WARNING(f'None possible parent on {obj}'))
            new_parent_name = f"{obj.genus.name} {obj.specific_epithet}"
            if new_parent_name in new_parents:
                new_parents[new_parent_name].append(obj)
            else:
                new_parents[new_parent_name] = [obj]
        elif len(parent) > 1:
            command.stderr.write(command.style.ERROR(f'More than one possible parent on {obj}'))
        else:
            official_parent = parent.first()
            if obj.parent != official_parent:
                command.stdout.write(command.style.HTTP_INFO(f'Different parent on {obj} (Family = {obj.family}), register {obj.parent}'))
                if official_parent.determined:
                    command.stdout.write(command.style.WARNING(
                        f'{official_parent} as terminal, changing')
                    )
                    official_parent.determined = False
                    official_parent.save(force_update=True)
            obj.parent_content_type = ContentType.objects.get_for_model(Species)
            obj.parent_taxon_id = official_parent.unique_taxon_id
            obj.save(force_update=True)


def generate_new_parent(new_parent_name: str, children: List[Species], command: "Command"):
    if len(children) > 1:
        command.stdout.write(command.style.HTTP_INFO(f"New species {new_parent_name}"))
        model_child = children[0]
        new_species = Species(
            genus=model_child.genus,
            specific_epithet=model_child.specific_epithet,
            scientific_name_authorship=model_child.scientific_name_authorship,
            in_argentina=any(child.in_argentina for child in children),
            in_bolivia=any(child.in_bolivia for child in children),
            in_peru=any(child.in_peru for child in children),
            determined=False,
            minimum_height=min(
                (child.minimum_height for child in children if child.minimum_height is not None),
                default=None
            ),
            maximum_height=max(
                (child.maximum_height for child in children if child.maximum_height is not None),
                default=None
            )
        )
        children_relations = {
            field.name: field.related_model.objects.filter(
                **{f"{field.related_query_name()}__in": children}
            ).distinct()
            for field in Species._meta.many_to_many
        }
        new_species.save(force_insert=True)
        for field_name, related in children_relations.items():
            getattr(new_species, field_name).set(related)
        new_species.save(force_update=True)
    else:
        command.stdout.write(command.style.HTTP_INFO(f"Just one children for {new_parent_name}"))

class Command(BaseCommand):
    help = 'Verify the parent of species models'

    def handle(self, *args, **kwargs):
        species = Species.objects.filter(taxon_rank=1)
        new_parents = dict()
        check_parent(species, Species.objects.filter(taxon_rank=2), self, new_parents)
        check_parent(species, Species.objects.filter(taxon_rank=3), self, new_parents)
        check_parent(species, Species.objects.filter(taxon_rank=4), self, new_parents)
        for new_parent_name, children in new_parents.items():
            generate_new_parent(new_parent_name, children, self)
