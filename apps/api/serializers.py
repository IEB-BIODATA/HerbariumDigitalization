from typing import Union, List

from django.contrib.auth.models import User
from rest_framework import serializers
from rest_framework.serializers import HyperlinkedModelSerializer, ModelSerializer, CharField, ReadOnlyField, \
    SerializerMethodField

from apps.catalog.models import Species, Family, Genus, Synonymy, Region, Division, Class_name, Order, Status, \
    CommonName, ConservationState, PlantHabit, EnvironmentalHabit, Cycle
from apps.digitalization.models import VoucherImported, GalleryImage


class StatusSerializer(HyperlinkedModelSerializer):
    class Meta:
        model = Status
        fields = ['id', 'name', ]


class CycleSerializer(HyperlinkedModelSerializer):
    class Meta:
        model = Cycle
        fields = ['id', 'name', ]


class DivisionSerializer(HyperlinkedModelSerializer):
    class Meta:
        model = Division
        fields = ['id', 'name', ]


class ClassSerializer(HyperlinkedModelSerializer):
    class Meta:
        model = Class_name
        fields = ['id', 'name', ]


class OrderSerializer(HyperlinkedModelSerializer):
    class Meta:
        model = Order
        fields = ['id', 'name', ]


class FamilySerializer(HyperlinkedModelSerializer):
    class Meta:
        model = Family
        fields = ['id', 'name', ]


class PlantHabitSerializer(HyperlinkedModelSerializer):
    class Meta:
        model = PlantHabit
        fields = ["id", "name", ]


class EnvHabitSerializer(HyperlinkedModelSerializer):
    class Meta:
        model = EnvironmentalHabit
        fields = ["id", "female_name", "male_name", ]


class SpeciesSerializer(HyperlinkedModelSerializer):
    class Meta:
        model = Species
        fields = ['id', 'scientificName', ]


class SynonymysSerializer(HyperlinkedModelSerializer):
    class Meta:
        model = Synonymy
        fields = ['id', 'scientificName', 'scientificNameFull', ]


class RegionSerializer(HyperlinkedModelSerializer):
    class Meta:
        model = Region
        fields = ['id', 'name', ]


class CommonNameSerializer(HyperlinkedModelSerializer):
    class Meta:
        model = CommonName
        fields = ['id', 'name', ]


class UserSerializer(HyperlinkedModelSerializer):
    class Meta:
        model = User
        fields = ['id', 'username', ]


class VoucherSerializer(HyperlinkedModelSerializer):
    species = CharField(source='scientificName')
    herbarium = ReadOnlyField(source='herbarium.name')
    herbarium_code = ReadOnlyField(source='herbarium.collection_code')

    class Meta:
        model = VoucherImported
        fields = ['id', 'herbarium', 'herbarium_code', 'otherCatalogNumbers', 'catalogNumber', 'recordedBy',
                  'recordNumber', 'organismRemarks', 'species', 'locality', 'verbatimElevation', 'georeferencedDate',
                  'identifiedBy', 'dateIdentified', 'image_public', 'image_public_resized_10',
                  'image_public_resized_60']


class GallerySerializer(HyperlinkedModelSerializer):
    species = CharField(source='scientificName')

    class Meta:
        model = GalleryImage
        fields = ['id', 'species', 'image', 'taken_by', 'upload_at', ]  # 'licence', ]


class ConservationStateSerializer(HyperlinkedModelSerializer):
    class Meta:
        model = ConservationState
        fields = ['id', 'name', 'key', 'order', ]


