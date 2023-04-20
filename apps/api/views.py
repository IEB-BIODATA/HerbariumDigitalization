import base64
import datetime as dt
import logging
import os

import jwt
from django.contrib.auth import authenticate
from django.db.models import Q
from django.http import HttpResponseBadRequest, JsonResponse, HttpResponse
from drf_multiple_model.pagination import MultipleModelLimitOffsetPagination
from drf_multiple_model.views import FlatMultipleModelAPIView, ObjectMultipleModelAPIView
from rest_framework import status
from rest_framework.generics import ListAPIView
from rest_framework.renderers import JSONRenderer
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.catalog.models import Species, Synonymy, Family, Division, Class_name, Order, Habit, Status, Ciclo, Genus, \
    CommonName, Region, ConservationState
from apps.digitalization.models import VoucherImported, GalleryImage, BannerImage
from web import settings
from .serializers import SpecieSerializer, SynonymySerializer, SpeciesSerializer, SpeciesFinderSerializer, \
    SynonymysFinderSerializer, FamilysFinderSerializer, DivisionSerializer, ClassSerializer, OrderSerializer, \
    FamilySerializer, HabitSerializer, StatusSerializer, CicloSerializer, GenusFinderSerializer, \
    DistributionSerializer, ImagesSerializer, CommonNameFinderSerializer, RegionSerializer, ConservationStateSerializer, \
    GalleryPhotosSerializer


class LimitPagination(MultipleModelLimitOffsetPagination):
    default_limit = 10


class LimitPaginationImages(MultipleModelLimitOffsetPagination):
    default_limit = 40


class DivisionList(ListAPIView):
    serializer_class = DivisionSerializer
    queryset = Division.objects.all()

    def get(self, request, limit=None, **kwargs):
        if int(limit) == 0:
            items = Division.objects.all()
        else:
            items = Division.objects.all()[:int(limit)]
        divisions = DivisionSerializer(items, many=True)
        return Response(status=status.HTTP_200_OK, data=divisions.data)


class ClassList(ListAPIView):
    serializer_class = ClassSerializer
    queryset = Class_name.objects.all()

    def get(self, request, limit=None, **kwargs):
        if int(limit) == 0:
            items = Class_name.objects.all()
        else:
            items = Class_name.objects.all()[:int(limit)]
        classes = ClassSerializer(items, many=True)
        return Response(status=status.HTTP_200_OK, data=classes.data)


class OrderList(ListAPIView):
    serializer_class = OrderSerializer
    queryset = Order.objects.all()

    def get(self, request, limit=None, **kwargs):
        if int(limit) == 0:
            items = Order.objects.all()
        else:
            items = Order.objects.all()[:int(limit)]
        orders = OrderSerializer(items, many=True)
        return Response(status=status.HTTP_200_OK, data=orders.data)


class FamilyList(ListAPIView):
    serializer_class = FamilySerializer
    queryset = Family.objects.all()

    def get(self, request, limit=None, **kwargs):
        if int(limit) == 0:
            items = Family.objects.all()
        else:
            items = Family.objects.all()[:int(limit)]
        families = FamilySerializer(items, many=True)
        return Response(status=status.HTTP_200_OK, data=families.data)


class HabitList(ListAPIView):
    serializer_class = HabitSerializer
    queryset = Habit.objects.all()

    def get(self, request, limit=None, **kwargs):
        if int(limit) == 0:
            items = Habit.objects.all()
        else:
            items = Habit.objects.all()[:int(limit)]
        habits = HabitSerializer(items, many=True)
        return Response(status=status.HTTP_200_OK, data=habits.data)


class SpeciesList(ListAPIView):
    serializer_class = SpeciesSerializer
    queryset = Species.objects.all()

    def get(self, request, specie_name=None, **kwargs):
        items = Species.objects.filter(scientificName__icontains=specie_name)
        species = SpeciesSerializer(items, many=True)

        for index, value in enumerate(species.data):
            value['type'] = 'specie'
        return Response(status=status.HTTP_200_OK, data=species.data)


class RegionList(ListAPIView):
    serializer_class = RegionSerializer
    queryset = Region.objects.all()

    def get(self, request, limit=None, **kwargs):
        if int(limit) == 0:
            items = Region.objects.all()
        else:
            items = Region.objects.all()[:int(limit)]
        regions = RegionSerializer(items, many=True)
        return Response(status=status.HTTP_200_OK, data=regions.data)


