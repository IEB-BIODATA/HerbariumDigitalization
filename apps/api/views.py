import logging
import os
from urllib.parse import urlparse, parse_qs, urlencode

from drf_yasg.utils import swagger_auto_schema

from apps.catalog.models import Species, Synonymy, Family, Division, ClassName, Order, Status, Genus, \
    CommonName, Region, ConservationState, PlantHabit, EnvironmentalHabit, Cycle, TAXONOMIC_RANK, ATTRIBUTES, FinderView
from apps.digitalization.models import VoucherImported, GalleryImage, BannerImage, Areas
from django.db.models import Q, ExpressionWrapper, F, FloatField, Value
from django.db.models.functions import Length
from django.http import JsonResponse
from django.shortcuts import redirect
from drf_multiple_model.pagination import MultipleModelLimitOffsetPagination
from drf_multiple_model.views import FlatMultipleModelAPIView, ObjectMultipleModelAPIView
from rest_framework import status
from rest_framework.generics import ListAPIView, RetrieveAPIView
from rest_framework.pagination import PageNumberPagination
from rest_framework.renderers import JSONRenderer
from rest_framework.response import Response
from rest_framework.views import APIView

from intranet.utils import get_geometry
from .serializers import SynonymySerializer, SpeciesSerializer, SpeciesFinderSerializer, \
    SynonymysFinderSerializer, FamilysFinderSerializer, DivisionSerializer, ClassSerializer, OrderSerializer, \
    FamilySerializer, StatusSerializer, GenusFinderSerializer, \
    ConservationStateSerializer, DistributionSerializer, CommonNameFinderSerializer, RegionSerializer, \
    ImagesSerializer, GalleryPhotosSerializer, PlantHabitSerializer, EnvHabitSerializer, CycleSerializer, \
    SpeciesImagesSerializer, SpecimenSerializer, FinderSerializer
from .utils import filter_query_set
from ..digitalization.utils import register_temporal_geometry


class LimitPagination(MultipleModelLimitOffsetPagination):
    default_limit = 10


class LimitPaginationImages(MultipleModelLimitOffsetPagination):
    default_limit = 40


class CustomPagination(PageNumberPagination):

    def get_paginated_response(self, data):
        paginate = self.request.query_params.get("paginated", "true")
        if paginate.lower() == "false":
            return Response(data)
        else:
            return super().get_paginated_response(data)


class QueryList(ListAPIView):
    pagination_class = CustomPagination

    def get_queryset(self):
        logging.info(f"Getting {self.queryset.model._meta.model_name}: {self.request.get_full_path()}")
        return filter_query_set(super().get_queryset(), self.request)


class DivisionList(QueryList):
    """
    Gets all available divisions in the catalog
    """

    serializer_class = DivisionSerializer
    queryset = Division.objects.all()


class ClassList(QueryList):
    serializer_class = ClassSerializer
    queryset = ClassName.objects.all()


class OrderList(QueryList):
    serializer_class = OrderSerializer
    queryset = Order.objects.all()


class FamilyList(QueryList):
    serializer_class = FamilySerializer
    queryset = Family.objects.all()


class RegionList(QueryList):
    serializer_class = RegionSerializer
    queryset = Region.objects.all()


class ConservationStateList(QueryList):
    serializer_class = ConservationStateSerializer
    queryset = ConservationState.objects.all()


class SpeciesDetails(RetrieveAPIView):
    queryset = Species.objects.all()
    serializer_class = SpeciesImagesSerializer


class SynonymyDetails(RetrieveAPIView):
    queryset = Synonymy.objects.all()
    serializer_class = SynonymySerializer


class SpecimensList(ListAPIView):
    queryset = VoucherImported.objects.all()
    serializer_class = SpecimenSerializer

    def get_queryset(self):
        queryset = super().get_queryset()
        query = Q(biodata_code__voucher_state=7)
        code = self.request.GET.get("code", None)
        herbarium = self.request.GET.get("herbarium", None)
        if herbarium is not None and herbarium != "all":
            query = query & Q(herbarium__collection_code=herbarium)
        if code is not None and code != "":
            similarity_score = ExpressionWrapper(
                F("catalog_number") / Length(Value(code)),
                output_field=FloatField()
            )
            query = query & Q(biodata_code__code__icontains=code)
            return queryset.filter(query).annotate(similarity=similarity_score).order_by(
                "similarity"
            )
        return queryset.filter(query).order_by(
            "scientific_name__genus__family__name",
            "scientific_name__genus__name",
            "scientific_name__scientific_name",
        )


