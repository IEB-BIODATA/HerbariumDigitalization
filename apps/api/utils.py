from drf_yasg import openapi
from rest_framework.request import Request

from apps.catalog.models import ATTRIBUTES, TAXONOMIC_RANK, CatalogQuerySet


def filter_query_set(queryset: CatalogQuerySet, request: Request) -> CatalogQuerySet:
    attribute_query = dict()
    for attribute in ATTRIBUTES:
        parameters = request.query_params.getlist(attribute, [])
        if len(parameters) > 0:
            # Adding small tree if tree is selected
            if attribute == "plant_habit" and "2" in parameters:
                parameters.append("5")
            attribute_query[attribute] = parameters.copy()
    taxonomic_query = dict()
    for taxonomic_rank in TAXONOMIC_RANK:
        parameters = request.query_params.getlist(taxonomic_rank, [])
        if len(parameters) > 0:
            taxonomic_query[taxonomic_rank] = parameters.copy()
    search = request.query_params.get("search")
    if search:
        return queryset.filter_query_in(**attribute_query).filter_taxonomy_in(**taxonomic_query).search(search)
    else:
        return queryset.filter_query_in(**attribute_query).filter_taxonomy_in(**taxonomic_query)


class OpenAPIQueryParameter(openapi.Parameter):
    __default_description__ = ("IDs of {0} to include. It can be search using the /{0} "
                               "endpoint and query parameter search")

    def __init__(self, name, description):
        super(OpenAPIQueryParameter, self).__init__(
            name=name, in_=openapi.IN_QUERY,
            description=description,
            type=openapi.TYPE_ARRAY,
            items=openapi.Items(type=openapi.TYPE_INTEGER),
            collection_format="multi"
        )
        return


class OpenAPIKingdom(OpenAPIQueryParameter):
    def __init__(self):
        super(OpenAPIKingdom, self).__init__(
            name="kingdom",
            description="""
            IDs of kingdoms to include. Only available `1` indicating Plantae
            """
        )
        return


class OpenAPIDivision(OpenAPIQueryParameter):
    def __init__(self):
        super(OpenAPIDivision, self).__init__(
            name="division",
            description=self.__default_description__.format("divisions")
        )
        return


class OpenAPIClass(OpenAPIQueryParameter):
    def __init__(self):
        super(OpenAPIClass, self).__init__(
            name="class_name",
            description=self.__default_description__.format("classes")
        )
        return


class OpenAPIOrder(OpenAPIQueryParameter):
    def __init__(self):
        super(OpenAPIOrder, self).__init__(
            name="order",
            description=self.__default_description__.format("orders")
        )
        return


class OpenAPIFamily(OpenAPIQueryParameter):
    def __init__(self):
        super(OpenAPIFamily, self).__init__(
            name="family",
            description=self.__default_description__.format("families")
        )
        return


class OpenAPIGenus(OpenAPIQueryParameter):
    def __init__(self):
        super(OpenAPIGenus, self).__init__(
            name="genus",
            description="IDs of genus to include."
        )
        return


class OpenAPISpecies(OpenAPIQueryParameter):
    def __init__(self):
        super(OpenAPISpecies, self).__init__(
            name="species",
            description="IDs of species to include."
        )
        return


class OpenAPIPlantHabit(OpenAPIQueryParameter):
    def __init__(self):
        super(OpenAPIPlantHabit, self).__init__(
            name="plant_habit",
            description="IDs of plant habits to include."
        )
        return


class OpenAPIEnvHabit(OpenAPIQueryParameter):
    def __init__(self):
        super(OpenAPIEnvHabit, self).__init__(
            name="env_habit",
            description="IDs of environmental habits to include."
        )
        return


class OpenAPIStatus(OpenAPIQueryParameter):
    def __init__(self):
        super(OpenAPIStatus, self).__init__(
            name="status",
            description="IDs of origin of species to include."
        )
        return


class OpenAPICycle(OpenAPIQueryParameter):
    def __init__(self):
        super(OpenAPICycle, self).__init__(
            name="cycle",
            description="IDs of cycle of plant to include."
        )
        return


class OpenAPIRegion(OpenAPIQueryParameter):
    def __init__(self):
        super(OpenAPIRegion, self).__init__(
            name="region",
            description="IDs of regions to include."
        )
        return


class OpenAPIConservation(OpenAPIQueryParameter):
    def __init__(self):
        super(OpenAPIConservation, self).__init__(
            name="conservation_status",
            description="IDs of conservation status to include."
        )
        return


class OpenAPICommonName(OpenAPIQueryParameter):
    def __init__(self):
        super(OpenAPICommonName, self).__init__(
            name="common_name",
            description="IDs of common names to include."
        )
        return


class OpenAPISearch(openapi.Parameter):
    def __init__(self):
        super(OpenAPISearch, self).__init__(
            name="search", in_=openapi.IN_QUERY,
            description="A string to match (case insensitive) the name of the model",
            type=openapi.TYPE_STRING,
        )
        return


class OpenAPIHerbarium(openapi.Parameter):
    def __init__(self):
        super(OpenAPIHerbarium, self).__init__(
            name="herbarium", in_=openapi.IN_QUERY,
            description="Filter by the herbarium of the specimen. `all` "
                        "equivalent to use no filter",
            type=openapi.TYPE_STRING,
            enum=["CONC", "ULS", "all"],
        )
        return
