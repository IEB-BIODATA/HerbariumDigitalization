import os

from rest_framework.serializers import HyperlinkedModelSerializer, CharField, ReadOnlyField, SerializerMethodField

from apps.digitalization.models import VoucherImported, PriorityVouchersFile, GeneratedPage, BiodataCode, GalleryImage


class PriorityVouchersSerializer(HyperlinkedModelSerializer):
    herbarium = ReadOnlyField(source='herbarium.name')
    created_by = ReadOnlyField(source='created_by.username')
    file_url = SerializerMethodField()
    filename = SerializerMethodField()

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
    color_profile = SerializerMethodField()
    stateless_count = SerializerMethodField()
    found_count = SerializerMethodField()
    not_found_count = SerializerMethodField()
    digitalized = SerializerMethodField()
    qr_count = SerializerMethodField()

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
            "color_profile", "terminated",  # TODO: terminated -> finished
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


class VoucherSerializer(HyperlinkedModelSerializer):
    species = CharField(source='scientific_name')
    occurrence_id = SerializerMethodField()
    herbarium = ReadOnlyField(source='herbarium.name')
    herbarium_code = ReadOnlyField(source='herbarium.collection_code')
    priority_voucher = SerializerMethodField()
    image_voucher_url = SerializerMethodField()
    image_voucher_thumb_url = SerializerMethodField()
    image_voucher_cr3_raw_url = SerializerMethodField()
    image_voucher_jpg_raw_url = SerializerMethodField()
    image_voucher_jpg_raw_url_public = SerializerMethodField()

    class Meta:
        model = VoucherImported
        fields = [
            'id', 'occurrence_id', 'herbarium', 'herbarium_code',
            'other_catalog_numbers', 'catalog_number', 'recorded_by',
            'record_number', 'organism_remarks', 'species', 'locality',
            'verbatim_elevation', 'georeferenced_date', 'identified_by',
            'identified_date', 'image_public', 'image_public_resized_10',
            'image_public_resized_60', 'priority_voucher',
            'image_voucher_url', 'image_voucher_thumb_url',
            'image_voucher_cr3_raw_url', 'image_voucher_jpg_raw_url',
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