class FinderApiView(ListAPIView):
    queryset = FinderView.objects.all()
    serializer_class = FinderSerializer
    pagination_class = None

    def get_queryset(self):
        text = self.kwargs.get("text", "")
        category = self.request.query_params.get("category", None)
        if category is None or category.lower() == "all":
            logging.info(f"Getting names: {self.request.get_full_path()}")
            return super().get_queryset().filter(name__icontains=text)
        else:
            logging.info(f"Getting {category.lower()}: {self.request.get_full_path()}")
            return super().get_queryset().filter(name__icontains=text, type=category.lower())


class GeoListApiView(ListAPIView):
    point_query_name = "point__within"

    def get_queryset(self):
        query = Q()
        queryset = filter_query_set(super().get_queryset(), self.request)
        areas = self.request.GET.getlist("area", None)
        for area in areas:
            areas_model = Areas.objects.get(pk=area)
            query = query | Q(**{self.point_query_name: areas_model.geometry})
        return queryset.filter(query).distinct()

    def post(self, request, *args, **kwargs):
        geometry = get_geometry(request)[0]
        area = register_temporal_geometry(geometry)
        original_url = request.get_full_path()
        parsed_url = urlparse(original_url)
        base_url = parsed_url.path
        query_params = parse_qs(parsed_url.query)
        query_params["area"] = [str(area)]
        updated_url = f"{base_url}?{urlencode(query_params, doseq=True)}"
        logging.info(f"Redirecting POST at {original_url} to {updated_url}")
        return redirect(updated_url)


class GeoSpeciesListApiView(GeoListApiView):
    serializer_class = SpeciesSerializer
    queryset = Species.objects.all()
    point_query_name = "voucherimported__point__within"

    def get_queryset(self):
        return super().get_queryset().order_by(
            "genus__family__name",
            "genus__name",
            "scientific_name",
        )


class GeoSpecimensListApiView(GeoListApiView):
    serializer_class = SpecimenSerializer
    queryset = VoucherImported.objects.all()
    point_query_name = "point__within"

    def get_queryset(self):
        return super().get_queryset().order_by(
            "scientific_name__genus__family__name",
            "scientific_name__genus__name",
            "scientific_name__scientific_name",
        )


class SpeciesListApiView(FlatMultipleModelAPIView):
    sorting_fields = ['name']
    pagination_class = LimitPagination

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.species_count = 0
        self.synonyms_count = 0

    def get_querylist(self):
        species_filter = self.request.query_params.get("species_filter", "false").lower() == "true"
        synonyms_filter = self.request.query_params.get("synonyms_filter", "false").lower() == "true"
        image_filter = self.request.query_params.get("image_filter", "false").lower() == "true"
        if not species_filter and not synonyms_filter:
            species_filter = True
            synonyms_filter = True
        if image_filter:
            species_filter = True
            synonyms_filter = False
        search = self.request.query_params.get("search", None)
        results = list()
        if species_filter:
            logging.info(f"Getting species: {self.request.get_full_path()}")
            queryset = filter_query_set(Species.objects.all(), self.request)
            if image_filter:
                queryset = queryset.exclude(
                    Q(voucherimported__isnull=True) &
                    Q(voucherimported__image_public_resized_10__exact='')
                )
            if search:
                queryset = queryset.search(search)
            self.species_count = queryset.count()
            results.append({
                "label": "species",
                "queryset": queryset,
                "serializer_class": SpeciesFinderSerializer
            })
        if synonyms_filter:
            logging.info(f"Getting synonyms: {self.request.get_full_path()}")
            queryset = filter_query_set(Synonymy.objects.all(), self.request)
            if search:
                queryset = queryset.search(search)
            self.synonyms_count = queryset.count()
            results.append({
                "label": "synonymy",
                "queryset": queryset,
                "serializer_class": SynonymysFinderSerializer
            })
        return results

    def list(self, request, *args, **kwargs):
        response = super().list(request, *args, **kwargs)
        # Modify the response data
        response.data['species_count'] = self.species_count
        response.data['synonyms_count'] = self.synonyms_count
        return response


