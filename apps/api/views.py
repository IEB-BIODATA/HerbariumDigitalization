import logging
import os
from django.db.models import Q, ExpressionWrapper, F, FloatField, Value, Count
from django.db.models.functions import Length
from django.http import JsonResponse
from django.shortcuts import redirect
from django.utils.translation import get_language, activate
from drf_multiple_model.pagination import MultipleModelLimitOffsetPagination
from drf_multiple_model.views import FlatMultipleModelAPIView, ObjectMultipleModelAPIView
from drf_spectacular.types import OpenApiTypes
from drf_spectacular.utils import extend_schema, OpenApiParameter, OpenApiResponse
from rest_framework import exceptions
from rest_framework.generics import ListAPIView, RetrieveAPIView
from rest_framework.pagination import PageNumberPagination
from rest_framework.renderers import JSONRenderer
from rest_framework.response import Response
from rest_framework.views import APIView
from urllib.parse import urlparse, parse_qs, urlencode

from apps.catalog.models import Species, Synonymy, Family, Division, ClassName, Order, Status, Genus, \
    Region, ConservationState, PlantHabit, EnvironmentalHabit, Cycle, FinderView, CommonName, Kingdom
from apps.digitalization.models import VoucherImported, BannerImage
from intranet.utils import get_geometry_post
from .serializers import SpeciesFinderSerializer, \
    SynonymyFinderSerializer, DivisionSerializer, ClassSerializer, OrderSerializer, \
    FamilySerializer, DistributionSerializer, \
    FinderSerializer, GenusSerializer, CommonNameSerializer, \
    SpeciesDetailsSerializer, SynonymyDetailsSerializer, SpecimenDetailSerializer, SpecimenFinderSerializer, \
    RegionDetailsSerializer, KingdomSerializer, MinimumSerializer
from .utils import filter_query_set, OpenAPIKingdom, OpenAPIClass, OpenAPIOrder, OpenAPIFamily, OpenAPIGenus, \
    OpenAPISpecies, OpenAPIPlantHabit, OpenAPIEnvHabit, OpenAPIStatus, OpenAPICycle, OpenAPIRegion, OpenAPIConservation, \
    OpenAPICommonName, OpenAPISearch, OpenAPIDivision, OpenAPIHerbarium, OpenApiPaginated, OpenAPILang, filter_by_geo, \
    OpenAPIArea, OpenAPIGeometry
from ..catalog.serializers import PlantHabitSerializer, EnvHabitSerializer, StatusSerializer, CycleSerializer, \
    RegionSerializer, ConservationStateSerializer
from ..digitalization.utils import register_temporal_geometry


class LimitPagination(MultipleModelLimitOffsetPagination):
    default_limit = 10


class InfoApi(APIView):
    """
    A view that returns the count of active images.
    """
    renderer_classes = (JSONRenderer,)

    @extend_schema(
        responses={
            ('200', 'application/json'): OpenApiResponse(
                description='Digitalized specimens in the herbarium and the amount of species with images',
            ),
        }
    )
    def get(self, request, format=None):
        images_count = VoucherImported.objects.all().exclude(
            Q(image_public_resized_10__exact='') |
            Q(image_public_resized_10__isnull=True)
        ).count()
        species_count = Species.objects.all().exclude(
            voucherimported__isnull=True
        ).exclude(
            Q(voucherimported__image_public_resized_10__exact='') |
            Q(voucherimported__image_public_resized_10__isnull=True)
        ).count()
        content = {
            'images': images_count,
            'species': species_count,
        }
        return Response(content)


class CustomPagination(PageNumberPagination):
    def paginate_queryset(self, queryset, request, view=None):
        paginated = request.query_params.get('paginated', 'true')
        if paginated.lower() == 'false':
            return None
        else:
            return super().paginate_queryset(queryset, request, view)


class BadRequestError(exceptions.APIException):
    status_code = 400
    default_detail = "Bad Request"


class QueryList(ListAPIView):
    pagination_class = CustomPagination

    def get_queryset(self):
        logging.info(f"Getting {self.queryset.model._meta.model_name}: {self.request.get_full_path()}")
        return filter_query_set(super().get_queryset(), self.request)

    def get_serializer_class(self):
        return super().get_serializer_class()

    @extend_schema(parameters=[
        OpenAPIKingdom(), OpenAPIDivision(), OpenAPIClass(), OpenAPIOrder(),
        OpenAPIFamily(), OpenAPIGenus(), OpenAPISpecies(),
        OpenAPIPlantHabit(), OpenAPIEnvHabit(), OpenAPIStatus(), OpenAPICycle(),
        OpenAPIRegion(), OpenAPIConservation(), OpenAPICommonName(), OpenAPISearch(),
        OpenApiPaginated(), OpenAPILang(),
    ])
    def get(self, request, *args, **kwargs):
        return super().get(request, *args, **kwargs)


