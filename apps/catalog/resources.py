from import_export import resources, fields
from import_export.widgets import ManyToManyWidget

from .models import Species, Region, Synonymy


class SpeciesAdminResource(resources.ModelResource):
    region_distribution = fields.Field(attribute='region_distribution', widget=ManyToManyWidget(Region))
    synonymys = fields.Field(attribute='synonymys', widget=ManyToManyWidget(Synonymy))

    class Meta:
        model = Species
        import_id_fields = ('id',)
        fields = (
            'id',
            'id_taxa',
            'genus',
            'scientificName',
            'scientificNameDB',
            'scientificNameFull',
            'specificEpithet',
            'scientificNameAuthorship',
            'subespecie',
            'autoresSsp',
            'variedad',
            'autoresVariedad',
            'forma',
            'autoresForma',
            'common_names',
            'enArgentina',
            'enBolivia',
            'enPeru',
            'habito',
            'ciclo',
            'status',
            'alturaMinima',
            'alturaMaxima',
            'notas',
            'id_tipo',
            'publicacion',
            'volumen',
            'paginas',
            'anio',
            'synonymys',
            'region_distribution',
            'determined',
            'id_taxa_origin',
            'id_mma',
            'conservation_state',
            'created_at',
            'updated_at',
            'created_by',

        )
        export_order = fields
