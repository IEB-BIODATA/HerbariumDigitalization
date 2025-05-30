from django.conf import settings
from django.db.models import Q
from drf_spectacular.utils import extend_schema_field
from rest_framework.serializers import HyperlinkedModelSerializer, ModelSerializer, CharField, ReadOnlyField, \
    SerializerMethodField, Serializer
from typing import Union, List, Dict

from apps.catalog.models import Species, Family, Genus, Synonymy, Division, ClassName, Order, CommonName, \
    TaxonomicModel, FinderView, ScientificName, Region, Kingdom
from apps.catalog.serializers import RegionSerializer, StatusSerializer
from apps.catalog.utils import get_habit, get_conservation_status, get_children
from apps.digitalization.models import VoucherImported, GalleryImage, Licence


class MinimumSerializer(Serializer):
    def to_representation(self, instance):
        try:
            id = instance.unique_taxon_id
        except AttributeError:
            id = instance.id
        return str(id), str(instance.name)


class RegionDetailsSerializer(RegionSerializer):
    class Meta:
        model = Region
        fields = RegionSerializer.Meta.fields + ['geometry']


class TaxonomicApiSerializer(ModelSerializer):
    class Meta:
        model = TaxonomicModel
        fields = ['taxon_id', 'unique_taxon_id', 'name']
        abstract = True


class CommonNameSerializer(ModelSerializer):
    class Meta:
        model = CommonName
        fields = ['id', 'name']
        read_only_fields = fields


class KingdomSerializer(TaxonomicApiSerializer):
    class Meta:
        model = Kingdom
        fields = TaxonomicApiSerializer.Meta.fields
        read_only_fields = fields


class DivisionSerializer(TaxonomicApiSerializer):
    class Meta:
        model = Division
        fields = TaxonomicApiSerializer.Meta.fields
        read_only_fields = fields


class ClassSerializer(TaxonomicApiSerializer):
    class Meta:
        model = ClassName
        fields = TaxonomicApiSerializer.Meta.fields
        read_only_fields = fields


class OrderSerializer(TaxonomicApiSerializer):
    class Meta:
        model = Order
        fields = TaxonomicApiSerializer.Meta.fields
        read_only_fields = fields


class FamilySerializer(TaxonomicApiSerializer):
    class Meta:
        model = Family
        fields = TaxonomicApiSerializer.Meta.fields
        read_only_fields = fields


class GenusSerializer(TaxonomicApiSerializer):
    class Meta:
        model = Genus
        fields = TaxonomicApiSerializer.Meta.fields
        read_only_fields = fields


class FinderSerializer(ModelSerializer):
    class Meta:
        model = FinderView
        fields = ['id', 'type', 'name', 'determined']


class ScientificNameSerializer(TaxonomicApiSerializer):
    name = CharField(source="scientific_name", read_only=True)
    taxon_rank = CharField(source="taxon_rank.name", read_only=True)
    taxonomic_status = SerializerMethodField()

    class Meta:
        model = ScientificName
        fields = TaxonomicApiSerializer.Meta.fields + [
            'scientific_name', 'genus',
            'specific_epithet', 'scientific_name_authorship',
            'subspecies', 'ssp_authorship',
            'variety', 'variety_authorship',
            'form', 'form_authorship',
            'taxonomic_status', 'taxon_rank'
        ]
        abstract = True


class SpeciesSerializer(ScientificNameSerializer):
    kingdom = ReadOnlyField(source='kingdom.name')
    division = DivisionSerializer()
    classname = ClassSerializer()
    genus = GenusSerializer()
    family = FamilySerializer()
    order = OrderSerializer()
    habit = SerializerMethodField()
    status = StatusSerializer()

    class Meta:
        model = Species
        fields = ScientificNameSerializer.Meta.fields + [
            'kingdom', 'division', 'classname',
            'family', 'order', 'habit', 'determined',
            'status',
        ]

    def get_habit(self, obj: Species) -> str:
        return get_habit(obj)

    def get_taxonomic_status(self, obj: Species) -> str:
        return "accepted"


serializer_registry = {
    Kingdom: KingdomSerializer,
    Division: DivisionSerializer,
    ClassName: ClassSerializer,
    Order: OrderSerializer,
    Family: FamilySerializer,
    Genus: GenusSerializer,
    Species: SpeciesSerializer,
}


class SampleSerializer(HyperlinkedModelSerializer):
    image_resized_10 = SerializerMethodField()
    image_resized_60 = SerializerMethodField()
    code = ReadOnlyField(source='biodata_code.code')

    class Meta:
        model = VoucherImported
        fields = ['id', 'code', 'image_resized_10', 'image_resized_60']

    def get_image_resized_10(self, obj: VoucherImported) -> str:
        try:
            return obj.image_public_resized_10.url
        except ValueError:
            return "#"

    def get_image_resized_60(self, obj: VoucherImported) -> str:
        try:
            return obj.image_public_resized_60.url
        except ValueError:
            return "#"


