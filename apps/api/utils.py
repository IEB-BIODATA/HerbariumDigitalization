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
    return queryset.filter_query_in(**attribute_query).filter_taxonomy_in(**taxonomic_query)
