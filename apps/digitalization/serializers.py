import os
from rest_framework.serializers import HyperlinkedModelSerializer, CharField, ReadOnlyField, SerializerMethodField

from apps.catalog.models import Species
from apps.digitalization.models import VoucherImported, PriorityVouchersFile, GeneratedPage, BiodataCode, GalleryImage, \
    PostprocessingLog
from urllib.parse import urlparse

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
            "color_profile", "finished",
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

def build_iiif_jpg_url(iiif_url, width=2500):
    """
    Genera una URL JPG renderizable en HTML desde distintos formatos IIIF.
    Soporta:
    1) RBGE:
       https://iiif.rbge.org.uk/herb/iiif/E00000032/full/full/0/default.jpg
       Retorna:
       https://iiif.rbge.org.uk/herb/iiif/E00000032/full/2500,/0/default.jpg
    2) Cantaloupe info.json:
       https://cantaloupe.herbariodigital.cl/iiif/2/UDEC_CONC_0082518_public.jpg/info.json
       Retorna:
       https://cantaloupe.herbariodigital.cl/iiif/2/UDEC_CONC_0082518_public.jpg/full/2500,/0/default.jpg
    """
    if not iiif_url:
        return "#"
    iiif_url = str(iiif_url).strip()
    if not iiif_url:
        return "#"
    # Caso Cantaloupe /info.json
    if iiif_url.endswith("/info.json"):
        base = iiif_url.removesuffix("/info.json")
        return f"{base}/full/{width},/0/default.jpg"
    # Caso URL IIIF de imagen ya renderizable, por ejemplo:
    # .../full/full/0/default.jpg
    if "/full/" in iiif_url and "/0/default.jpg" in iiif_url:
        base = iiif_url.split("/full/")[0]
        return f"{base}/full/{width},/0/default.jpg"
    # Fallback: si viene como base del recurso IIIF sin info.json ni parámetros
    return f"{iiif_url.rstrip('/')}/full/{width},/0/default.jpg"

def build_iiif_info_url(iiif: str) -> str:
    """
    Normaliza una URL IIIF para que siempre apunte a info.json.
    Compatible con Cantaloupe, RBGE y URLs IIIF de imagen.
    """
    if not iiif:
        return ""
    url = iiif.strip()
    if not url:
        return ""
    if url.endswith("/info.json") or url.endswith("info.json"):
        return url
    parsed = urlparse(url)
    path_parts = parsed.path.strip("/").split("/")
    # Caso RBGE:
    # https://iiif.rbge.org.uk/herb/iiif/E00000032/full/full/0/default.jpg
    # https://iiif.rbge.org.uk/herb/iiif/E00000032/full/300,/0/default.jpg
    #
    # Resultado:
    # https://iiif.rbge.org.uk/herb/iiif/E00000032/info.json
    if "iiif" in path_parts:
        iiif_index = path_parts.index("iiif")

        if len(path_parts) > iiif_index + 2:
            if path_parts[iiif_index + 2] == "full":
                prefix = "/".join(path_parts[:iiif_index + 2])
                return f"{parsed.scheme}://{parsed.netloc}/{prefix}/info.json"
    # Caso genérico:
    # .../full/full/0/default.jpg
    # .../full/2500,/0/default.jpg
    if "/full/" in url:
        return url.split("/full/")[0].rstrip("/") + "/info.json"
    return url

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
    image_resized_60 = SerializerMethodField()

    class Meta:
        model = VoucherImported
        fields = [
            'id', 'occurrence_id', 'herbarium', 'herbarium_code',
            'other_catalog_numbers', 'catalog_number', 'recorded_by',
            'record_number', 'organism_remarks', 'species', 'locality',
            'verbatim_elevation', 'georeferenced_date', 'identified_by',
            'date_identified', 'image_public', 'image_public_resized_10',
            'image_public_resized_60', 'priority_voucher',
            'image_voucher_url', 'image_voucher_thumb_url',
            'image_voucher_cr3_raw_url', 'image_voucher_jpg_raw_url',
            'image_voucher_jpg_raw_url_public', 'image_resized_60',
        ]

    def get_occurrence_id(self, obj):
        return BiodataCodeSerializer(
            instance=obj.biodata_code,
            many=False,
            context=self.context
        ).data

    def get_priority_voucher(self, obj):
        return PriorityVouchersSerializer(
            instance=obj.vouchers_file,
            many=False,
            context=self.context
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

    def get_image_resized_60(self, obj):
        if herbarium.herbarium_type == 0:
            try:
                if obj.image_public_resized_60:
                    return obj.image_public_resized_60.url
            except Exception:
                pass
        else:
            return build_iiif_jpg_url(obj.iiif, width=2500)
        return "#"


class SpeciesGallerySerializer(HyperlinkedModelSerializer):
    division = ReadOnlyField(source='genus.family.order.classname.division.name')
    classname = ReadOnlyField(source='genus.family.order.classname.name')
    order = ReadOnlyField(source='genus.family.order.name')
    family = ReadOnlyField(source='genus.family.name')
    gallery_images = SerializerMethodField()

    class Meta:
        model = Species
        fields = [
            "unique_taxon_id", "division", "classname", "order", "family",
            "scientific_name_full", "updated_at", "gallery_images"
        ]

    def get_gallery_images(self, obj: Species) -> int:
        return obj.galleryimage_set.count()


class GallerySerializer(HyperlinkedModelSerializer):
    species = ReadOnlyField(source='scientific_name')
    licence = ReadOnlyField(source='licence.short_name')
    upload_by = ReadOnlyField(source='upload_by.username')
    specimen = ReadOnlyField(source='specimen.code')

    class Meta:
        model = GalleryImage
        fields = [
            'id', 'species', 'image', 'thumbnail', 'aspect_ratio',
            'specimen', 'taken_by', 'licence', 'upload_by', 'upload_at',
        ]


class PostprocessingLogSerializer(HyperlinkedModelSerializer):
    created_by = ReadOnlyField(source='created_by.username')
    file_name = SerializerMethodField()
    file_url = SerializerMethodField()

    class Meta:
        model = PostprocessingLog
        fields = [
            'id', 'date', 'file_name', 'file_url',
            'found_images', 'processed_images', 'failed_images',
            'scheduled', 'created_by',
        ]

    def get_file_name(self, obj):
        return obj.file.name

    def get_file_url(self, obj):
        return obj.file.url
