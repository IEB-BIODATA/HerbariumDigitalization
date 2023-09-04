from import_export import resources

from .models import VoucherImported


class VoucherImportedAdminResource(resources.ModelResource):
    class Meta:
        model = VoucherImported
        fields = (
            'id',
            'vouchers_file',
            'biodata_code',
            'herbarium',
            'other_catalog_numbers',
            'catalog_number',
            'recorded_by',
            'record_number',
            'organism_remarks',
            'scientific_name',
            'locality',
            'verbatim_elevation',
            'georeference_date',
            'decimal_latitude',
            'decimal_longitude',
            'identified_by',
            'identified_date',
            'image',
            'image_resized_10',
            'image_resized_60',
            'image_public',
            'image_public_resized_10',
            'image_public_resized_60',
            'image_raw',
            'point',

        )
        export_order = fields