class SpecieSerializer(HyperlinkedModelSerializer):
    genus = ReadOnlyField(source='genus.name')
    genus_id = ReadOnlyField(source='genus.id')
    habit = SerializerMethodField()
    cycle = SerializerMethodField()
    status = ReadOnlyField(source='status.name')
    synonymys = SynonymysSerializer(required=False, many=True)
    region = RegionSerializer(required=False, many=True)
    created_by = ReadOnlyField(source='created_by.username')
    family = ReadOnlyField(source='genus.family.name')
    family_id = ReadOnlyField(source='genus.family.id')
    order = ReadOnlyField(source='genus.family.order.name')
    order_id = ReadOnlyField(source='genus.family.order.id')
    class_name = ReadOnlyField(source='genus.family.order.class_name.name')
    class_name_id = ReadOnlyField(source='genus.family.order.class_name.id')
    division = ReadOnlyField(source='genus.family.order.class_name.division.name')
    division_id = ReadOnlyField(source='genus.family.order.class_name.division.id')
    kingdom = ReadOnlyField(source='genus.family.order.class_name.division.kingdom.name')
    common_names = CommonNameSerializer(required=False, many=True)
    conservation_state = ConservationStateSerializer(required=False, many=True)
    vouchers = SerializerMethodField()
    gallery_images = SerializerMethodField()

    class Meta:
        model = Species
        fields = ['id', 'id_taxa', 'kingdom', 'division', 'division_id', 'class_name', 'class_name_id', 'order',
                  'order_id', 'family', 'family_id', 'genus', 'genus_id', 'scientificName', 'scientificNameDB',
                  'scientificNameFull', 'specificEpithet', 'scientificNameAuthorship', 'subespecie', 'autoresSsp',
                  'variedad', 'autoresVariedad', 'forma', 'autoresForma', 'common_names', 'enArgentina', 'enBolivia',
                  'enPeru', 'habit', 'cycle', 'status', 'alturaMinima', 'alturaMaxima', 'notas', 'id_tipo',
                  'publicacion', 'volumen', 'paginas', 'anio', 'synonymys', 'region', 'created_at',
                  'updated_at', 'created_by', 'determined', 'id_taxa_origin', 'conservation_state', 'id_mma',
                  'vouchers', 'gallery_images']

    def get_vouchers(self, obj):
        vouchers = obj.voucherimported_set.all().exclude(image_public_resized_10__exact='')
        count = len(vouchers)
        vouchers = vouchers[:5]
        response = {
            "count": count,
            "images": VoucherSerializer(vouchers, many=True, context=self.context).data
        }
        return response

    def get_gallery_images(self, obj):
        galleries_entries = obj.galleryimage_set.all()
        count = len(galleries_entries)
        galleries_entries = galleries_entries[:4]
        response = {
            "count": count,
            "gallery": GallerySerializer(galleries_entries, many=True, context=self.context).data
        }
        return response

    def get_habit(self, obj):
        plant_habit = obj.plant_habit.all()
        if len(list(plant_habit)) > 0:
            env_habit = get_habit_name(
                obj.env_habit.all(),
                env=True,
                plant_habit=list(plant_habit)[-1]
            )
            if env_habit != "":
                return "{} {}".format(get_habit_name(plant_habit), env_habit)
            else:
                return get_habit_name(plant_habit)
        else:
            return ""

    def get_cycle(self, obj):
        cycles = list(obj.cycle.all())
        if len(cycles) == 0:
            return ""
        elif len(cycles) == 1:
            return cycles[0].name
        else:
            return " o ".join([
                cycle.name if i == 0 else cycle.name.lower()
                for i, cycle in enumerate(cycles)
            ])


class SynonymySerializer(HyperlinkedModelSerializer):
    created_by = UserSerializer(required=False)
    species = SerializerMethodField()

    class Meta:
        model = Synonymy
        fields = ['id', 'species', 'genus', 'scientificName', 'scientificNameDB', 'scientificNameFull',
                  'specificEpithet', 'scientificNameAuthorship', 'subespecie', 'autoresSsp', 'variedad',
                  'autoresVariedad', 'forma', 'autoresForma', 'created_at', 'updated_at', 'created_by']

    def get_species(self, obj):
        species = obj.species_set.all()
        response = SpecieSerializer(species, many=True).data
        return response