class ConservationStateList(ListAPIView):
    serializer_class = RegionSerializer
    queryset = ConservationState.objects.all()

    def get(self, request, limit=None, **kwargs):
        if int(limit) == 0:
            items = ConservationState.objects.all()
        else:
            items = ConservationState.objects.all()[:int(limit)]
        conservation_state = ConservationStateSerializer(items, many=True)
        return Response(status=status.HTTP_200_OK, data=conservation_state.data)


class SpecieDetails(ListAPIView):
    serializer_class = SpecieSerializer
    queryset = Species.objects.all()

    def get(self, request, specie_id=None, **kwargs):
        items = Species.objects.get(pk=specie_id)
        specie = SpecieSerializer(items, many=False, context={'request': request})
        return Response(status=status.HTTP_200_OK, data=specie.data)


class SynonymyDetails(ListAPIView):
    serializer_class = SynonymySerializer
    queryset = Synonymy.objects.all()

    def get(self, request, synonymy_id=None, **kwargs):
        items = Synonymy.objects.get(pk=synonymy_id)
        synonymy = SynonymySerializer(instance=items, many=False, context={'request': request})
        return Response(status=status.HTTP_200_OK, data=synonymy.data)


class FinderApiView(FlatMultipleModelAPIView):
    sorting_fields = ['name']
    pagination_class = None

    def get_querylist(self):
        word = self.kwargs['word']
        category = self.kwargs['category']
        querylist = list()
        if category == 'all':
            querylist = [
                {'queryset': Species.objects.filter(scientificName__icontains=word),
                 'serializer_class': SpeciesFinderSerializer},
                {'queryset': Synonymy.objects.filter(scientificName__icontains=word),
                 'serializer_class': SynonymysFinderSerializer},
                {'queryset': Family.objects.filter(name__icontains=word), 'serializer_class': FamilysFinderSerializer},
                {'queryset': Genus.objects.filter(name__icontains=word), 'serializer_class': GenusFinderSerializer},
                {'queryset': CommonName.objects.filter(name__icontains=word),
                 'serializer_class': CommonNameFinderSerializer},
            ]
        elif category == 'species':
            querylist = [
                {'queryset': Species.objects.filter(scientificName__icontains=word),
                 'serializer_class': SpeciesFinderSerializer},
            ]
        elif category == 'synonyms':
            querylist = [
                {'queryset': Synonymy.objects.filter(scientificName__icontains=word),
                 'serializer_class': SynonymysFinderSerializer},
            ]
        elif category == 'families':
            querylist = [
                {'queryset': Family.objects.filter(name__icontains=word), 'serializer_class': FamilysFinderSerializer},
            ]
        elif category == 'genus':
            querylist = [
                {'queryset': Genus.objects.filter(name__icontains=word), 'serializer_class': GenusFinderSerializer},
            ]
        elif category == 'common_names':
            querylist = [
                {'queryset': CommonName.objects.filter(name__icontains=word),
                 'serializer_class': CommonNameFinderSerializer},
            ]
        return querylist


