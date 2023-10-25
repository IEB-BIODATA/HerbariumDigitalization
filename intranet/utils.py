from __future__ import annotations
import logging
import os
import tempfile
from abc import ABC, abstractmethod
from typing import Dict, List

from django.contrib.gis.gdal import DataSource
from django.contrib.gis.geos import GEOSGeometry
from django.core.paginator import Paginator
from django.db import models
from django.db.models import Q, QuerySet
from django.http import HttpRequest, JsonResponse
from rest_framework.serializers import SerializerMetaclass


class CatalogQuerySet(models.QuerySet, ABC):

    @abstractmethod
    def filter_query_in(self, **parameters: Dict[str, List[str]]) -> CatalogQuerySet:
        pass

    @abstractmethod
    def filter_query(self, **parameters: Dict[str, List[str]]) -> CatalogQuerySet:
        pass

    @abstractmethod
    def filter_taxonomy_in(self, **parameters: Dict[str: List[str]]) -> CatalogQuerySet:
        pass

    @abstractmethod
    def filter_taxonomy(self, **parameters: Dict[str: List[str]]) -> CatalogQuerySet:
        pass

    @abstractmethod
    def search(self, text: str) -> CatalogQuerySet:
        pass


def paginated_table(
        request: HttpRequest,
        entries: QuerySet,
        serializer: SerializerMetaclass,
        sort_by_func: dict[int, str],
        model_name: str,
        search_query: Q
) -> JsonResponse:
    search_value = request.GET.get("search[value]", None)
    if search_value:
        logging.debug(f"Searching with {search_value}")
        entries = entries.filter(search_query)

    sort_by = int(request.GET.get("order[0][column]", 4))
    sort_type = request.GET.get("order[0][dir]", "desc")

    if sort_by in sort_by_func:
        sort_by_str = "ascending" if sort_type == "asc" else "descending"
        second_sort_by = request.GET.get("order[1][column]", None)
        second_sort_type = request.GET.get("order[1][dir]", "asc")
        if second_sort_by:
            second_sort_by_str = "ascending" if second_sort_type == "asc" else "descending"
            logging.debug(f"Order by {sort_by} ({sort_by_func[sort_by]}) in {sort_by_str} order"
                          f" and {second_sort_by} ({sort_by_func[int(second_sort_by)]}) in {second_sort_by_str} order")
            entries = entries.order_by(
                ("" if sort_type == "asc" else "-") + sort_by_func[sort_by],
                ("" if second_sort_type == "asc" else "-") + sort_by_func[int(second_sort_by)]
            )
        else:
            logging.debug(f"Order by {sort_by} ({sort_by_func[sort_by]}) in {sort_by_str} order")
            entries = entries.order_by(("" if sort_type == "asc" else "-") + sort_by_func[sort_by])

    length = int(request.GET.get("length", 10))
    start = int(request.GET.get("start", 0))
    paginator = Paginator(entries, length)
    page_number = start // length + 1
    page_obj = paginator.get_page(page_number)
    data = list()

    logging.debug(f"Returning {entries.count()} {model_name}, starting at {start + 1} with {length} items")

    for item in page_obj:
        data.append(serializer(
            instance=item,
            many=False,
            context=request
        ).data)

    return JsonResponse({
        "draw": int(request.GET.get("draw", 0)),
        "recordsTotal": entries.count(),
        "recordsFiltered": paginator.count,
        "data": data
    })


def get_geometry(request: HttpRequest) -> GEOSGeometry:
    kml_file = request.data.get("file")
    file_extension = os.path.splitext(kml_file.name)[1]
    with tempfile.NamedTemporaryFile(delete=True, suffix=file_extension) as temp_file:
        kml_data = kml_file.read()
        temp_file.write(kml_data)
        temp_file.seek(0)
        data_source = DataSource(temp_file.name)
        layer = data_source[0]
        kml_geometry = layer.get_geoms(True)
    return kml_geometry
