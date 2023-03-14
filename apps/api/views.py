from django.db.models import Q
from drf_multiple_model.pagination import MultipleModelLimitOffsetPagination
from drf_multiple_model.views import FlatMultipleModelAPIView, ObjectMultipleModelAPIView
from rest_framework import status
from rest_framework.generics import ListAPIView
from rest_framework.renderers import JSONRenderer
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.catalog.models import Species, Synonymy, Family, Division, Class_name, Order, Habit, Status, Ciclo, Genus, \
    CommonName, Region, ConservationState
from apps.digitalization.models import VoucherImported
from .serializers import SpecieSerializer, SynonymySerializer, SpeciesSerializer, SpeciesFinderSerializer, \
    SynonymysFinderSerializer, FamilysFinderSerializer, DivisionSerializer, ClassSerializer, OrderSerializer, \
    FamilySerializer, HabitSerializer, StatusSerializer, CicloSerializer, GenusFinderSerializer, \
    DistributionSerializer, ImagesSerializer, CommonNameFinderSerializer, RegionSerializer, ConservationStateSerializer


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
            query_species &= Q(genus__family__orden__class_name__division_id__in=division)
            query_synonymy &= Q(species__genus__family__orden__class_name__division_id__in=division)
        class_name = self.request.query_params.getlist('class_name')
        if class_name:
            query_species &= Q(genus__family__orden__class_name_id__in=class_name)
            query_synonymy &= Q(species__genus__family__orden__class_name_id__in=class_name)
        orden = self.request.query_params.getlist('order')
        if orden:
            query_species &= Q(genus__family__orden_id__in=orden)
            query_synonymy &= Q(species__genus__family__orden_id__in=orden)
        family = self.request.query_params.getlist('family')
        if family:
            query_species &= Q(genus__family_id__in=family)
            query_synonymy &= Q(species__genus__family_id__in=family)
        habit = self.request.query_params.getlist('habit')
        if habit:
            query_species &= Q(habito_id__in=habit)
            query_synonymy &= Q(species__habito_id__in=habit)
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
            query_species &= Q(region_distribution__in=region)
            query_synonymy &= Q(species__region_distribution__in=region)
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

    def get_querylist(self, limit=5):
        limit = int(self.kwargs['limit'])
        query_division = Q()
        query_class_name = Q()
        query_order = Q()
        query_family = Q()
        query_habit = Q()
        query_status = Q()
        query_cycle = Q()
        query_region = Q()
        query_conservation = Q()
        division = self.request.query_params.getlist('division')
        if division:
            query_division &= Q(id__in=division)
            query_class_name &= Q(division__in=division)
            query_order &= Q(class_name__division__in=division)
            query_family &= Q(orden__class_name__division__in=division)
            query_habit &= Q(species__genus__family__orden__class_name__division__in=division)
            query_status &= Q(species__genus__family__orden__class_name__division__in=division)
            query_cycle &= Q(species__genus__family__orden__class_name__division__in=division)
            query_region &= Q(species__genus__family__orden__class_name__division__in=division)
            query_conservation &= Q(species__genus__family__orden__class_name__division__in=division)
        class_name = self.request.query_params.getlist('class_name')
        if class_name:
            query_division &= Q(class_name__in=class_name)
            query_class_name &= Q(id__in=class_name)
            query_order &= Q(class_name__in=class_name)
            query_family &= Q(orden__class_name__in=class_name)
            query_habit &= Q(species__genus__family__orden__class_name__in=class_name)
            query_status &= Q(species__genus__family__orden__class_name__in=class_name)
            query_cycle &= Q(species__genus__family__orden__class_name__in=class_name)
            query_region &= Q(species__genus__family__orden__class_name__in=class_name)
            query_conservation &= Q(species__genus__family__orden__class_name__in=class_name)
        order = self.request.query_params.getlist('order')
        if order:
            query_division &= Q(class_name__order__in=order)
            query_class_name &= Q(order__in=order)
            query_order &= Q(id__in=order)
            query_family &= Q(orden__in=order)
            query_habit &= Q(species__genus__family__orden__in=order)
            query_status &= Q(species__genus__family__orden__in=order)
            query_cycle &= Q(species__genus__family__orden__in=order)
            query_region &= Q(species__genus__family__orden__in=order)
            query_conservation &= Q(species__genus__family__orden__in=order)
        family = self.request.query_params.getlist('family')
        if family:
            query_division &= Q(class_name__order__family__in=family)
            query_class_name &= Q(order__family__in=family)
            query_order &= Q(family__in=family)
            query_family &= Q(id__in=family)
            query_habit &= Q(species__genus__family__in=family)
            query_status &= Q(species__genus__family__in=family)
            query_cycle &= Q(species__genus__family__in=family)
            query_region &= Q(species__genus__family__in=family)
            query_conservation &= Q(species__genus__family__in=family)
        habit = self.request.query_params.getlist('habit')
        if habit:
            query_division &= Q(class_name__order__family__genus__species__habito__in=habit)
            query_class_name &= Q(order__family__genus__species__habito__in=habit)
            query_order &= Q(family__genus__species__habito__in=habit)
            query_family &= Q(genus__species__habito__in=habit)
            query_habit &= Q(id__in=habit)
            query_status &= Q(species__habito__in=habit)
            query_cycle &= Q(species__habito__in=habit)
            query_region &= Q(species__habito__in=habit)
            query_conservation &= Q(species__habito__in=habit)
        status = self.request.query_params.getlist('status')
        if status:
            query_division &= Q(class_name__order__family__genus__species__status__in=status)
            query_class_name &= Q(order__family__genus__species__status__in=status)
            query_order &= Q(family__genus__species__status__in=status)
            query_family &= Q(genus__species__status__in=status)
            query_habit &= Q(species__status__in=status)
            query_status &= Q(id__in=status)
            query_cycle &= Q(species__status__in=status)
            query_region &= Q(species__status__in=status)
            query_conservation &= Q(species__status__in=status)
        cycle = self.request.query_params.getlist('cycle')
        if cycle:
            query_division &= Q(class_name__order__family__genus__species__ciclo__in=cycle)
            query_class_name &= Q(order__family__genus__species__ciclo__in=cycle)
            query_order &= Q(family__genus__species__ciclo__in=cycle)
            query_family &= Q(genus__species__ciclo__in=cycle)
            query_habit &= Q(species__ciclo__in=cycle)
            query_status &= Q(species__ciclo__in=cycle)
            query_cycle &= Q(id__in=cycle)
            query_region &= Q(species__ciclo__in=cycle)
            query_conservation &= Q(species__ciclo__in=cycle)
        region = self.request.query_params.getlist('region')
        if region:
            query_division &= Q(class_name__order__family__genus__species__region_distribution__in=region)
            query_class_name &= Q(order__family__genus__species__region_distribution__in=region)
            query_order &= Q(family__genus__species__region_distribution__in=region)
            query_family &= Q(genus__species__region_distribution__in=region)
            query_habit &= Q(species__region_distribution__in=region)
            query_status &= Q(species__region_distribution__in=region)
            query_cycle &= Q(species__region_distribution__in=region)
            query_region &= Q(id__in=region)
            query_conservation &= Q(id__in=region)
        conservation = self.request.query_params.getlist('conservation')
        if conservation:
            query_division &= Q(class_name__order__family__genus__species__conservation_state__in=conservation)
            query_class_name &= Q(order__family__genus__species__conservation_state__in=conservation)
            query_order &= Q(family__genus__species__conservation_state__in=conservation)
            query_family &= Q(genus__species__conservation_state__in=conservation)
            query_habit &= Q(species__conservation_state__in=conservation)
            query_status &= Q(species__conservation_state__in=conservation)
            query_cycle &= Q(species__conservation_state__in=conservation)
            query_region &= Q(id__in=conservation)
            query_conservation &= Q(id__in=conservation)
        if limit == 0:
            orders = Order.objects.filter(query_order).distinct().order_by('name')
            families = Family.objects.filter(query_family).distinct().order_by('name')
            habits = Habit.objects.filter(query_habit).distinct().order_by('name')
            cycles = Ciclo.objects.filter(query_cycle).distinct().order_by('name')
            regions = Region.objects.filter(query_region).distinct().order_by('order')
            conservations = ConservationState.objects.filter(query_conservation).distinct().order_by('order')
        else:
            orders = Order.objects.filter(query_order).distinct().order_by('name')[:limit]
            families = Family.objects.filter(query_family).distinct().order_by('name')[:limit]
            habits = Habit.objects.filter(query_habit).distinct().order_by('name')[:limit]
            cycles = Ciclo.objects.filter(query_cycle).distinct().order_by('name')[:limit]
            regions = Region.objects.filter(query_region).distinct().order_by('order')[:limit]
            conservations = ConservationState.objects.filter(query_conservation).distinct().order_by('order')[:limit]

        querylist = [
            {'queryset': Division.objects.filter(query_division).distinct().order_by('name'),
             'serializer_class': DivisionSerializer},
            {'queryset': Class_name.objects.filter(query_class_name).distinct().order_by('name'),
             'serializer_class': ClassSerializer},
            {'queryset': orders, 'serializer_class': OrderSerializer},
            {'queryset': families, 'serializer_class': FamilySerializer},
            {'queryset': habits, 'serializer_class': HabitSerializer},
            {'queryset': Status.objects.filter(query_status).distinct().order_by('name'),
             'serializer_class': StatusSerializer},
            {'queryset': cycles, 'serializer_class': CicloSerializer},
            {'queryset': regions, 'serializer_class': RegionSerializer},
            {'queryset': conservations, 'serializer_class': ConservationStateSerializer},
        ]
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


