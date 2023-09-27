import os
from typing import Union, List

from django.contrib.auth.models import User
from rest_framework import serializers
from rest_framework.serializers import HyperlinkedModelSerializer, ModelSerializer, CharField, ReadOnlyField, \
    SerializerMethodField, URLField

from apps.catalog.models import Species, Family, Genus, Synonymy, Region, Division, ClassName, Order, Status, \
    CommonName, ConservationState, PlantHabit, EnvironmentalHabit, Cycle, TaxonomicModel, CatalogView, Binnacle
from apps.digitalization.models import VoucherImported, GalleryImage, BiodataCode, GeneratedPage, ColorProfileFile, \
    PriorityVouchersFile


class StatusSerializer(HyperlinkedModelSerializer):
    class Meta:
        model = Status
        fields = ['id', 'name', ]


class CycleSerializer(HyperlinkedModelSerializer):
    class Meta:
        model = Cycle
        fields = ['id', 'name', ]


class TaxonomicSerializer(HyperlinkedModelSerializer):
    created_by = ReadOnlyField(source='created_by.username')

    class Meta:
        model = TaxonomicModel
        fields = ['id', 'created_by', 'created_at', 'updated_at', ]
        abstract = True


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
        model = Family
        fields = TaxonomicSerializer.Meta.fields + ['name', 'family']


class PlantHabitSerializer(HyperlinkedModelSerializer):
    class Meta:
        model = PlantHabit
        fields = ["id", "name", ]


class EnvHabitSerializer(HyperlinkedModelSerializer):
    class Meta:
        model = EnvironmentalHabit
        fields = ["id", "female_name", "male_name", ]


class SpeciesSerializer(TaxonomicSerializer):
    genus = ReadOnlyField(source='genus.name')

    class Meta:
        model = Species
        fields = TaxonomicSerializer.Meta.fields + ['scientific_name', 'genus']


class CatalogViewSerializer(HyperlinkedModelSerializer):

    class Meta:
        model = CatalogView
        fields = TaxonomicSerializer.Meta.fields + [
            'division', 'class_name', 'order', 'family',
            'scientific_name_full', 'status', 'determined',
        ]


class SynonymysSerializer(TaxonomicSerializer):
    species = SerializerMethodField()

    class Meta:
        model = Synonymy
        fields = TaxonomicSerializer.Meta.fields + [
            'scientific_name', 'scientific_name_full',
            'species'
        ]

    def get_species(self, obj):
        species = obj.species_set.all()
        return "\t".join([specie.scientific_name for specie in species])


class RegionSerializer(HyperlinkedModelSerializer):
    class Meta:
        model = Region
        fields = ['id', 'name', ]


class CommonNameSerializer(TaxonomicSerializer):
    species = SerializerMethodField()

    class Meta:
        model = CommonName
        fields = TaxonomicSerializer.Meta.fields + ['name', 'species']

    def get_species(self, obj):
        species = obj.species_set.all()
        return "\t".join([specie.scientific_name for specie in species])


class BinnacleSerializer(TaxonomicSerializer):
    class Meta:
        model = Binnacle
        fields = TaxonomicSerializer.Meta.fields + [
            'type_update', 'model', 'description', 'note',
        ]


class UserSerializer(HyperlinkedModelSerializer):
    class Meta:
        model = User
        fields = ['id', 'username', ]


class VoucherSerializer(HyperlinkedModelSerializer):
    species = CharField(source='scientific_name')
    herbarium = ReadOnlyField(source='herbarium.name')
    herbarium_code = ReadOnlyField(source='herbarium.collection_code')

    class Meta:
        model = VoucherImported
        fields = ['id', 'herbarium', 'herbarium_code', 'other_catalog_numbers', 'catalog_number', 'recorded_by',
                  'record_number', 'organism_remarks', 'species', 'locality', 'verbatim_elevation', 'georeferenced_date',
                  'identified_by', 'identified_date', 'image_public', 'image_public_resized_10',
                  'image_public_resized_60']


class PriorityVouchersSerializer(HyperlinkedModelSerializer):
    herbarium = ReadOnlyField(source='herbarium.name')
    created_by = ReadOnlyField(source='created_by.username')
    file_url = serializers.SerializerMethodField()
    filename = serializers.SerializerMethodField()

    def get_file_url(self, obj):
        return obj.file.url

    def get_filename(self, obj):
        return os.path.basename(obj.file.name)

    class Meta:
        model = PriorityVouchersFile
        fields = [
            'herbarium', 'file_url', 'filename',
            'created_at', 'created_by',
        ]


class GeneratedPageSerializer(HyperlinkedModelSerializer):
    created_by = ReadOnlyField(source='created_by.username')
    herbarium = CharField(source='herbarium.name')
    color_profile = serializers.SerializerMethodField()
    stateless_count = serializers.SerializerMethodField()
    found_count = serializers.SerializerMethodField()
    not_found_count = serializers.SerializerMethodField()
    digitalized = serializers.SerializerMethodField()
    qr_count = serializers.SerializerMethodField()

    def get_total(self, obj):
        return obj.total

    def get_stateless_count(self, obj):
        return obj.stateless_count

    def get_found_count(self, obj):
        return obj.found_count

    def get_not_found_count(self, obj):
        return obj.not_found_count

    def get_digitalized(self, obj):
        return obj.digitalized

    def get_color_profile(self, obj):
        if obj.color_profile:
            return obj.color_profile.file.url
        else:
            return None

    def get_qr_count(self, obj):
        return obj.qr_count

    class Meta:
        model = GeneratedPage
        fields = [
            "id", "name", "herbarium",
            "created_by", "created_at",
            "color_profile", "terminated",
            "total", "stateless_count", "found_count",
            "not_found_count", "digitalized", "qr_count"
        ]