class SpeciesFinderSerializer(SpeciesSerializer):
    genus_name = CharField(source="genus.name", read_only=True)
    sample = SerializerMethodField()

    class Meta:
        model = Species
        fields = SpeciesSerializer.Meta.fields + [
            'genus_name', 'sample'
        ]
        read_only_fields = fields

    @extend_schema_field(SampleSerializer)
    def get_sample(self, obj: Species) -> Union[Dict, None]:
        sample = obj.voucherimported_set.exclude(
            Q(image_public_resized_10__isnull=True) |
            Q(image_public_resized_10__exact='')
        ).first()
        if sample is None:
            sample = VoucherImported.objects.filter(
                scientific_name__in=get_children(obj)
            ).exclude(
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
    species = SpeciesSerializer()
    genus_name = CharField(source="genus")

    class Meta:
        model = Synonymy
        fields = ScientificNameSerializer.Meta.fields + [
            'species', 'genus_name',
        ]

    def get_taxonomic_status(self, obj: Synonymy) -> str:
        return "synonym"


class LicenceSerializer(HyperlinkedModelSerializer):
    class Meta:
        model = Licence
        fields = [
            'id', 'name', 'short_name', 'link',
        ]


class GallerySerializer(HyperlinkedModelSerializer):
    licence = LicenceSerializer()

    class Meta:
        model = GalleryImage
        fields = [
            'id', 'image', 'thumbnail', 'aspect_ratio',
            'specimen', 'taken_by', 'licence',
        ]


class SpeciesDetailsSerializer(SpeciesSerializer):
    common_names = CommonNameSerializer(required=False, many=True)
    status = SerializerMethodField()
    conservation_status = SerializerMethodField()
    parent = SerializerMethodField()
    synonyms = SerializerMethodField()
    vouchers = SerializerMethodField()
    gallery_images = SerializerMethodField()
    herbarium_url = SerializerMethodField()
    region = RegionSerializer(required=False, many=True)

    class Meta:
        model = Species
        fields = SpeciesSerializer.Meta.fields + [
            'scientific_name_db', 'scientific_name_full',
            'parent', 'synonyms', 'common_names',
            'status', 'minimum_height', 'maximum_height', 'conservation_status', 'id_mma',
            'region', 'vouchers', 'gallery_images', 'herbarium_url',
        ]

    def get_status(self, obj: Species) -> Union[str, None]:
        try:
            return obj.status.name
        except AttributeError:
            return None

    def get_conservation_status(self, obj: Species) -> List[str]:
        return get_conservation_status(obj)

    def get_parent(self, obj: Species) -> Dict:
        parent_model = obj.parent
        serializer_class = serializer_registry[type(parent_model)]
        return serializer_class(parent_model).data

    def get_synonyms(self, obj: Species) -> List[str]:
        return [synonym.scientific_name_full for synonym in obj.synonyms.all()]

    def get_vouchers(self, obj: Species) -> SampleSerializer:
        children = get_children(obj)
        vouchers = VoucherImported.objects.filter(
            scientific_name__in=children
        ).exclude(
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

    def get_gallery_images(self, obj: Species) -> Dict:
        return GallerySerializer(
            instance=obj.galleryimage_set.all(),
            many=True, context=self.context
        ).data

    def get_herbarium_url(self, obj: Species) -> str:
        return f"{settings.HERBARIUM_FRONTEND}/catalog/details/species/{obj.id}"


class SynonymyDetailsSerializer(SynonymyFinderSerializer):
    species = SpeciesDetailsSerializer()

    class Meta:
        model = Synonymy
        fields = SynonymyFinderSerializer.Meta.fields + [
            'scientific_name_full'
        ]


class DistributionSerializer(SampleSerializer):
    code = ReadOnlyField(source="biodata_code.code")
    decimal_latitude = ReadOnlyField(source='decimal_latitude_public')
    decimal_longitude = ReadOnlyField(source='decimal_longitude_public')

    class Meta:
        model = VoucherImported
        fields = SampleSerializer.Meta.fields + [
            'code',
            'decimal_latitude',
            'decimal_longitude',
        ]


class SpecimenFinderSerializer(SampleSerializer):
    herbarium_code = ReadOnlyField(source='herbarium.collection_code')
    decimal_latitude = ReadOnlyField(source='decimal_latitude_public')
    decimal_longitude = ReadOnlyField(source='decimal_longitude_public')
    species = SpeciesSerializer(source='scientific_name')

    class Meta:
        model = VoucherImported
        fields = SampleSerializer.Meta.fields + [
            'herbarium_code',
            'catalog_number',
            'decimal_latitude',
            'decimal_longitude',
            'species',
        ]


class SpecimenDetailSerializer(SpecimenFinderSerializer):
    image = SerializerMethodField()

    class Meta:
        model = VoucherImported
        fields = SpecimenFinderSerializer.Meta.fields + [
            'image', 'recorded_by', 'georeferenced_date',
            'record_number', 'locality', 'identified_by',
            'date_identified', 'organism_remarks',
        ]

    def get_image(self, obj: VoucherImported) -> Dict[str, str]:
        return {
            'name': obj.image_public.name,
            'url': obj.image_public.url,
        }