class ImagesFilterApiView(FlatMultipleModelAPIView):
    pagination_class = LimitPaginationImages

    def get_querylist(self):
        query_images = Q()
        division = self.request.query_params.get('division')
        if division:
            query_images &= Q(scientificName__genus__family__orden__class_name__division_id__in=division)
        class_name = self.request.query_params.getlist('class_name')
        if class_name:
            query_images &= Q(scientificName__genus__family__orden__class_name_id__in=class_name)
        orden = self.request.query_params.getlist('order')
        if orden:
            query_images &= Q(scientificName__genus__family__orden_id__in=orden)
        family = self.request.query_params.getlist('family')
        if family:
            query_images &= Q(scientificName__genus__family_id__in=family)
        habit = self.request.query_params.getlist('habit')
        if habit:
            query_images &= Q(scientificName__habito_id__in=habit)
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
            query_images &= Q(scientificName__region_distribution__in=region)
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
            query_species &= Q(genus__family__orden__class_name__division_id__in=division)
            query_synonymy &= Q(species__genus__family__orden__class_name__division_id__in=division)
        class_name = self.request.query_params.getlist('class_name')
        if class_name:
            query_species &= Q(genus__family__orden__class_name_id__in=class_name)
            query_synonymy &= Q(species__genus__family__orden__class_name_id__in=class_name)
        orden = self.request.query_params.getlist('order')
        if orden:
            query_species &= Q(genus__family__orden_id__in=orden)
            query_synonymy &= Q(species__genus__family__orden_id__in=orden)
        family = self.request.query_params.getlist('family')
        if family:
            query_species &= Q(genus__family_id__in=family)
            query_synonymy &= Q(species__genus__family_id__in=family)
        habit = self.request.query_params.getlist('habit')
        if habit:
            query_species &= Q(habito_id__in=habit)
            query_synonymy &= Q(species__habito_id__in=habit)
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
            query_species &= Q(region_distribution__in=region)
            query_synonymy &= Q(species__region_distribution__in=region)
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
            query_images &= Q(scientificName__genus__family__orden__class_name__division_id__in=division)
        class_name = self.request.query_params.getlist('class_name')
        if class_name:
            query_images &= Q(scientificName__genus__family__orden__class_name_id__in=class_name)
        orden = self.request.query_params.getlist('order')
        if orden:
            query_images &= Q(scientificName__genus__family__orden_id__in=orden)
        family = self.request.query_params.getlist('family')
        if family:
            query_images &= Q(scientificName__genus__family_id__in=family)
        habit = self.request.query_params.getlist('habit')
        if habit:
            query_images &= Q(scientificName__habito_id__in=habit)
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
            query_images &= Q(scientificName__region_distribution__in=region)
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