class BiodataCodeSerializer(HyperlinkedModelSerializer):
    voucher_state_name = SerializerMethodField()

    class Meta:
        model = BiodataCode
        fields = [
            "id", "voucher_state", "voucher_state_name", "code",
        ]

    def get_voucher_state_name(self, obj):
        return obj.get_voucher_state_display()


class MinimizedVoucherSerializer(HyperlinkedModelSerializer):
    species = CharField(source='scientific_name')
    occurrence_id = SerializerMethodField()
    priority_voucher = SerializerMethodField()
    image_voucher_url = SerializerMethodField()
    image_voucher_thumb_url = SerializerMethodField()
    image_voucher_cr3_raw_url = SerializerMethodField()
    image_voucher_jpg_raw_url = SerializerMethodField()
    image_voucher_jpg_raw_url_public = SerializerMethodField()

    class Meta:
        model = VoucherImported
        fields = [
            'id', 'occurrence_id', 'catalog_number',
            'recorded_by', 'record_number',
            'species', 'locality',
            'priority_voucher',
            'image_voucher_url',
            'image_voucher_thumb_url',
            'image_voucher_cr3_raw_url',
            'image_voucher_jpg_raw_url',
            'image_voucher_jpg_raw_url_public',
        ]

    def get_occurrence_id(self, obj):
        return BiodataCodeSerializer(
            instance=obj.biodata_code,
            many=False,
        ).data

    def get_priority_voucher(self, obj):
        return PriorityVouchersSerializer(
            instance=obj.vouchers_file,
            many=False,
        ).data

    def get_image_voucher_url(self, obj):
        return obj.image_voucher_url()

    def get_image_voucher_thumb_url(self, obj):
        return obj.image_voucher_thumb_url()

    def get_image_voucher_cr3_raw_url(self, obj):
        return obj.image_voucher_cr3_raw_url()

    def get_image_voucher_jpg_raw_url(self, obj):
        return obj.image_voucher_jpg_raw_url()

    def get_image_voucher_jpg_raw_url_public(self, obj):
        return obj.image_voucher_jpg_raw_url_public()


class GallerySerializer(HyperlinkedModelSerializer):
    species = CharField(source='scientific_name')

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
    synonyms = SynonymysSerializer(required=False, many=True)
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
                  'order_id', 'family', 'family_id', 'genus', 'genus_id', 'scientific_name', 'scientific_name_db',
                  'scientific_name_full', 'specific_epithet', 'scientific_name_authorship', 'subspecies', 'ssp_authorship',
                  'variety', 'variety_authorship', 'form', 'form_authorship', 'common_names', 'in_argentina', 'in_bolivia',
                  'in_peru', 'habit', 'cycle', 'status', 'minimum_height', 'maximum_height', 'notes', 'type_id',
                  'publication', 'volume', 'pages', 'year', 'synonyms', 'region', 'created_at',
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
        fields = ['id', 'species', 'genus', 'scientific_name', 'scientific_name_db', 'scientific_name_full',
                  'specific_epithet', 'scientific_name_authorship', 'subspecies', 'ssp_authorship', 'variety',
                  'variety_authorship', 'form', 'form_authorship', 'created_at', 'updated_at', 'created_by']

    def get_species(self, obj):
        species = obj.species_set.all()
        response = SpecieSerializer(species, many=True).data
        return response


class SpeciesFinderSerializer(ModelSerializer):
    name = CharField(source='scientific_name')
    genus = CharField(source='genus.name')
    family = ReadOnlyField(source='genus.family.name')
    order = ReadOnlyField(source='genus.family.order.name')
    habit = SerializerMethodField()
    vouchers = SerializerMethodField()

    class Meta:
        model = Species
        fields = [
            'id', 'name', 'genus', 'specific_epithet',
            'family', 'order', 'scientific_name_authorship',
            'habit', 'subspecies', 'ssp_authorship',
            'variety', 'variety_authorship', 'form',
            'form_authorship', 'vouchers', 'determined'
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
    name = CharField(source='scientific_name')
    species = SerializerMethodField()

    class Meta:
        model = Synonymy
        fields = ['id', 'name', 'genus', 'specific_epithet', 'scientific_name_authorship', 'species', 'subspecies',
                  'ssp_authorship', 'variety', 'variety_authorship', 'form', 'form_authorship']

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
        fields = ['decimal_latitude_public', 'decimal_longitude_public', ]


class ImagesSerializer(HyperlinkedModelSerializer):
    name = CharField(source='scientific_name')
    specie_id = CharField(source='scientific_name.id')
    image_name = CharField(source='image_public.name')
    herbarium_code = CharField(source='herbarium.collection_code')
    georeferenced_date = serializers.DateTimeField(format="%d-%m-%Y")

    class Meta:
        model = VoucherImported
        fields = ['id', 'name', 'specie_id', 'herbarium_code', 'image_public', 'image_public_resized_10',
                  'image_public_resized_60', 'image_name', 'catalog_number', 'recorded_by', 'record_number',
                  'organism_remarks', 'locality', 'identified_by', 'identified_date', 'georeferenced_date']


class GalleryPhotosSerializer(HyperlinkedModelSerializer):
    name = CharField(source='scientific_name.scientific_name')

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