class SpeciesFinderSerializer(ModelSerializer):
    name = CharField(source='scientificName')
    genus = CharField(source='genus.name')
    family = ReadOnlyField(source='genus.family.name')
    order = ReadOnlyField(source='genus.family.order.name')
    habit = SerializerMethodField()
    vouchers = SerializerMethodField()

    class Meta:
        model = Species
        fields = [
            'id', 'name', 'genus', 'specificEpithet',
            'family', 'order', 'scientificNameAuthorship',
            'habit', 'subespecie', 'autoresSsp',
            'variedad', 'autoresVariedad', 'forma',
            'autoresForma', 'vouchers', 'determined'
        ]

    def get_vouchers(self, obj):
        vouchers = obj.voucherimported_set.all().exclude(image_public_resized_10__exact='')[:1]
        response = VoucherSerializer(vouchers, many=True, context=self.context).data
        return response

    def get_habit(self, obj):
        plant_habit = obj.plant_habit.all()
        if len(list(plant_habit)) > 0:
            env_habit = get_habit_name(
                obj.env_habit.all(),
                env=True,
                plant_habit=list(plant_habit)[-1]
            )
            if env_habit != "":
                return "{} {}".format(get_habit_name(plant_habit), env_habit)
            else:
                return get_habit_name(plant_habit)
        else:
            return ""


class SynonymysFinderSerializer(ModelSerializer):
    name = CharField(source='scientificName')
    species = SerializerMethodField()

    class Meta:
        model = Synonymy
        fields = ['id', 'name', 'genus', 'specificEpithet', 'scientificNameAuthorship', 'species', 'subespecie',
                  'autoresSsp', 'variedad', 'autoresVariedad', 'forma', 'autoresForma']

    def get_species(self, obj):
        species = obj.species_set.all()
        try:
            response = SpeciesFinderSerializer(species, many=True).data[0]
        except:
            response = None
        return response


class FamilysFinderSerializer(ModelSerializer):
    class Meta:
        model = Family
        fields = ['id', 'name', ]


class GenusFinderSerializer(ModelSerializer):
    class Meta:
        model = Genus
        fields = ['id', 'name', ]


class DistributionSerializer(ModelSerializer):
    class Meta:
        model = VoucherImported
        fields = ['decimalLatitude_public', 'decimalLongitude_public', ]


class ImagesSerializer(HyperlinkedModelSerializer):
    name = CharField(source='scientificName')
    specie_id = CharField(source='scientificName.id')
    image_name = CharField(source='image_public.name')
    herbarium_code = CharField(source='herbarium.collection_code')
    georeferencedDate = serializers.DateTimeField(format="%d-%m-%Y")

    class Meta:
        model = VoucherImported
        fields = ['id', 'name', 'specie_id', 'herbarium_code', 'image_public', 'image_public_resized_10',
                  'image_public_resized_60', 'image_name', 'catalogNumber', 'recordedBy', 'recordNumber',
                  'organismRemarks', 'locality', 'identifiedBy', 'dateIdentified', 'georeferencedDate']


class GalleryPhotosSerializer(HyperlinkedModelSerializer):
    name = CharField(source='scientificName.scientificName')

    class Meta:
        model = GalleryImage
        fields = ['id', 'name', 'image']


class CommonNameFinderSerializer(ModelSerializer):
    class Meta:
        model = CommonName
        fields = ['id', 'name', ]


def get_habit_name(
        habit: List[Union[PlantHabit, EnvironmentalHabit]],
        env: bool = False,
        plant_habit: PlantHabit = None
) -> str:
    if len(habit) == 0:
        return ""
    elif len(habit) == 1:
        return env_habit_name(habit[0], plant_habit) if env else habit[0].name
    else:
        return "{} o {}".format(
            env_habit_name(habit[0], plant_habit) if env else habit[0].name,
            env_habit_name(habit[1], plant_habit) if env else habit[1].name,
        )


def env_habit_name(env_habit: EnvironmentalHabit, plant_habit: PlantHabit) -> str:
    if plant_habit.id == 3:
        return env_habit.female_name.lower()
    else:
        return env_habit.male_name.lower()
