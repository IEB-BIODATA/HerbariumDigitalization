from typing import List

from rest_framework.fields import ReadOnlyField, SerializerMethodField
from rest_framework.serializers import ModelSerializer

from apps.catalog.models import CommonName, PlantHabit, EnvironmentalHabit, Status, Cycle, Region, ConservationState, \
    TaxonomicModel, Genus, Family, Order, ClassName, Division, CatalogView, Synonymy, Species, Binnacle, TaxonRank
from apps.catalog.utils import get_habit, get_cycle, get_conservation_state


class CommonSerializer(ModelSerializer):
    class Meta:
        fields = ['id', ]
        abstract = True


class AttributeSerializer(CommonSerializer):
    class Meta:
        fields = CommonSerializer.Meta.fields + ['name']
        abstract = True


class PlantHabitSerializer(AttributeSerializer):
    class Meta:
        model = PlantHabit
        fields = AttributeSerializer.Meta.fields


class EnvHabitSerializer(AttributeSerializer):
    class Meta:
        model = EnvironmentalHabit
        fields = AttributeSerializer.Meta.fields


class StatusSerializer(AttributeSerializer):
    class Meta:
        model = Status
        fields = AttributeSerializer.Meta.fields


class CycleSerializer(AttributeSerializer):
    class Meta:
        model = Cycle
        fields = AttributeSerializer.Meta.fields


class TaxonRankSerializer(AttributeSerializer):
    class Meta:
        model = TaxonRank
        fields = AttributeSerializer.Meta.fields


class RegionSerializer(AttributeSerializer):
    class Meta:
        model = Region
        fields = AttributeSerializer.Meta.fields


class ConservationStateSerializer(AttributeSerializer):
    class Meta:
        model = ConservationState
        fields = AttributeSerializer.Meta.fields + ['key']


class TaxonomicSerializer(CommonSerializer):
    created_by = ReadOnlyField(source='created_by.username')

    class Meta:
        model = TaxonomicModel
        fields = CommonSerializer.Meta.fields + ['created_by', 'created_at', 'updated_at', ]
        abstract = True


class CommonNameSerializer(TaxonomicSerializer):
    species = SerializerMethodField()

    class Meta:
        model = CommonName
        fields = TaxonomicSerializer.Meta.fields + ['name', 'species', ]

    def get_species(self, obj: CommonName) -> str:
        species = obj.species_set.all()
        return "\t".join([specie.scientific_name for specie in species])


class DivisionSerializer(TaxonomicSerializer):
    kingdom = ReadOnlyField(source='kingdom.name')

    class Meta:
        model = Division
        fields = TaxonomicSerializer.Meta.fields + ['name', 'kingdom']


class ClassSerializer(TaxonomicSerializer):
    division = ReadOnlyField(source='division.name')

    class Meta:
        model = ClassName
        fields = TaxonomicSerializer.Meta.fields + ['name', 'division']


class OrderSerializer(TaxonomicSerializer):
    class_name = ReadOnlyField(source='class_name.name')

    class Meta:
        model = Order
        fields = TaxonomicSerializer.Meta.fields + ['name', 'class_name']


class FamilySerializer(TaxonomicSerializer):
    order = ReadOnlyField(source='order.name')

    class Meta:
        model = Family
        fields = TaxonomicSerializer.Meta.fields + ['name', 'order']


class GenusSerializer(TaxonomicSerializer):
    family = ReadOnlyField(source='family.name')

    class Meta:
        model = Genus
        fields = TaxonomicSerializer.Meta.fields + ['name', 'family']


class CatalogViewSerializer(TaxonomicSerializer):
    created_by = ReadOnlyField()

    class Meta:
        model = CatalogView
        fields = TaxonomicSerializer.Meta.fields + [
            'division', 'class_name', 'order', 'family',
            'scientific_name_full', 'status', 'determined',
        ]


class SynonymsSerializer(TaxonomicSerializer):
    species = SerializerMethodField()

    class Meta:
        model = Synonymy
        fields = TaxonomicSerializer.Meta.fields + [
            'scientific_name',
            'scientific_name_full',
            'species'
        ]

    def get_species(self, obj):
        if obj.species is not None:
            return obj.species.scientific_name
        else:
            return ""


class SpeciesSerializer(TaxonomicSerializer):
    genus = SerializerMethodField()
    habit = SerializerMethodField()
    cycle = SerializerMethodField()
    conservation_state = SerializerMethodField()
    status = ReadOnlyField(source='status.name')
    synonyms = SynonymsSerializer(required=False, many=True)
    common_names = CommonNameSerializer(required=False, many=True)
    region = RegionSerializer(required=False, many=True)

    class Meta:
        model = Species
        fields = TaxonomicSerializer.Meta.fields + [
            'scientific_name', 'scientific_name_full', 'genus',
            'specific_epithet', 'scientific_name_authorship',
            'subspecies', 'ssp_authorship',
            'variety', 'variety_authorship',
            'form', 'form_authorship',
            'habit', 'cycle', 'status',
            'in_argentina', 'in_bolivia', 'in_peru',
            'minimum_height', 'maximum_height',
            'notes', 'type_id', 'publication',
            'volume', 'pages', 'year',
            'common_names', 'synonyms', 'region',
            'conservation_state', 'determined',
            'id_taxa_origin',
        ]

    def get_genus(self, obj: Species) -> str:
        return obj.genus.name

    def get_cycle(self, obj: Species) -> str:
        return get_cycle(obj)

    def get_habit(self, obj: Species) -> str:
        return get_habit(obj)

    def get_conservation_state(self, obj: Species) -> List[str]:
        return get_conservation_state(obj)


class BinnacleSerializer(TaxonomicSerializer):
    class Meta:
        model = Binnacle
        fields = TaxonomicSerializer.Meta.fields + [
            'type_update', 'model', 'description', 'note',
        ]
