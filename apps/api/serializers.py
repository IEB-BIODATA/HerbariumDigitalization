import logging
from django.conf import settings

from django.db.models import Q
from rest_framework import serializers
from rest_framework.serializers import HyperlinkedModelSerializer, ModelSerializer, CharField, ReadOnlyField, \
    SerializerMethodField

from apps.catalog.models import Species, Family, Genus, Synonymy, Division, ClassName, Order, CommonName, \
    TaxonomicModel, FinderView, ScientificName
from apps.catalog.serializers import CommonSerializer, StatusSerializer
from apps.catalog.utils import get_habit, get_conservation_state
from apps.digitalization.models import VoucherImported, GalleryImage
from apps.digitalization.serializers import GallerySerializer, VoucherSerializer


class TaxonomicApiSerializer(CommonSerializer):
    class Meta:
        model = TaxonomicModel
        fields = CommonSerializer.Meta.fields + ['name']
        abstract = True


class CommonNameSerializer(TaxonomicApiSerializer):
    class Meta:
        model = CommonName
        fields = TaxonomicApiSerializer.Meta.fields


class DivisionSerializer(TaxonomicApiSerializer):
    class Meta:
        model = Division
        fields = TaxonomicApiSerializer.Meta.fields


class ClassSerializer(TaxonomicApiSerializer):
    class Meta:
        model = ClassName
        fields = TaxonomicApiSerializer.Meta.fields


class OrderSerializer(TaxonomicApiSerializer):
    class Meta:
        model = Order
        fields = TaxonomicApiSerializer.Meta.fields


class FamilySerializer(TaxonomicApiSerializer):
    class Meta:
        model = Family
        fields = TaxonomicApiSerializer.Meta.fields


class GenusSerializer(TaxonomicApiSerializer):
    class Meta:
        model = Genus
        fields = TaxonomicApiSerializer.Meta.fields


class FinderSerializer(ModelSerializer):
    class Meta:
        model = FinderView
        fields = ['id', 'type', 'name', 'determined']


class ScientificNameSerializer(TaxonomicApiSerializer):
    name = CharField(source="scientific_name")

    class Meta:
        model = ScientificName
        fields = TaxonomicApiSerializer.Meta.fields + [
            'scientific_name', 'genus',
            'specific_epithet', 'scientific_name_authorship',
            'subspecies', 'ssp_authorship',
            'variety', 'variety_authorship',
            'form', 'form_authorship',
        ]
        abstract = True


class SpeciesSerializer(ScientificNameSerializer):
    kingdom = ReadOnlyField(source='genus.family.order.class_name.division.kingdom.name')
    division = DivisionSerializer()
    class_name = ClassSerializer()
    genus = GenusSerializer()
    family = FamilySerializer()
    order = OrderSerializer()
    habit = SerializerMethodField()

    class Meta:
        model = Species
        fields = ScientificNameSerializer.Meta.fields + [
            'kingdom', 'division', 'class_name',
            'family', 'order', 'habit', 'determined',
        ]

    def get_habit(self, obj):
        return get_habit(obj)


class SampleSerializer(HyperlinkedModelSerializer):
    image_resized_10 = SerializerMethodField()
    image_resized_60 = SerializerMethodField()

    class Meta:
        model = VoucherImported
        fields = ['id', 'image_resized_10', 'image_resized_60']

    def get_image_resized_10(self, obj: VoucherImported):
        try:
            return obj.image_public_resized_10.url
        except ValueError:
            return "#"

    def get_image_resized_60(self, obj: VoucherImported):
        try:
            return obj.image_public_resized_10.url
        except ValueError:
            return "#"


class SpeciesFinderSerializer(SpeciesSerializer):
    genus_name = CharField(source="genus.name")
    sample = SerializerMethodField()

    class Meta:
        model = Species
        fields = SpeciesSerializer.Meta.fields + [
            'genus_name', 'sample'
        ]

    def get_sample(self, obj):
        sample = obj.voucherimported_set.exclude(
            Q(image_public_resized_10__isnull=True) |
            Q(image_public_resized_10__exact='')
        ).first()
        if sample:
            return SampleSerializer(
                instance=sample, many=False, context=self.context
            ).data
        else:
            return None


