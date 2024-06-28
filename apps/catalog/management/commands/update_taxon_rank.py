from django.core.management.base import BaseCommand

from apps.catalog.models import Species, Synonymy


class Command(BaseCommand):
    help = 'Update taxon rank fields for existing rows'

    def handle(self, *args, **kwargs):
        for obj in list(Species.objects.all()) + list(Synonymy.objects.all()):
            obj.save(force_update=True)
        self.stdout.write(self.style.SUCCESS('Successfully updated calculated fields'))