class DivisionList(QueryList):
    """
    Gets all available divisions in the catalogue
    """
    serializer_class = DivisionSerializer
    queryset = Division.objects.all()


class ClassList(QueryList):
    """
    Gets all available classes in the catalogue
    """
    serializer_class = ClassSerializer
    queryset = ClassName.objects.all()


class OrderList(QueryList):
    """
    Gets all available orders in the catalogue
    """
    serializer_class = OrderSerializer
    queryset = Order.objects.all()


class FamilyList(QueryList):
    """
    Gets all available families in the catalogue
    """
    serializer_class = FamilySerializer
    queryset = Family.objects.all()


class GenusList(QueryList):
    """
    Gets all available genus in the catalogue
    """
    serializer_class = GenusSerializer
    queryset = Genus.objects.all()


class PlantHabitList(QueryList):
    """
    Gets all available plant Habit in the catalogue
    """
    serializer_class = PlantHabitSerializer
    queryset = PlantHabit.objects.all()


class EnvHabitList(QueryList):
    """
    Gets all available environmental habit in the catalogue
    """
    serializer_class = EnvHabitSerializer
    queryset = EnvironmentalHabit.objects.all()


class StatusList(QueryList):
    """
    Gets all available status in the catalogue
    """
    serializer_class = StatusSerializer
    queryset = Status.objects.all()


class CycleList(QueryList):
    """
    Gets all available cycles in the catalogue
    """
    serializer_class = CycleSerializer
    queryset = Cycle.objects.all()


class RegionList(QueryList):
    """
    Gets all available regions of Chile in the catalog
    """
    serializer_class = RegionSerializer
    queryset = Region.objects.all()


class ConservationStateList(QueryList):
    """
    Gets all available conservation state in the catalogue
    """
    serializer_class = ConservationStateSerializer
    queryset = ConservationState.objects.all()


class CommonNameList(QueryList):
    """
    Gets all available common names in the catalogue
    """
    serializer_class = CommonNameSerializer
    queryset = CommonName.objects.all()


# TODO: Filter by GEOMETRY
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
                "label": "genus",
                "queryset": Genus.objects.all(),
                "serializer_class": GenusSerializer
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

    @extend_schema(parameters=[
        OpenAPIKingdom(), OpenAPIDivision(), OpenAPIClass(), OpenAPIOrder(),
        OpenAPIFamily(), OpenAPIGenus(), OpenAPISpecies(),
        OpenAPIPlantHabit(), OpenAPIEnvHabit(), OpenAPIStatus(), OpenAPICycle(),
        OpenAPIRegion(), OpenAPIConservation(), OpenAPICommonName(), OpenAPISearch(),
        OpenApiPaginated(), OpenAPILang(),
    ], responses={
        ('200', 'application/json'): OpenApiResponse(
            description='All available options of each menu filter. Used on the main page',
        ),
    })
    def get(self, request, *args, **kwargs):
        return super().get(request, *args, **kwargs)


class NameApiView(ObjectMultipleModelAPIView):
    """
    Retrieve the names of the taxonomies or attributes associated to its unique id
    """
    pagination_class = None

    def get_querylist(self):
        base_querylist = [
            {
                "label": "kingdom",
                "queryset": Kingdom.objects.all(),
            },
            {
                "label": "division",
                "queryset": Division.objects.all(),
            },
            {
                "label": "class_name",
                "queryset": ClassName.objects.all(),
            },
            {
                "label": "order",
                "queryset": Order.objects.all(),
            },
            {
                "label": "family",
                "queryset": Family.objects.all(),
            },
            {
                "label": "genus",
                "queryset": Genus.objects.all(),
            },
            {
                "label": "plant_habit",
                "queryset": PlantHabit.objects.all(),
            },
            {
                "label": "env_habit",
                "queryset": EnvironmentalHabit.objects.all(),
            },
            {
                "label": "status",
                "queryset": Status.objects.all(),
            },
            {
                "label": "cycle",
                "queryset": Cycle.objects.all(),
            },
            {
                "label": "region",
                "queryset": Region.objects.all(),
            },
            {
                "label": "conservation_state",
                "queryset": ConservationState.objects.all(),
            },
        ]
        querylist = list()
        for a_model in base_querylist:
            label = a_model["label"]
            asking_for = self.request.query_params.getlist(label)
            if len(asking_for) > 0:
                a_queryset = a_model["queryset"].filter(id__in=self.request.query_params.getlist(label))
                if a_queryset.count() > 0:
                    logging.info(label)
                    logging.debug(a_queryset)
                    querylist.append({
                        "label": label,
                        "queryset": a_queryset,
                        "serializer_class": MinimumSerializer,
                    })
        return querylist

    def add_to_results(self, data, label, results):
        results[label] = dict(data)
        return results

    @extend_schema(parameters=[
        OpenAPIKingdom(), OpenAPIDivision(), OpenAPIClass(), OpenAPIOrder(),
        OpenAPIFamily(), OpenAPIGenus(), OpenAPISpecies(),
        OpenAPIPlantHabit(), OpenAPIEnvHabit(), OpenAPIStatus(), OpenAPICycle(),
        OpenAPIRegion(), OpenAPIConservation(), OpenAPICommonName(), OpenAPILang(),
    ], responses={
        ('200', 'application/json'): OpenApiResponse(
            description='Names of the parameter using its unique id',
        ),
    })
    def get(self, request, *args, **kwargs):
        return super().get(request, *args, **kwargs)