class SynonymyFinderSerializer(ScientificNameSerializer):
    species = SerializerMethodField()
    genus_name = CharField(source="genus")

    class Meta:
        model = Synonymy
        fields = ScientificNameSerializer.Meta.fields + [
            'species', 'genus_name',
        ]

    def get_species(self, obj):
        return SpeciesSerializer(
            instance=obj.species_set.all(),
            many=True, context=self.context
        ).data


class SpeciesDetailsSerializer(SpeciesSerializer):
    common_names = CommonNameSerializer(required=False, many=True)
    status = SerializerMethodField()
    conservation_state = SerializerMethodField()
    synonyms = SerializerMethodField()
    vouchers = SerializerMethodField()
    gallery_images = SerializerMethodField()
    herbarium_url = SerializerMethodField()

    class Meta:
        model = Species
        fields = SpeciesSerializer.Meta.fields + [
            'scientific_name_db', 'scientific_name_full',
            'common_names', 'status', 'minimum_height', 'maximum_height',
            'conservation_state', 'id_mma',
            'synonyms', 'vouchers', 'gallery_images',
            'herbarium_url',
        ]

    def get_status(self, obj):
        return obj.status.name

    def get_conservation_state(self, obj):
        return get_conservation_state(obj)

    def get_synonyms(self, obj):
        return [synonym.scientific_name_full for synonym in obj.synonyms.all()]

    def get_vouchers(self, obj):
        vouchers = obj.voucherimported_set.exclude(
            Q(image_public_resized_10__isnull=True) |
            Q(image_public_resized_10__exact='') |
            Q(image_public_resized_60__isnull=True) |
            Q(image_public_resized_60__exact='') |
            Q(image_public__isnull=True) |
            Q(image_public__exact='')
        ).all()
        return SampleSerializer(
            instance=vouchers,
            many=True, context=self.context
        ).data

    def get_gallery_images(self, obj):
        return GallerySerializer(
            instance=obj.galleryimage_set.all(),
            many=True, context=self.context
        ).data

    def get_herbarium_url(self, obj):
        return f"{settings.HERBARIUM_FRONTEND}/catalog/details/species/{obj.id}"


class SynonymyDetailsSerializer(SynonymyFinderSerializer):

    class Meta:
        model = Synonymy
        fields = SynonymyFinderSerializer.Meta.fields + [
            'scientific_name_full'
        ]

    def get_species(self, obj):
        return SpeciesDetailsSerializer(
            instance=obj.species_set.all(),
            many=True,
            context=self.context
        ).data


class DistributionSerializer(SampleSerializer):
    decimal_latitude = ReadOnlyField(source='decimal_latitude_public')
    decimal_longitude = ReadOnlyField(source='decimal_longitude_public')

    class Meta:
        model = VoucherImported
        fields = SampleSerializer.Meta.fields + [
            'decimal_latitude',
            'decimal_longitude',
        ]


class SpecimenFinderSerializer(SampleSerializer):
    code = ReadOnlyField(source="biodata_code.code")
    herbarium_code = ReadOnlyField(source="herbarium.collection_code")
    species = SpeciesSerializer(source="scientific_name")

    class Meta:
        model = VoucherImported
        fields = SampleSerializer.Meta.fields + [
            "code",
            "herbarium_code",
            "catalog_number",
            "species",
        ]


class SpecimenDetailSerializer(SpecimenFinderSerializer):
    image = SerializerMethodField()

    class Meta:
        model = VoucherImported
        fields = SpecimenFinderSerializer.Meta.fields + [
            'image', 'recorded_by', 'georeferenced_date',
            'record_number', 'locality', 'identified_by',
            'identified_date', 'organism_remarks',
        ]

    def get_image(self, obj):
        return {
            'name': obj.image_public.name,
            'url': obj.image_public.url,
        }