class SpeciesFilterApiView(FlatMultipleModelAPIView):
    sorting_fields = ['name']
    pagination_class = LimitPagination

    def get_querylist(self):
        query_species = Q()
        query_synonymy = Q()
        division = self.request.query_params.get('division')
        if division:
            query_species &= Q(genus__family__order__class_name__division_id__in=division)
            query_synonymy &= Q(species__genus__family__order__class_name__division_id__in=division)
        class_name = self.request.query_params.getlist('class_name')
        if class_name:
            query_species &= Q(genus__family__order__class_name_id__in=class_name)
            query_synonymy &= Q(species__genus__family__order__class_name_id__in=class_name)
        order = self.request.query_params.getlist('order')
        if order:
            query_species &= Q(genus__family__order_id__in=order)
            query_synonymy &= Q(species__genus__family__order_id__in=order)
        family = self.request.query_params.getlist('family')
        if family:
            query_species &= Q(genus__family_id__in=family)
            query_synonymy &= Q(species__genus__family_id__in=family)
        habit = self.request.query_params.getlist('habit')
        if habit:
            query_species &= Q(habit_id__in=habit)
            query_synonymy &= Q(species__habit_id__in=habit)
        genus = self.request.query_params.getlist('genus')
        if genus:
            query_species &= Q(genus_id__in=genus)
            query_synonymy &= Q(species__genus_id__in=genus)
        common_name = self.request.query_params.getlist('common_name')
        if common_name:
            query_species &= Q(common_names__in=common_name)
            query_synonymy &= Q(species__common_names__in=common_name)
        status = self.request.query_params.getlist('status')
        if status:
            query_species &= Q(status__in=status)
            query_synonymy &= Q(species__status__in=status)
        cycle = self.request.query_params.getlist('cycle')
        if cycle:
            query_species &= Q(ciclo__in=cycle)
            query_synonymy &= Q(species__ciclo__in=cycle)
        region = self.request.query_params.getlist('region')
        if region:
            query_species &= Q(region__in=region)
            query_synonymy &= Q(species__region__in=region)
        conservation = self.request.query_params.getlist('conservation')
        if conservation:
            query_species &= Q(conservation_state__in=conservation)
            query_synonymy &= Q(species__conservation_state__in=conservation)

        species = self.request.query_params.get('species_filter')
        synonymys = self.request.query_params.get('synonymys_filter')
        images_filter = self.request.query_params.get('images_filter')
        if images_filter:
            querylist = [
                {'queryset': Species.objects.filter(query_species).exclude(voucherimported__isnull=True).exclude(
                    voucherimported__image_public_resized_10__exact=''), 'serializer_class': SpeciesFinderSerializer},
            ]
        else:
            if species and synonymys:
                querylist = [
                    {'queryset': Species.objects.filter(query_species), 'serializer_class': SpeciesFinderSerializer},
                    {'queryset': Synonymy.objects.filter(query_synonymy),
                     'serializer_class': SynonymysFinderSerializer},
                ]
            elif species:
                querylist = [
                    {'queryset': Species.objects.filter(query_species), 'serializer_class': SpeciesFinderSerializer},
                ]
            elif synonymys:
                querylist = [
                    {'queryset': Synonymy.objects.filter(query_synonymy),
                     'serializer_class': SynonymysFinderSerializer},
                ]
            else:
                querylist = [
                    {'queryset': Species.objects.filter(query_species), 'serializer_class': SpeciesFinderSerializer},
                    {'queryset': Synonymy.objects.filter(query_synonymy),
                     'serializer_class': SynonymysFinderSerializer},
                ]

        return querylist


class MenuApiView(ObjectMultipleModelAPIView):
    pagination_class = None

    def get_querylist(self):
        querylist = [
            {'queryset': Division.objects.all().order_by('name'), 'serializer_class': DivisionSerializer},
            {'queryset': Class_name.objects.all().order_by('name'), 'serializer_class': ClassSerializer},
            {'queryset': Order.objects.all().order_by('name')[:5], 'serializer_class': OrderSerializer},
            {'queryset': Family.objects.all().order_by('name')[:5], 'serializer_class': FamilySerializer},
            {'queryset': Habit.objects.all().order_by('name')[:5], 'serializer_class': HabitSerializer},
            {'queryset': Region.objects.all().order_by('name')[:5], 'serializer_class': RegionSerializer},
            {'queryset': ConservationState.objects.all().order_by('order')[:5],
             'serializer_class': ConservationStateSerializer},
        ]
        return querylist