class FinderApiView(ListAPIView):
    """
    Gets if there are any Species, Synonyms, Common Name,
    Genus or Family that matches the given text
    """
    queryset = FinderView.objects.all()
    serializer_class = FinderSerializer
    pagination_class = None

    @extend_schema(parameters=[OpenAPILang()])
    def get(self, request, *args, **kwargs):
        return super().get(request, *args, **kwargs)

    def get_queryset(self):
        text = self.kwargs.get("text", "")
        default_language = get_language()
        lang = self.request.query_params.get("lang", default_language)
        activate(lang)
        category = self.request.query_params.get("category", None)
        logging.info(f"Getting names: {self.request.get_full_path()}")
        filters = {"name__icontains": text}
        if category is not None and category.lower() != "all":
            filters["type"] = category.lower()
        return super().get_queryset().filter(**filters)


class RegionDetails(RetrieveAPIView):
    queryset = Region.objects.all()
    serializer_class = RegionDetailsSerializer

    @extend_schema(parameters=[
        OpenAPILang(),
    ])
    def get(self, request, *args, **kwargs):
        default_language = get_language()
        lang = request.query_params.get("lang", default_language)
        activate(lang)
        return super(RegionDetails, self).get(request, *args, **kwargs)


class POSTRedirect(APIView):

    @extend_schema(
        parameters=[
            OpenAPIKingdom(), OpenAPIDivision(), OpenAPIClass(), OpenAPIOrder(),
            OpenAPIFamily(), OpenAPIGenus(), OpenAPISpecies(),
            OpenAPIPlantHabit(), OpenAPIEnvHabit(), OpenAPIStatus(), OpenAPICycle(),
            OpenAPIRegion(), OpenAPIConservation(), OpenAPICommonName(), OpenAPISearch(),
            OpenApiPaginated(), OpenAPILang(),
        ],
        request={
            'multipart/form-data': {
                'type': 'object',
                'properties': {
                    'file': {
                        'type': 'string',
                        'format': 'binary'
                    }
                }
            }
        },
    )
    def post(self, request, *args, **kwargs):
        geometry = get_geometry_post(request)[0]
        area = register_temporal_geometry(geometry)
        original_url = request.get_full_path()
        parsed_url = urlparse(original_url)
        base_url = parsed_url.path
        query_params = parse_qs(parsed_url.query)
        query_params["area"] = [str(area)]
        updated_url = f"{base_url}?{urlencode(query_params, doseq=True)}"
        logging.info(f"Redirecting POST at {original_url} to {updated_url}")
        return redirect(updated_url)


class SpeciesListApiView(FlatMultipleModelAPIView, POSTRedirect):
    """
    Gets all species and synonyms matching the current query
    and filter given on the query parameters
    """
    serializer_class = SpeciesFinderSerializer
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
        results = list()
        if species_filter:
            logging.info(f"Getting species: {self.request.get_full_path()}")
            queryset = filter_query_set(Species.objects.all(), self.request)
            if image_filter:
                queryset = queryset.annotate(
                    vouchers_count=Count('voucherimported')
                ).exclude(
                    Q(vouchers_count__isnull=True) |
                    Q(vouchers_count=0) |
                    Q(voucherimported__image_public_resized_10__exact='')
                )
            queryset = queryset.filter(
                filter_by_geo(self.request, "voucherimported__point__within")
            ).distinct()
            self.species_count = queryset.count()
            results.append({
                "label": "species",
                "queryset": queryset,
                "serializer_class": SpeciesFinderSerializer
            })
        if synonyms_filter:
            logging.info(f"Getting synonyms: {self.request.get_full_path()}")
            queryset = filter_query_set(Synonymy.objects.all(), self.request)
            queryset = queryset.filter(
                filter_by_geo(self.request, "species__voucherimported__point__within")
            ).distinct()
            self.synonyms_count = queryset.count()
            results.append({
                "label": "synonymy",
                "queryset": queryset,
                "serializer_class": SynonymyFinderSerializer
            })
        return results

    def list(self, request, *args, **kwargs):
        response = super().list(request, *args, **kwargs)
        # Modify the response data
        response.data['species_count'] = self.species_count
        response.data['synonyms_count'] = self.synonyms_count
        return response

    @extend_schema(parameters=[
        OpenAPIKingdom(), OpenAPIDivision(), OpenAPIClass(), OpenAPIOrder(),
        OpenAPIFamily(), OpenAPIGenus(), OpenAPISpecies(),
        OpenAPIPlantHabit(), OpenAPIEnvHabit(), OpenAPIStatus(), OpenAPICycle(),
        OpenAPIRegion(), OpenAPIConservation(), OpenAPICommonName(),
        OpenAPIArea(), OpenAPIGeometry(), OpenAPISearch(),
        OpenApiPaginated(), OpenAPILang(),
    ])
    def get(self, request, *args, **kwargs):
        return super(SpeciesListApiView, self).get(request, *args, **kwargs)


