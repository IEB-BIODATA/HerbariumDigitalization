from import_export import resources

from .models import VoucherImported


class VoucherImportedAdminResource(resources.ModelResource):
    class Meta:
        model = VoucherImported
        fields = (
            'id',
            'vouchers_file',
            'occurrenceID',
            'herbarium',
            'otherCatalogNumbers',
            'catalogNumber',
            'recordedBy',
            'recordNumber',
            'organismRemarks',
            'scientificName',
            'locality',
            'verbatimElevation',
            'georeferencedDate',
            'decimalLatitude',
            'decimalLongitude',
            'identifiedBy',
            'dateIdentified',
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