class MenuFilterApiView(ObjectMultipleModelAPIView):
    pagination_class = None
    QUERIES = {
        "division": {
            "model": Division,
            "serializer": DivisionSerializer
        },
        "class_name": {
            "model": Class_name,
            "serializer": ClassSerializer
        },
        "order": {
            "model": Order,
            "serializer": OrderSerializer
        },
        "family": {
            "model": Family,
            "serializer": FamilySerializer
        },
        "habit": {
            "model": Habit,
            "serializer": HabitSerializer
        },
        "status": {
            "model": Status,
            "serializer": StatusSerializer
        },
        "ciclo": {
            "model": Ciclo,
            "serializer": CicloSerializer
        },
        "region": {
            "model": Region,
            "serializer": RegionSerializer
        },
        "conservation_state": {
            "model": ConservationState,
            "serializer": ConservationStateSerializer
        },
    }
    TAXONOMY = list(QUERIES.keys())[0:4]

    def get_querylist(self, limit=5):
        limit = int(self.kwargs['limit'])
        old_tag = ""
        prev_tag = ""
        querylist = list()
        for query_name in self.QUERIES:
            query = Q()
            tag = ""
            to_delete = ""
            additive = False
            for parameter_name in self.QUERIES:
                parameters = self.request.query_params.getlist(parameter_name)
                if query_name == parameter_name:
                    tag = "id__"
                    if query_name in self.TAXONOMY:
                        prev_tag = "{}__{}".format(query_name, prev_tag)
                        old_tag = ""
                else:
                    if query_name in self.TAXONOMY:
                        if additive:
                            if parameter_name in self.TAXONOMY:
                                tag = "{}{}__".format(tag, parameter_name)
                                old_tag = tag
                            else:
                                tag = "{}genus__species__{}__".format(old_tag, parameter_name)
                        else:
                            tag = prev_tag.replace(to_delete, "")
                            to_delete = "{}__{}".format(parameter_name, to_delete)
                    else:
                        if parameter_name in self.TAXONOMY:
                            tag = "species__genus__family__order__class_name__division__".replace(to_delete, "")
                            to_delete = "{}{}__".format(to_delete, parameter_name)
                        else:
                            tag = "species__{}__".format(parameter_name)
                logging.debug("Query: {}\tParameter: {}\n{}in".format(query_name, parameter_name, tag))
                if len(parameters) > 0:
                    query &= Q(**{"{}in".format(tag): parameters})
                    logging.debug(query)
                if tag == "id__":
                    tag = ""
                    additive = True
            results = self.QUERIES[query_name]["model"].objects.filter(query).distinct().order_by('name')
            if limit != 0 and query_name not in list(self.QUERIES.keys())[0:2] + ["status"]:
                results = results[:limit]
            querylist.append({
                "queryset": results, "serializer_class": self.QUERIES[query_name]["serializer"],
            })
        return querylist


class DistributionList(ListAPIView):
    serializer_class = DistributionSerializer
    queryset = VoucherImported.objects.all()

    def get(self, request, specie_id=None, **kwargs):
        items = VoucherImported.objects.filter(scientificName=specie_id)
        distribution = DistributionSerializer(items, many=True)

        return Response(status=status.HTTP_200_OK, data=distribution.data)


class ImagesList(ListAPIView):
    serializer_class = ImagesSerializer
    queryset = VoucherImported.objects.all()

    def get(self, request, specie_id=None, **kwargs):
        items = VoucherImported.objects.filter(scientificName=specie_id).exclude(image_public_resized_10__exact='')
        images = ImagesSerializer(items, many=True)

        return Response(status=status.HTTP_200_OK, data=images.data)


class GalleryList(ListAPIView):
    serializer_class = GalleryPhotosSerializer
    queryset = GalleryImage.objects.all()

    def get(self, request, specie_id=None, **kwargs):
        items = GalleryImage.objects.filter(scientificName=specie_id)
        images = GalleryPhotosSerializer(items, many=True)
        return Response(status=status.HTTP_200_OK, data=images.data)


class ImagesFilterApiView(FlatMultipleModelAPIView):
    pagination_class = LimitPaginationImages

    def get_querylist(self):
        query_images = Q()
        division = self.request.query_params.get('division')
        if division:
            query_images &= Q(scientificName__genus__family__order__class_name__division_id__in=division)
        class_name = self.request.query_params.getlist('class_name')
        if class_name:
            query_images &= Q(scientificName__genus__family__order__class_name_id__in=class_name)
        order = self.request.query_params.getlist('order')
        if order:
            query_images &= Q(scientificName__genus__family__order_id__in=order)
        family = self.request.query_params.getlist('family')
        if family:
            query_images &= Q(scientificName__genus__family_id__in=family)
        habit = self.request.query_params.getlist('habit')
        if habit:
            query_images &= Q(scientificName__habit_id__in=habit)
        genus = self.request.query_params.getlist('genus')
        if genus:
            query_images &= Q(scientificName__genus_id__in=genus)
        common_name = self.request.query_params.getlist('common_name')
        if common_name:
            query_images &= Q(scientificName__common_names__in=common_name)
        status = self.request.query_params.getlist('status')
        if status:
            query_images &= Q(scientificName__status__in=status)
        cycle = self.request.query_params.getlist('cycle')
        if cycle:
            query_images &= Q(scientificName__ciclo__in=cycle)
        region = self.request.query_params.getlist('region')
        if region:
            query_images &= Q(scientificName__region__in=region)
        conservation = self.request.query_params.getlist('conservation')
        if conservation:
            query_images &= Q(scientificName__conservation_state__in=conservation)
        querylist = [
            {'queryset': VoucherImported.objects.filter(query_images).exclude(
                image_public_resized_10__exact='').order_by('scientificName'), 'serializer_class': ImagesSerializer},

        ]
        return querylist