class MenuApiView(ObjectMultipleModelAPIView):
    pagination_class = None

    def get_querylist(self):
        querylist = [
            {
                "label": "division",
                "queryset": Division.objects.all(),
                "serializer_class": DivisionSerializer
            },
            {
                "label": "class_name",
                "queryset": ClassName.objects.all(),
                "serializer_class": ClassSerializer
            },
            {
                "label": "order",
                "queryset": Order.objects.all(),
                "serializer_class": OrderSerializer
            },
            {
                "label": "family",
                "queryset": Family.objects.all(),
                "serializer_class": FamilySerializer
            },
            {
                "label": "plant_habit",
                "queryset": PlantHabit.objects.all(),
                "serializer_class": PlantHabitSerializer
            },
            {
                "label": "env_habit",
                "queryset": EnvironmentalHabit.objects.all(),
                "serializer_class": EnvHabitSerializer
            },
            {
                "label": "status",
                "queryset": Status.objects.all(),
                "serializer_class": StatusSerializer
            },
            {
                "label": "cycle",
                "queryset": Cycle.objects.all(),
                "serializer_class": CycleSerializer
            },
            {
                "label": "region",
                "queryset": Region.objects.all(),
                "serializer_class": RegionSerializer
            },
            {
                "label": "conservation_state",
                "queryset": ConservationState.objects.all(),
                "serializer_class": ConservationStateSerializer
            },
        ]
        for i in range(len(querylist)):
            label = querylist[i]["label"]
            logging.info(label)
            querylist[i]["queryset"] = filter_query_set(querylist[i]["queryset"], self.request)
            logging.info(querylist[i])
        return querylist


class DistributionList(QueryList):
    queryset = VoucherImported.objects.all()
    serializer_class = DistributionSerializer

    def get_queryset(self):
        species_id = self.kwargs["species_id"]
        queryset = super().get_queryset()
        if species_id:
            queryset = queryset.filter(scientific_name=species_id)
        return queryset.order_by("id")


class ImagesList(QueryList):
    queryset = VoucherImported.objects.all()
    serializer_class = ImagesSerializer

    def get_queryset(self):
        species_id = self.kwargs["species_id"]
        queryset = super().get_queryset()
        if species_id:
            queryset = queryset.filter(scientific_name=species_id)
        queryset = queryset.exclude(image_public_resized_10__exact="")
        return queryset.order_by("id")


class GalleryList(QueryList):
    queryset = GalleryImage.objects.all()
    serializer_class = GalleryPhotosSerializer

    def get_queryset(self):
        species_id = self.kwargs["species_id"]
        queryset = super().get_queryset()
        if species_id:
            queryset = queryset.filter(scientific_name=species_id)
        return queryset.order_by("id")


class ImagesFilterApiView(FlatMultipleModelAPIView):
    sorting_fields = ['name']
    pagination_class = LimitPaginationImages

    def get_querylist(self):
        queryset = VoucherImported.objects.exclude(image_public_resized_10__exact='').all()
        queryset = filter_query_set(queryset, self.request)
        return [{
            "label": "image",
            "queryset": queryset,
            "serializer_class": ImagesSerializer
        }]


class ImageDetails(RetrieveAPIView):
    queryset = VoucherImported.objects.all()
    serializer_class = ImagesSerializer


class InfoApi(APIView):
    """
    A view that returns the count of active images.
    """
    renderer_classes = (JSONRenderer,)

    def get(self, request, format=None):
        images_count = VoucherImported.objects.all().exclude(image_public_resized_10__exact='').count()
        species_count = Species.objects.all().exclude(voucherimported__isnull=True).exclude(
            voucherimported__image_public_resized_10__exact=''
        ).count()
        content = {
            'images': images_count,
            'species': species_count,
        }
        return Response(content)


class BannerSpecie(APIView):
    """
    Generates image of banner and url to 'herbariodigital.cl'
    """
    renderer_classes = (JSONRenderer,)

    def get(self, request, format=None, **kwargs):
        specie_id = kwargs.get("specie_id")
        specie = Species.objects.filter(id=specie_id).first()
        logging.debug("Getting banner for {}".format(specie.scientific_name))
        banners = BannerImage.objects.filter(specie_id=specie)
        if banners.count() == 0:
            logging.warning("No banner found for {} species".format(specie.scientific_name))
            return Response(
                {
                    "msg": "No banner for specie {}".format(
                        specie.scientific_name
                    )
                }, status=501)
        return Response({
            'image': banners.first().banner.url,
            'url': "{}/catalog/details/Species/{}/".format(
                os.environ.get("HERBARIUM_FRONTEND"),
                specie_id
            )
        })


def get_names(request):
    logging.debug(request.GET)
    taxonomy_models = {
        'genus': Genus,
        'family': Family,
    }
    info = dict()
    for name, model in taxonomy_models.items():
        request_list = request.GET.getlist(name)
        if request_list is not None:
            info[name] = dict()
            for m in request_list:
                logging.debug(name)
                logging.debug(model)
                try:
                    info[name][m] = model.objects.get(pk=m).name
                except model.DoesNotExist:
                    info[name][m] = None
                logging.debug(info)
    return JsonResponse(info)