class ScientificNameDetails(RetrieveAPIView):
    @extend_schema(parameters=[
        OpenAPILang(),
    ])
    def get(self, request, *args, **kwargs):
        default_language = get_language()
        lang = request.query_params.get("lang", default_language)
        activate(lang)
        return super(ScientificNameDetails, self).get(request, *args, **kwargs)


class SpeciesDetails(ScientificNameDetails):
    """
    Gets the detail of the species given the unique ID
    """
    queryset = Species.objects.all()
    serializer_class = SpeciesDetailsSerializer


class SynonymyDetails(ScientificNameDetails):
    """
    Gets the detail of the synonymy given the unique ID
    """
    queryset = Synonymy.objects.all()
    serializer_class = SynonymyDetailsSerializer


class DistributionList(ListAPIView):
    pagination_class = CustomPagination
    queryset = VoucherImported.objects.all()
    serializer_class = DistributionSerializer

    def get_queryset(self):
        species_id = self.kwargs["species_id"]
        queryset = super().get_queryset()
        if species_id:
            queryset = queryset.filter(scientific_name=species_id)
        return queryset.order_by("id")

    @extend_schema(parameters=[
        OpenApiPaginated(), OpenAPILang(),
    ])
    def get(self, request, *args, **kwargs):
        return super(DistributionList, self).get(request, *args, **kwargs)


class SpecimensList(QueryList, POSTRedirect):
    """
    Gets the list of available specimens in the herbarium
    """
    queryset = VoucherImported.objects.all()
    serializer_class = SpecimenFinderSerializer

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
        image_filter = self.request.query_params.get("image_filter", "false").lower() == "true"
        if image_filter:
            query = query & (
                Q(image_public_resized_10__isnull=False) &
                Q(image_public_resized_60__isnull=False) &
                Q(image_public__isnull=False)
            )
        query = query & filter_by_geo(self.request, "point__within")
        regions = self.request.GET.getlist("region", [])
        if len(regions) > 0:
            region_query = Q()
            for pk in regions:
                region = Region.objects.get(pk=pk)
                region_query = region_query | Q(point__within=region.geometry)
            query = query & region_query
        return queryset.filter(query).order_by(
            "scientific_name__genus__family__name",
            "scientific_name__genus__name",
            "scientific_name__scientific_name",
        )

    @extend_schema(parameters=[
        OpenAPIKingdom(), OpenAPIDivision(), OpenAPIClass(), OpenAPIOrder(),
        OpenAPIFamily(), OpenAPIGenus(), OpenAPISpecies(),
        OpenAPIPlantHabit(), OpenAPIEnvHabit(), OpenAPIStatus(), OpenAPICycle(),
        OpenAPIRegion(), OpenAPIConservation(), OpenAPICommonName(),
        OpenAPISearch(), OpenApiPaginated(), OpenAPILang(),
        OpenAPIHerbarium(), OpenAPIArea(), OpenAPIGeometry(),
        OpenApiParameter(
            name="code",
            location=OpenApiParameter.QUERY,
            description="""
            Either the catalogNumber or the complete code including institution, 
            herbarium code and seven digits catalogNumber, example UDEC:CONC:000XXXX 
            """,
            type=OpenApiTypes.STR
        )
    ])
    def get(self, request, *args, **kwargs):
        return super().get(request, *args, **kwargs)


class SpecimenDetails(ScientificNameDetails):
    """
    Gets the information of a particular specimen
    """
    queryset = VoucherImported.objects.all()
    serializer_class = SpecimenDetailSerializer


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