class SpeciesCountView(APIView):
    """
    A view that returns the count of active species.
    """
    renderer_classes = (JSONRenderer,)

    def get(self, request, format=None):
        query_species = Q()
        query_synonymy = Q()
        division = self.request.query_params.get('division')
        if division:
            query_species &= Q(genus__family__order__class_name__division_id__in=division)
            query_synonymy &= Q(species__genus__family__order__class_name__division_id__in=division)
        class_name = self.request.query_params.getlist('class_name')
        if class_name:
            query_species &= Q(genus__family__order__class_name_id__in=class_name)
            query_synonymy &= Q(species__genus__family__order__class_name_id__in=class_name)
        order = self.request.query_params.getlist('order')
        if order:
            query_species &= Q(genus__family__order_id__in=order)
            query_synonymy &= Q(species__genus__family__order_id__in=order)
        family = self.request.query_params.getlist('family')
        if family:
            query_species &= Q(genus__family_id__in=family)
            query_synonymy &= Q(species__genus__family_id__in=family)
        habit = self.request.query_params.getlist('habit')
        if habit:
            query_species &= Q(habit_id__in=habit)
            query_synonymy &= Q(species__habit_id__in=habit)
        genus = self.request.query_params.getlist('genus')
        if genus:
            query_species &= Q(genus_id__in=genus)
            query_synonymy &= Q(species__genus_id__in=genus)
        common_name = self.request.query_params.getlist('common_name')
        if common_name:
            query_species &= Q(common_names__in=common_name)
            query_synonymy &= Q(species__common_names__in=common_name)
        status = self.request.query_params.getlist('status')
        if status:
            query_species &= Q(status__in=status)
            query_synonymy &= Q(species__status__in=status)
        cycle = self.request.query_params.getlist('cycle')
        if cycle:
            query_species &= Q(ciclo__in=cycle)
            query_synonymy &= Q(species__ciclo__in=cycle)
        region = self.request.query_params.getlist('region')
        if region:
            query_species &= Q(region__in=region)
            query_synonymy &= Q(species__region__in=region)
        conservation = self.request.query_params.getlist('conservation')
        if conservation:
            query_species &= Q(conservation_state__in=conservation)
            query_synonymy &= Q(species__conservation_state__in=conservation)
        species = self.request.query_params.get('species_filter')
        synonymys = self.request.query_params.get('synonymys_filter')
        images_filter = self.request.query_params.get('images_filter')
        if images_filter:
            species_count = Species.objects.filter(query_species).exclude(voucherimported__isnull=True).exclude(
                voucherimported__image_public_resized_10__exact='').count()
            synonymys_count = 0
        else:
            if species and synonymys:
                species_count = Species.objects.filter(query_species).count()
                synonymys_count = Synonymy.objects.filter(query_synonymy).count()
            elif species:
                species_count = Species.objects.filter(query_species).count()
                synonymys_count = 0
            elif synonymys:
                species_count = 0
                synonymys_count = Synonymy.objects.filter(query_synonymy).count()
            else:
                species_count = Species.objects.filter(query_species).count()
                synonymys_count = Synonymy.objects.filter(query_synonymy).count()

        content = {'species_count': species_count, 'synonymys_count': synonymys_count}
        return Response(content)


