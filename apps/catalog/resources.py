from import_export import resources, fields
from import_export.widgets import ManyToManyWidget

from .models import Species, Region, Synonymy


class SpeciesAdminResource(resources.ModelResource):
    region = fields.Field(attribute='region', widget=ManyToManyWidget(Region))
    synonyms = fields.Field(attribute='synonyms', widget=ManyToManyWidget(Synonymy))

    class Meta:
        model = Species
        import_id_fields = ('id',)
        fields = (
            'id',
            'id_taxa',
            'genus',
            'scientific_name',
            'scientific_name_db',
            'scientific_name_full',
            'specific_epithet',
            'scientific_name_authorship',
            'subspecies',
            'ssp_authorship',
            'variety',
            'variety_authorship',
            'form',
            'form_authorship',
            'common_names',
            'in_argentina',
            'in_bolivia',
            'in_peru',
            'habit',
            'ciclo',
            'status',
            'minimum_height',
            'maximum_height',
            'notes',
            'type_id',
            'publication',
            'volume',
            'pages',
            'year',
            'synonyms',
            'region',
            'determined',
            'id_taxa_origin',
            'id_mma',
            'conservation_state',
            'created_at',
            'updated_at',
            'created_by',

        )
        export_order = fields
