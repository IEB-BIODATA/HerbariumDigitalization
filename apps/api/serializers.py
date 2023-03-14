from rest_framework.serializers import HyperlinkedModelSerializer, ModelSerializer, CharField, ReadOnlyField, \
    SerializerMethodField
from apps.catalog.models import Species, Family, Genus, Habit, Synonymy, Region, Division, Class_name, Order, Status, \
    Ciclo, CommonName, ConservationState
from apps.digitalization.models import VoucherImported
from django.contrib.auth.models import User
from rest_framework import serializers


class StatusSerializer(HyperlinkedModelSerializer):
    class Meta:
        model = Status
        fields = ['id', 'name', ]


class CicloSerializer(HyperlinkedModelSerializer):
    class Meta:
        model = Ciclo
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


class HabitSerializer(HyperlinkedModelSerializer):
    class Meta:
        model = Habit
        fields = ['id', 'name', ]


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


class ConservationStateSerializer(HyperlinkedModelSerializer):
    class Meta:
        model = ConservationState
        fields = ['id', 'name', 'key', 'order', ]


class SpecieSerializer(HyperlinkedModelSerializer):
    genus = ReadOnlyField(source='genus.name')
    genus_id = ReadOnlyField(source='genus.id')
    habito = ReadOnlyField(source='habito.name')
    ciclo = ReadOnlyField(source='ciclo.name')
    status = ReadOnlyField(source='status.name')
    synonymys = SynonymysSerializer(required=False, many=True)
    region_distribution = RegionSerializer(required=False, many=True)
    created_by = ReadOnlyField(source='created_by.username')
    family = ReadOnlyField(source='genus.family.name')
    family_id = ReadOnlyField(source='genus.family.id')
    orden = ReadOnlyField(source='genus.family.orden.name')
    orden_id = ReadOnlyField(source='genus.family.orden.id')
    class_name = ReadOnlyField(source='genus.family.orden.class_name.name')
    class_name_id = ReadOnlyField(source='genus.family.orden.class_name.id')
    division = ReadOnlyField(source='genus.family.orden.class_name.division.name')
    division_id = ReadOnlyField(source='genus.family.orden.class_name.division.id')
    kingdom = ReadOnlyField(source='genus.family.orden.class_name.division.kingdom.name')
    common_names = CommonNameSerializer(required=False, many=True)
    conservation_state = ConservationStateSerializer(required=False, many=True)
    vouchers = SerializerMethodField()

    class Meta:
        model = Species
        fields = ['id', 'id_taxa', 'kingdom', 'division', 'division_id', 'class_name', 'class_name_id', 'orden',
                  'orden_id', 'family', 'family_id', 'genus', 'genus_id', 'scientificName', 'scientificNameDB',
                  'scientificNameFull', 'specificEpithet', 'scientificNameAuthorship', 'subespecie', 'autoresSsp',
                  'variedad', 'autoresVariedad', 'forma', 'autoresForma', 'common_names', 'enArgentina', 'enBolivia',
                  'enPeru', 'habito', 'ciclo', 'status', 'alturaMinima', 'alturaMaxima', 'notas', 'id_tipo',
                  'publicacion', 'volumen', 'paginas', 'anio', 'synonymys', 'region_distribution', 'created_at',
                  'updated_at', 'created_by', 'determined', 'id_taxa_origin', 'conservation_state', 'id_mma',
                  'vouchers']

    def get_vouchers(self, obj):
        vouchers = obj.voucherimported_set.all().exclude(image_public_resized_10__exact='')[:5]
        response = VoucherSerializer(vouchers, many=True, context=self.context).data
        return response


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
    orden = ReadOnlyField(source='genus.family.orden.name')
    habit = ReadOnlyField(source='habito.name')
    vouchers = SerializerMethodField()

    class Meta:
        model = Species
        fields = ['id', 'name', 'genus', 'specificEpithet', 'family', 'orden', 'scientificNameAuthorship', 'habit',
                  'subespecie', 'autoresSsp', 'variedad', 'autoresVariedad', 'forma', 'autoresForma', 'vouchers']

    def get_vouchers(self, obj):
        vouchers = obj.voucherimported_set.all().exclude(image_public_resized_10__exact='')[:1]
        response = VoucherSerializer(vouchers, many=True, context=self.context).data
        return response


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


class CommonNameFinderSerializer(ModelSerializer):
    class Meta:
        model = CommonName
        fields = ['id', 'name', ]