class ImagesCountApiView(APIView):
    """
    A view that returns the count of active images.
    """
    renderer_classes = (JSONRenderer,)

    def get(self, request, format=None):
        query_images = Q()
        division = self.request.query_params.get('division')
        if division:
            query_images &= Q(scientificName__genus__family__order__class_name__division_id__in=division)
        class_name = self.request.query_params.getlist('class_name')
        if class_name:
            query_images &= Q(scientificName__genus__family__order__class_name_id__in=class_name)
        order = self.request.query_params.getlist('order')
        if order:
            query_images &= Q(scientificName__genus__family__order_id__in=order)
        family = self.request.query_params.getlist('family')
        if family:
            query_images &= Q(scientificName__genus__family_id__in=family)
        habit = self.request.query_params.getlist('habit')
        if habit:
            query_images &= Q(scientificName__habit_id__in=habit)
        genus = self.request.query_params.getlist('genus')
        if genus:
            query_images &= Q(scientificName__genus_id__in=genus)
        common_name = self.request.query_params.getlist('common_name')
        if common_name:
            query_images &= Q(scientificName__common_names__in=common_name)
        status = self.request.query_params.getlist('status')
        if status:
            query_images &= Q(scientificName__status__in=status)
        cycle = self.request.query_params.getlist('cycle')
        if cycle:
            query_images &= Q(scientificName__ciclo__in=cycle)
        region = self.request.query_params.getlist('region')
        if region:
            query_images &= Q(scientificName__region__in=region)
        conservation = self.request.query_params.getlist('conservation')
        if conservation:
            query_images &= Q(scientificName__conservation_state__in=conservation)
        images_count = VoucherImported.objects.filter(query_images).exclude(image_public_resized_10__exact='').count()
        content = {'images_count': images_count}
        return Response(content)


class ImageDetails(ListAPIView):
    serializer_class = ImagesSerializer
    queryset = VoucherImported.objects.all()

    def get(self, request, voucher_id=None, **kwargs):
        items = VoucherImported.objects.get(pk=voucher_id)
        voucher = ImagesSerializer(items, many=False, context={'request': request})
        return Response(status=status.HTTP_200_OK, data=voucher.data)


class TotalImages(APIView):
    """
    A view that returns the count of active images.
    """
    renderer_classes = (JSONRenderer,)

    def get(self, request, format=None):
        images_count = VoucherImported.objects.all().exclude(image_public_resized_10__exact='').count()
        content = {'total': images_count}
        return Response(content)


class TotalSpecies(APIView):
    """
    A view that returns the count of active images.
    """
    renderer_classes = (JSONRenderer,)

    def get(self, request, format=None):
        species_count = Species.objects.all().exclude(voucherimported__isnull=True).exclude(
            voucherimported__image_public_resized_10__exact='').count()
        content = {'total': species_count}
        return Response(content)


class BannerSpecie(APIView):
    """
    Generates image of banner and url to 'herbariodigital.cl'
    """
    renderer_classes = (JSONRenderer,)

    def get(self, request, format=None, **kwargs):
        specie_id = kwargs.get("specie_id")
        specie = Species.objects.filter(id=specie_id).first()
        logging.debug("Getting banner for {}".format(specie.scientificName))
        banners = BannerImage.objects.filter(specie_id=specie)
        if banners.count() == 0:
            logging.warning("No banner found for {} species".format(specie.scientificName))
            return Response(
                {
                    "msg": "No banner for specie {}".format(
                        specie.scientificName
                    )
                }, status=501)
        return Response({
            'image': banners.first().banner.url,
            'url': "{}/catalog/details/Species/{}/".format(
                os.environ.get("HERBARIUM_FRONTEND"),
                specie_id
            )
        })


def login(request):
    if request.method == 'POST':
        logging.debug("Authorizing backend")
        authorization_header = request.META['HTTP_AUTHORIZATION']
        if not authorization_header:
            logging.warning("Authorization header missing")
            return HttpResponseBadRequest('Authorization header missing')

        auth_type, encoded_credentials = authorization_header.split(' ', 1)
        if auth_type.lower() != 'basic':
            logging.warning("Invalid authentication type: {}".format(auth_type))
            return HttpResponseBadRequest('Invalid authentication type')

        decoded_credentials = base64.b64decode(encoded_credentials).decode('utf-8')
        username, password = decoded_credentials.split(':', 1)

        # Authenticate user
        user = authenticate(request, username=username, password=password)

        # Generate JWT token
        if user is not None:
            payload = {
                'user_id': user.id,
                'username': user.username,
                'exp': dt.datetime.utcnow() + dt.timedelta(days=1)
            }
            jwt_token = jwt.encode(payload, settings.SECRET_KEY, algorithm='HS256')
            return JsonResponse({'token': jwt_token})
        else:
            return HttpResponse(status=401)
