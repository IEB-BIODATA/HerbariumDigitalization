from django.contrib.contenttypes.models import ContentType
from django.core.management.base import BaseCommand

from apps.catalog.models import Species, SpeciesQuerySet


def check_parent(possible_parent: SpeciesQuerySet, taxa: SpeciesQuerySet, command: "Command"):
    command.stdout.write(command.style.HTTP_INFO(f'Checking {taxa.first().taxon_rank.name}'))
    for obj in taxa:
        parent = possible_parent.filter(genus=obj.genus, specific_epithet=obj.specific_epithet).all()
        if len(parent) == 0:
            command.stderr.write(command.style.WARNING(f'None possible parent on {obj}'))
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

class Command(BaseCommand):
    help = 'Verify the parent of species models'

    def handle(self, *args, **kwargs):
        species = Species.objects.filter(taxon_rank=1)
        check_parent(species, Species.objects.filter(taxon_rank=2), self)
        check_parent(species, Species.objects.filter(taxon_rank=3), self)
        check_parent(species, Species.objects.filter(taxon_rank=4), self)
