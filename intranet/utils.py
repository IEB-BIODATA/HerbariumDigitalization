from __future__ import annotations

import logging
import os
import tempfile
from abc import ABC, abstractmethod
from django.contrib.gis.gdal import DataSource
from django.contrib.gis.geos import GEOSGeometry, Point, LineString, LinearRing, Polygon, MultiPoint, MultiLineString, \
    MultiPolygon, GeometryCollection
from django.core.files.uploadedfile import UploadedFile
from django.core.paginator import Paginator
from django.db import models
from django.db.models import Q, QuerySet
from django.http import HttpRequest, JsonResponse
from rest_framework.serializers import SerializerMetaclass
from typing import Dict, List, Tuple

GEOM_TYPE = {
    0: Point,
    1: LineString,
    2: LinearRing,
    3: Polygon,
    4: MultiPoint,
    5: MultiLineString,
    6: MultiPolygon,
    7: GeometryCollection,
}


class CatalogQuerySet(models.QuerySet, ABC):

    @abstractmethod
    def filter_query(self, **parameters: Dict[str, List[str]]) -> CatalogQuerySet:
        pass

    @abstractmethod
    def filter_taxonomy(self, **parameters: Dict[str: List[str]]) -> CatalogQuerySet:
        pass

    @abstractmethod
    def filter_geometry(self, geometries: List[str]) -> CatalogQuerySet:
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
            context={"request": request}
        ).data)

    return JsonResponse({
        "draw": int(request.GET.get("draw", 0)),
        "recordsTotal": entries.count(),
        "recordsFiltered": paginator.count,
        "data": data
    })


def get_geometry_post(request: HttpRequest) -> GEOSGeometry:
    kml_file = request.data.get("file")
    return get_geometry(kml_file)


def get_geometry(file: UploadedFile) -> GEOSGeometry:
    file_extension = os.path.splitext(file.name)[1]
    with tempfile.NamedTemporaryFile(delete=True, suffix=file_extension) as temp_file:
        kml_data = file.read()
        temp_file.write(kml_data)
        temp_file.seek(0)
        data_source = DataSource(temp_file.name)
        layer = data_source[0]
        kml_geometry = layer.get_geoms(True)
        if len(kml_geometry) > 1:
            logging.warning(f"File has {len(kml_geometry)} layers, using first one only")
        geometry = kml_geometry[0]
    if geometry.hasz:
        logging.debug(f"Stripping z dimension of {geometry.geom_type}")
        geometry = strip_z_dimension(geometry)
    return geometry


def strip_z_dimension(geometry: GEOSGeometry) -> GEOSGeometry:
    if geometry.num_geom > 1:
        geoms = list()
        for geom in geometry:
            geoms.append(__strip_z_dimension_coord__(geom))
        return GEOM_TYPE[geometry.geom_typeid](*geoms)
    else:
        return __strip_z_dimension_coord__(geometry)


def __strip_z_dimension_coord__(geometry: GEOSGeometry) -> GEOSGeometry:
    if geometry.geom_typeid == 3:
        rings = list()
        for linear_ring in geometry:
            rings.append(__strip_z_dimension_coord__(linear_ring))
        return Polygon(*rings)
    else:
        return GEOM_TYPE[geometry.geom_typeid](
            list(map(__strip_z__, geometry.coords)),
            srid=geometry.srid
        )


def __strip_z__(coordinate: Tuple[float, float, float]) -> Tuple[float, float]:
    if abs(coordinate[2] - 1e-6) < 0:
        logging.warning(f"{coordinate[2]} is not a zero Z coordinate")
    return coordinate[0], coordinate[1]
