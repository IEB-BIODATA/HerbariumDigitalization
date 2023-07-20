import json
import logging
import re
from typing import Dict, List

import pandas as pd
import tablib
from django.contrib.auth.decorators import login_required
from django.core import serializers
from django.core.handlers.wsgi import WSGIRequest
from django.core.paginator import Paginator
from django.db.models import Q
from django.forms.utils import ErrorList
from django.http import HttpResponse, JsonResponse
from django.shortcuts import render, redirect
from django.urls import reverse
from rest_framework.serializers import SerializerMetaclass

from apps.digitalization.models import VoucherImported
from .forms import DivisionForm, ClassForm, OrderForm, FamilyForm, GenusForm, SpeciesForm, SynonymyForm, BinnacleForm, \
    CommonNameForm
from .models import Species, CatalogView, SynonymyView, RegionDistributionView, Division, ClassName, Order, Family, \
    Genus, Synonymy, Region, CommonName, Binnacle, PlantHabit, EnvironmentalHabit, Cycle, TaxonomicModel
from .utils import generate_etiquete
from .tasks import update_voucher_name
from ..api.serializers import DivisionSerializer, ClassSerializer, OrderSerializer, \
    FamilySerializer, GenusSerializer, SynonymysSerializer, CommonNameSerializer, SpeciesSerializer, \
    CatalogViewSerializer


@login_required
def catalog_download(request):
    if request.method == 'GET':
        headers1 = ['id', 'id_taxa', 'kingdom', 'division', 'class_name', 'order', 'family', 'genus', 'scientificName',
                    'scientificNameFull'
            , 'specificEpithet', 'scientificNameAuthorship', 'subespecie', 'autoresSsp', 'variedad', 'autoresVariedad',
                    'forma', 'autoresForma'
            , 'enArgentina', 'enBolivia', 'enPeru', 'habit', 'ciclo', 'status', 'alturaMinima', 'alturaMaxima',
                    'notas', 'id_tipo'
            , 'publicacion', 'volumen', 'paginas', 'anio', 'determined', 'id_taxa_origin']
        headers2 = ['id', 'specie_id', 'id_taxa', 'specie scientificName', 'synonymy id', 'synonymy scientificName',
                    'scientificNameFull', 'genus', 'specificEpithet', 'scientificNameAuthorship'
            , 'subespecie', 'autoresSsp', 'variedad', 'autoresVariedad', 'forma', 'autoresForma']
        headers3 = ['id', 'specie_id', 'id_taxa', 'specie scientificName', 'region name', 'region key']
        species = CatalogView.objects.values_list('id', 'id_taxa', 'kingdom', 'division', 'class_name', 'order',
                                                  'family', 'genus', 'scientificName', 'scientificNameFull'
                                                  , 'specificEpithet', 'scientificNameAuthorship', 'subespecie',
                                                  'autoresSsp', 'variedad', 'autoresVariedad', 'forma', 'autoresForma'
                                                  , 'enArgentina', 'enBolivia', 'enPeru', 'habit', 'ciclo', 'status',
                                                  'alturaMinima', 'alturaMaxima', 'notas', 'id_tipo'
                                                  , 'publicacion', 'volumen', 'paginas', 'anio', 'determined',
                                                  'id_taxa_origin').order_by('id')
        synonymys = SynonymyView.objects.values_list('id', 'specie_id', 'id_taxa', 'specie_scientificname',
                                                     'synonymy_id', 'scientificName', 'scientificNameFull', 'genus',
                                                     'specificEpithet', 'scientificNameAuthorship'
                                                     , 'subespecie', 'autoresSsp', 'variedad', 'autoresVariedad',
                                                     'forma', 'autoresForma').order_by('id')
        region = RegionDistributionView.objects.values_list('id', 'specie_id', 'id_taxa',
                                                                         'specie_scientificname', 'region_name',
                                                                         'region_key').order_by('id')
        databook = tablib.Databook()
        data_set1 = tablib.Dataset(*species, headers=headers1, title='Species')
        data_set2 = tablib.Dataset(*synonymys, headers=headers2, title='Synonymys')
        data_set3 = tablib.Dataset(*region, headers=headers3, title='Region Distribution')
        databook.add_sheet(data_set1)
        databook.add_sheet(data_set2)
        databook.add_sheet(data_set3)
        response = HttpResponse(databook.xlsx, content_type='application/vnd.ms-Excel')
        response['Content-Disposition'] = "attachment; filename=catalog.xlsx"
        return response


def __catalog_table__(
        request: WSGIRequest,
        model: TaxonomicModel,
        serializer: SerializerMetaclass,
        sort_by_func: Dict[int, str],
        model_name: str,
        add_searchable: Q = None
) -> JsonResponse:
    entries = model.objects.all()
    search_value = request.GET.get('search[value]', None)
    if search_value:
        logging.debug("Searching with {}".format(search_value))
        search_query = (
                model.get_query_name(search_value) |
                model.get_parent_query(search_value) |
                model.get_created_by_query(search_value) |
                Q(created_at__icontains=search_value) |
                Q(updated_at__icontains=search_value)
        )
        if add_searchable:
            search_query = search_query | add_searchable
        entries = entries.filter(search_query)
    sort_by = int(request.GET.get('order[0][column]', 4))
    sort_type = request.GET.get('order[0][dir]', 'desc')

    if sort_by in sort_by_func:
        logging.debug("Order by {} ({}) in {} order".format(
            sort_by,
            sort_by_func[sort_by],
            "ascending" if sort_type == "asc" else "descending"
        ))
        entries = entries.order_by(
            ('' if sort_type == 'asc' else '-') + sort_by_func[sort_by]
        )

    length = int(request.GET.get('length', 10))
    start = int(request.GET.get('start', 0))
    paginator = Paginator(entries, length)
    page_number = start // length + 1
    page_obj = paginator.get_page(page_number)
    data = list()

    logging.debug("Returning {} {}, starting at {} with {} items".format(
        entries.count(), model_name, start + 1, length
    ))

    for item in page_obj:
        data.append(serializer(
            instance=item,
            many=False,
            context=request
        ).data)
    return JsonResponse({
        'draw': int(request.GET.get('draw', 0)),
        'recordsTotal': entries.count(),
        'recordsFiltered': paginator.count,
        'data': data
    })


@login_required
def list_division(request):
    return render(request, 'catalog/list_catalog.html', {
        'table_url': reverse('division_table'),
        'rank_name': 'name',
        'parent_rank': 'kingdom',
        'update_rank_url': reverse('update_division', kwargs={"id": 0}),
        'rank_title': 'División',
        'rank_name_title': 'Nombre',
        'parent_rank_title': 'Reino',
        'deletable': 0,
    })


@login_required
def division_table(request):
    sort_by_func = {
        0: 'name',
        1: 'kingdom__name',
        2: 'created_by__username',
        3: 'created_at',
        4: 'updated_at',
    }
    return __catalog_table__(
        request, Division, DivisionSerializer,
        sort_by_func, "divisions"
    )


@login_required
def create_division(request):
    if request.method == 'POST':
        form = DivisionForm(request.POST)
        html_instructions = ""
        if form.is_valid():
            try:
                new_division = form.save()
                binnacle = Binnacle(type_update="Nuevo", model="Division",
                                    description="Se crea Division " + new_division.name, created_by=request.user)
                binnacle.save()
                CatalogView.refresh_view()
                SynonymyView.refresh_view()
                RegionDistributionView.refresh_view()
                return redirect('list_division')
            except Exception as e:
                print(e)
                pass
    else:
        form = DivisionForm()
    return render(request, 'catalog/create_division.html', {'form': form})


def update_division(request, id):
    division = Division.objects.get(id=id)
    if request.method == 'POST':
        form = DivisionForm(request.POST, instance=division)
        if form.is_valid():
            new_division = form.save()
            binnacle = Binnacle(type_update="Actualización", model="Division",
                                description="Se actualiza Division " + division.name + " en " + new_division.name,
                                created_by=request.user)
            binnacle.save()
            CatalogView.refresh_view()
            SynonymyView.refresh_view()
            RegionDistributionView.refresh_view()
            return redirect('list_division')
    else:
        form = DivisionForm(instance=division)

    return render(request, 'catalog/update_division.html', {'form': form, 'id': id})


@login_required
def list_class(request):
    return render(request, 'catalog/list_catalog.html', {
        'table_url': reverse('class_table'),
        'rank_name': 'name',
        'parent_rank': 'division',
        'update_rank_url': reverse('update_class', kwargs={"id": 0}),
        'rank_title': 'Clase',
        'rank_name_title': 'Nombre',
        'parent_rank_title': 'División',
        'deletable': 0,
    })


@login_required
def class_table(request):
    sort_by_func = {
        0: 'name',
        1: 'division__name',
        2: 'created_by__username',
        3: 'created_at',
        4: 'updated_at',
    }
    return __catalog_table__(
        request, ClassName, ClassSerializer,
        sort_by_func, "classes"
    )


@login_required
def create_class(request):
    if request.method == 'POST':
        form = ClassForm(request.POST)
        html_instructions = ""
        if form.is_valid():
            try:
                new_class = form.save()
                binnacle = Binnacle(type_update="Nuevo", model="Clase", description="Se crea Clase " + new_class.name)
                binnacle.save()
                CatalogView.refresh_view()
                SynonymyView.refresh_view()
                RegionDistributionView.refresh_view()
                return redirect('list_class')
            except Exception as e:
                print(e)
                pass
    else:
        form = ClassForm()
    return render(request, 'catalog/create_class.html', {'form': form})


def update_class(request, id):
    class_name = ClassName.objects.get(id=id)
    if request.method == 'POST':
        form = ClassForm(request.POST, instance=class_name)
        if form.is_valid():
            new_class = form.save()
            binnacle = Binnacle(type_update="Actualización", model="Clase",
                                description="Se actualiza Clase {} ({}) en {}".format(
                                    class_name.name,
                                    class_name.id,
                                    new_class.name
                                ),
                                created_by=request.user)
            binnacle.save()
            CatalogView.refresh_view()
            SynonymyView.refresh_view()
            RegionDistributionView.refresh_view()
            return redirect('list_class')
    else:
        form = ClassForm(instance=class_name)

    return render(request, 'catalog/update_class.html', {'form': form, 'id': id})


@login_required
def list_order(request):
    return render(request, 'catalog/list_catalog.html', {
        'table_url': reverse('order_table'),
        'rank_name': 'name',
        'parent_rank': 'class_name',
        'update_rank_url': reverse('update_order', kwargs={"id": 0}),
        'rank_title': 'Orden',
        'rank_name_title': 'Nombre',
        'parent_rank_title': 'Clase',
        'deletable': 0,
    })


@login_required
def order_table(request):
    sort_by_func = {
        0: 'name',
        1: 'class_name__name',
        2: 'created_by__username',
        3: 'created_at',
        4: 'updated_at',
    }
    return __catalog_table__(
        request, Order, OrderSerializer,
        sort_by_func, "orders"
    )


@login_required
def create_order(request):
    if request.method == 'POST':
        form = OrderForm(request.POST)
        html_instructions = ""
        if form.is_valid():
            try:
                new_order = form.save()
                binnacle = Binnacle(type_update="Nuevo", model="order", description="Se crea order " + new_order.name,
                                    created_by=request.user)
                binnacle.save()
                CatalogView.refresh_view()
                SynonymyView.refresh_view()
                RegionDistributionView.refresh_view()
                return redirect('list_order')
            except Exception as e:
                print(e)
                pass
    else:
        form = OrderForm()
    return render(request, 'catalog/create_order.html', {'form': form})


def update_order(request, id):
    order = Order.objects.get(id=id)
    if request.method == 'POST':
        form = OrderForm(request.POST, instance=order)
        if form.is_valid():
            new_order = form.save()
            binnacle = Binnacle(type_update="Actualización", model="order",
                                description="Se actualiza order {} ({}) en {}".format(
                                    order.name,
                                    order.id,
                                    new_order.name
                                ),
                                created_by=request.user)
            binnacle.save()
            CatalogView.refresh_view()
            SynonymyView.refresh_view()
            RegionDistributionView.refresh_view()
            return redirect('list_order')
    else:
        form = OrderForm(instance=order)

    return render(request, 'catalog/update_order.html', {'form': form, 'id': id})


@login_required
def list_family(request):
    return render(request, 'catalog/list_catalog.html', {
        'table_url': reverse('family_table'),
        'rank_name': 'name',
        'parent_rank': 'order',
        'update_rank_url': reverse('update_family', kwargs={"id": 0}),
        'rank_title': 'Familia',
        'rank_name_title': 'Nombre',
        'parent_rank_title': 'Orden',
        'deletable': 0,
    })


@login_required
def family_table(request):
    sort_by_func = {
        0: 'name',
        1: 'order__name',
        2: 'created_by__username',
        3: 'created_at',
        4: 'updated_at',
    }
    return __catalog_table__(
        request, Family, FamilySerializer,
        sort_by_func, "families"
    )


@login_required
def create_family(request):
    if request.method == 'POST':
        form = FamilyForm(request.POST)
        html_instructions = ""
        if form.is_valid():
            try:
                new_family = form.save()
                binnacle = Binnacle(type_update="Nuevo", model="Familia",
                                    description="Se crea Familia " + new_family.name, created_by=request.user)
                binnacle.save()
                CatalogView.refresh_view()
                SynonymyView.refresh_view()
                RegionDistributionView.refresh_view()
                return redirect('list_family')
            except Exception as e:
                print(e)
                pass
    else:
        form = FamilyForm()
    return render(request, 'catalog/create_family.html', {'form': form})


def update_family(request, id):
    family = Family.objects.get(id=id)
    if request.method == 'POST':
        form = FamilyForm(request.POST, instance=family)
        if form.is_valid():
            new_family = form.save()
            binnacle = Binnacle(type_update="Actualización", model="Familia",
                                description="Se actualiza Familia " + family.name + " en " + new_family.name,
                                created_by=request.user)
            binnacle.save()
            vouchers = VoucherImported.objects.filter(occurrenceID__voucher_state=7,
                                                      scientificName__genus__family__id=new_family.id)
            for voucher in vouchers:
                generate_etiquete(voucher.id)
            CatalogView.refresh_view()
            SynonymyView.refresh_view()
            RegionDistributionView.refresh_view()
            return redirect('list_family')
    else:
        form = FamilyForm(instance=family)

    return render(request, 'catalog/update_family.html', {'form': form, 'id': id})


@login_required
def list_genus(request):
    return render(request, 'catalog/list_catalog.html', {
        'table_url': reverse('genus_table'),
        'rank_name': 'name',
        'parent_rank': 'family',
        'update_rank_url': reverse('update_genus', kwargs={"id": 0}),
        'rank_title': 'Género',
        'rank_name_title': 'Nombre',
        'parent_rank_title': 'Familia',
        'deletable': 0,
    })


@login_required
def genus_table(request):
    sort_by_func = {
        0: 'name',
        1: 'family__name',
        2: 'created_by__username',
        3: 'created_at',
        4: 'updated_at',
    }
    return __catalog_table__(
        request, Genus, GenusSerializer,
        sort_by_func, "genuses"
    )


@login_required
def create_genus(request):
    if request.method == 'POST':
        form = GenusForm(request.POST)
        html_instructions = ""
        if form.is_valid():
            try:
                new_genus = form.save()
                binnacle = Binnacle(type_update="Nuevo", model="Genero", description="Se crea Genero " + new_genus.name,
                                    created_by=request.user)
                binnacle.save()
                CatalogView.refresh_view()
                SynonymyView.refresh_view()
                RegionDistributionView.refresh_view()
                return redirect('list_genus')
            except Exception as e:
                print(e)
                pass
    else:
        form = GenusForm()
    return render(request, 'catalog/create_genus.html', {'form': form})


def update_genus(request, id):
    genus_preview = Genus.objects.get(id=id)
    genus_preview_name = genus_preview.name
    family_preview_name = genus_preview.family.name
    form = GenusForm(instance=genus_preview)
    if request.method == 'POST':
        genus = request.POST['genus_name']
        family = Family.objects.get(id=request.POST['family_id'])
        if genus != genus_preview_name or family_preview_name != family.name:
            species = Species.objects.filter(genus=genus_preview)
            if len(request.POST) - 4 != species.count():
                genus = Genus(name=genus, family=family)
                genus.save()
                binnacle = Binnacle(type_update="Nuevo", model="Genero", description="Se crea Genero " + genus.name,
                                    created_by=request.user)
                binnacle.save()
            else:
                genus_preview.name = genus
                genus_preview.family = family
                genus_preview.save()
                genus = Genus.objects.get(id=genus_preview.id)
                binnacle = Binnacle(type_update="Actualización", model="Genero",
                                    description="Se actualiza Genero " + genus_preview.name + " en " + genus.name,
                                    created_by=request.user)
                binnacle.save()
            for specie in species:
                if 'specie_id_' + str(specie.id) in request.POST:
                    scientificName_preview = specie.scientificName
                    scientificNameDB_preview = specie.scientificNameDB
                    scientificNameFull_preview = specie.scientificNameFull
                    specificEpithet_preview = specie.specificEpithet
                    scientificNameAuthorship_preview = specie.scientificNameAuthorship
                    subespecie_preview = specie.subespecie
                    autoresSsp_preview = specie.autoresSsp
                    variedad_preview = specie.variedad
                    autoresVariedad_preview = specie.autoresVariedad
                    forma_preview = specie.forma
                    autoresForma_preview = specie.autoresForma
                    scientificName = genus.name + " " + specie.specificEpithet
                    scientificNameFull = genus.name + " " + specie.specificEpithet
                    regexp = re.compile('\((.+)\)')
                    if regexp.search(scientificNameAuthorship_preview):
                        previous_autor = regexp.search(scientificNameAuthorship_preview).group(0)
                        scientificNameAuthorship_proposal = previous_autor + " " + request.POST['autor_name']
                    else:
                        scientificNameAuthorship_proposal = '(' + scientificNameAuthorship_preview + ') ' + \
                                                            request.POST['autor_name']
                    scientificNameAuthorship = scientificNameAuthorship_proposal
                    subespecie = str(specie.subespecie)
                    autoresSsp = str(specie.autoresSsp)
                    variedad = str(specie.variedad)
                    autoresVariedad = str(specie.autoresVariedad)
                    forma = str(specie.forma)
                    autoresForma = str(specie.autoresForma)
                    if scientificNameAuthorship != None:
                        scientificNameFull += " " + scientificNameAuthorship
                    if specie.subespecie != None:
                        scientificName += " subsp. " + subespecie
                    if specie.autoresSsp != None:
                        scientificNameFull += " subsp. " + subespecie + " " + autoresSsp
                    if specie.variedad != None:
                        scientificName += " var. " + variedad
                    if specie.autoresVariedad != None:
                        scientificNameFull += " var. " + variedad + " " + autoresVariedad
                    if specie.forma != None:
                        scientificName += " fma. " + forma
                    if specie.autoresForma != None:
                        scientificNameFull += " fma. " + forma + " " + autoresForma
                    specie.scientificName = scientificName
                    specie.scientificNameFull = scientificNameFull
                    specie.scientificNameDB = scientificName.upper()
                    specie.scientificNameAuthorship = scientificNameAuthorship
                    specie.genus = genus
                    new_synonymy = Synonymy(
                        scientificName=scientificName_preview,
                        scientificNameDB=scientificNameDB_preview,
                        scientificNameFull=scientificNameFull_preview,
                        genus=genus_preview_name,
                        specificEpithet=specificEpithet_preview,
                        scientificNameAuthorship=scientificNameAuthorship_preview,
                        subespecie=subespecie_preview,
                        autoresSsp=autoresSsp_preview,
                        variedad=variedad_preview,
                        autoresVariedad=autoresVariedad_preview,
                        forma=forma_preview,
                        autoresForma=autoresForma_preview
                    )
                    new_synonymy.save()
                    specie.synonymys.add(new_synonymy)
                    specie.save()
                    vouchers = VoucherImported.objects.filter(occurrenceID__voucher_state=7,
                                                              scientificName__id=specie.id)
                    for voucher in vouchers:
                        generate_etiquete(voucher.id)
            CatalogView.refresh_view()
            SynonymyView.refresh_view()
            RegionDistributionView.refresh_view()
            return redirect('list_genus')
        else:
            errors = form.errors.setdefault("name", ErrorList())
            errors.append(u"Debe crear un nombre de genero que no exista anteriormente.")
            return render(request, 'catalog/update_genus.html', {'form': form, 'id': id})

    return render(request, 'catalog/update_genus.html', {'form': form, 'id': id})


def proposal_genus(request, id):
    species = Species.objects.filter(genus=id)
    proposal = []
    genus = request.POST['name']
    family = request.POST['family']
    autor = request.POST['autor']
    for specie in species:
        scientificName = genus + " " + specie.specificEpithet
        scientificNameFull = genus + " " + specie.specificEpithet
        scientificNameAuthorship = str(specie.scientificNameAuthorship)
        regexp = re.compile('\((.+)\)')
        if regexp.search(scientificNameAuthorship):
            previous_autor = regexp.search(scientificNameAuthorship).group(0)
            scientificNameAuthorship_proposal = previous_autor + " " + autor
        else:
            scientificNameAuthorship_proposal = '(' + scientificNameAuthorship + ') ' + autor
        subespecie = str(specie.subespecie)
        autoresSsp = str(specie.autoresSsp)
        variedad = str(specie.variedad)
        autoresVariedad = str(specie.autoresVariedad)
        forma = str(specie.forma)
        autoresForma = str(specie.autoresForma)
        if specie.scientificNameAuthorship != None:
            scientificNameFull += " " + scientificNameAuthorship_proposal
        if specie.subespecie != None:
            scientificName += " subsp. " + subespecie
        if specie.autoresSsp != None:
            scientificNameFull += " subsp. " + subespecie + " " + autoresSsp
        if specie.variedad != None:
            scientificName += " var. " + variedad
        if specie.autoresVariedad != None:
            scientificNameFull += " var. " + variedad + " " + autoresVariedad
        if specie.forma != None:
            scientificName += " fma. " + forma
        if specie.autoresForma != None:
            scientificNameFull += " fma. " + forma + " " + autoresForma
        proposal.append([specie.id, scientificName, scientificNameAuthorship_proposal])
    result = pd.DataFrame(proposal, columns=['id', 'scientificName', 'scientificNameAuthorship'])
    return HttpResponse(json.dumps({'data': result.to_json(), 'genus': genus, 'family': family, 'autor': autor}),
                        content_type="application/json")


def update_genus_family(request, id):
    genus = Genus.objects.get(id=id)
    if request.method == 'POST':
        form = GenusForm(request.POST, instance=genus)
        if form.is_valid():
            new_genus = form.save()
            binnacle = Binnacle(type_update="Actualización", model="Genero",
                                description="Se actualiza Familia de genero " + new_genus.name + " en " + str(
                                    new_genus.family), created_by=request.user)
            binnacle.save()
            vouchers = VoucherImported.objects.filter(occurrenceID__voucher_state=7,
                                                      scientificName__genus__id=new_genus.id)
            for voucher in vouchers:
                generate_etiquete(voucher.id)
            CatalogView.refresh_view()
            SynonymyView.refresh_view()
            RegionDistributionView.refresh_view()
            return redirect('list_genus')
    else:
        form = GenusForm(instance=genus)

    return render(request, 'catalog/update_genus_family.html', {'form': form, 'id': id})


@login_required
def list_taxa(request):
    return render(request, 'catalog/list_taxa.html')


@login_required
def taxa_table(request):
    sort_by_func = {
        0: 'division',
        1: 'class_name',
        2: 'order',
        3: 'family',
        4: 'scientificNameFull',
        5: 'created_by',
        6: 'created_at',
        7: 'updated_at',
        8: 'status',
        9: 'determined'
    }
    search_value = request.GET.get('search[value]', None)
    return __catalog_table__(
        request, CatalogView, CatalogViewSerializer,
        sort_by_func, "species",
        add_searchable=(
            Q(division__icontains=search_value) |
            Q(class_name__icontains=search_value) |
            Q(order__icontains=search_value) |
            Q(family__icontains=search_value) |
            Q(status__icontains=search_value) |
            Q(determined__icontains=search_value)
        )
    )


def create_taxa(request):
    if request.method == 'POST':
        form = SpeciesForm(request.POST)
        html_instructions = ""
        if form.is_valid():
            try:
                specie = form.save()
                genus = str(specie.genus).capitalize()
                specificEpithet = str(specie.specificEpithet)
                scientificName = genus + specificEpithet
                scientificNameFull = genus + specificEpithet
                scientificNameAuthorship = str(specie.scientificNameAuthorship)
                subespecie = str(specie.subespecie)
                autoresSsp = str(specie.autoresSsp)
                variedad = str(specie.variedad)
                autoresVariedad = str(specie.autoresVariedad)
                forma = str(specie.forma)
                autoresForma = str(specie.autoresForma)
                if specie.scientificNameAuthorship != None:
                    scientificNameFull += " " + scientificNameAuthorship
                if specie.subespecie != None:
                    scientificName += " subsp. " + subespecie
                if specie.autoresSsp != None:
                    scientificNameFull += " subsp. " + subespecie + " " + autoresSsp
                if specie.variedad != None:
                    scientificName += " var. " + variedad
                if specie.autoresVariedad != None:
                    scientificNameFull += " var. " + variedad + " " + autoresVariedad
                if specie.forma != None:
                    scientificName += " fma. " + forma
                if specie.autoresForma != None:
                    scientificNameFull += " fma. " + forma + " " + autoresForma
                specie.scientificName = scientificName
                specie.scientificNameFull = scientificNameFull
                specie.scientificNameDB = scientificName.upper()
                specie.id_taxa = specie.id
                specie.save()
                CatalogView.refresh_view()
                SynonymyView.refresh_view()
                RegionDistributionView.refresh_view()
                binnacle = Binnacle(type_update="Nuevo", model="Especie",
                                    description="Se crea Especie " + specie.scientificName, created_by=request.user)
                binnacle.save()
                return redirect('list_taxa')
            except Exception as e:
                print(e)
                pass
    else:
        form = SpeciesForm()
    return render(request, 'catalog/create_taxa.html', {'form': form})


def update_taxa(request, specie_id):
    species = Species.objects.get(id=specie_id)
    warnings = list()
    if species.galleryimage_set.exists():
        warnings.append("gallery")
    if species.voucherimported_set.exists():
        warnings.append("voucher")
    if species.synonymys.exists():
        warnings.append("synonymy")
    genus_preview = species.genus
    specificEpithet_preview = species.specificEpithet
    scientificNameAuthorship_preview = species.scientificNameAuthorship
    subespecie_preview = species.subespecie
    autoresSsp_preview = species.autoresSsp
    variedad_preview = species.variedad
    autoresVariedad_preview = species.autoresVariedad
    forma_preview = species.forma
    autoresForma_preview = species.autoresForma
    scientificName_preview = species.scientificName
    scientificNameDB_preview = species.scientificNameDB
    scientificNameFull_preview = species.scientificNameFull
    form = SpeciesForm(instance=species)
    if request.method == "POST":
        form = SpeciesForm(request.POST, instance=species)
        if form.is_valid():
            try:
                specie = form.save()
                genus = str(specie.genus).capitalize()
                specificEpithet = str(specie.specificEpithet)
                scientificName = genus + specificEpithet
                scientificNameFull = genus + specificEpithet
                scientificNameAuthorship = str(specie.scientificNameAuthorship)
                subespecie = str(specie.subespecie)
                autoresSsp = str(specie.autoresSsp)
                variedad = str(specie.variedad)
                autoresVariedad = str(specie.autoresVariedad)
                forma = str(specie.forma)
                autoresForma = str(specie.autoresForma)
                if specie.scientificNameAuthorship != None:
                    scientificNameFull += " " + scientificNameAuthorship
                if specie.subespecie != None:
                    scientificName += " subsp. " + subespecie
                if specie.autoresSsp != None:
                    scientificNameFull += " subsp. " + subespecie + " " + autoresSsp
                if specie.variedad != None:
                    scientificName += " var. " + variedad
                if specie.autoresVariedad != None:
                    scientificNameFull += " var. " + variedad + " " + autoresVariedad
                if specie.forma != None:
                    scientificName += " fma. " + forma
                if specie.autoresForma != None:
                    scientificNameFull += " fma. " + forma + " " + autoresForma
                if (specie.genus != genus_preview
                        or specie.specificEpithet != specificEpithet_preview
                        or specie.scientificNameAuthorship != scientificNameAuthorship_preview
                        or specie.subespecie != subespecie_preview
                        or specie.autoresSsp != autoresSsp_preview
                        or specie.variedad != variedad_preview
                        or specie.autoresVariedad != autoresVariedad_preview
                        or specie.forma != forma_preview
                        or specie.autoresForma != autoresForma_preview):
                    new_synonymy = Synonymy(
                        scientificName=scientificName_preview,
                        scientificNameDB=scientificNameDB_preview,
                        scientificNameFull=scientificNameFull_preview,
                        genus=genus_preview,
                        specificEpithet=specificEpithet_preview,
                        scientificNameAuthorship=scientificNameAuthorship_preview,
                        subespecie=subespecie_preview,
                        autoresSsp=autoresSsp_preview,
                        variedad=variedad_preview,
                        autoresVariedad=autoresVariedad_preview,
                        forma=forma_preview,
                        autoresForma=autoresForma_preview
                    )
                    new_synonymy.save()
                    specie.synonymys.add(new_synonymy)
                specie.scientificName = scientificName
                specie.scientificNameFull = scientificNameFull
                specie.scientificNameDB = scientificName.upper()
                specie.save()
                vouchers = VoucherImported.objects.filter(occurrenceID__voucher_state=7, scientificName__id=specie.id)
                for voucher in vouchers:
                    generate_etiquete(voucher.id)
                CatalogView.refresh_view()
                SynonymyView.refresh_view()
                RegionDistributionView.refresh_view()
                binnacle = Binnacle(type_update="Actualización", model="Especie",
                                    description="Se actualiza Especie " + specie.scientificName,
                                    created_by=request.user)
                binnacle.save()
                return redirect('list_taxa')
            except Exception as e:
                logging.error(e, exc_info=True)
                pass
    return render(request, 'catalog/update_taxa.html', {
        'form': form,
        'specie_id': specie_id,
        'species_name': species.scientificNameFull,
        'warnings': warnings
    })


def delete_taxa(request, species_id):
    species = Species.objects.get(id=species_id)
    name = species.scientificNameFull
    try:
        logging.info("Taxa to be deleted {}:{}".format(
            species_id, name
        ))
        species.delete()
        binnacle = Binnacle(
            type_update="Eliminación", model="Taxón",
            description="Se elimina Taxón {}".format(name),
            created_by=request.user
        )
        binnacle.save()
        CatalogView.refresh_view()
        SynonymyView.refresh_view()
        RegionDistributionView.refresh_view()
    except Exception as e:
        logging.error("Error deleting species {}:{}".format(
            species_id, name
        ))
        logging.error(e, exc_info=True)
    return redirect('list_taxa')


@login_required
def merge_taxa(request, id):
    taxa_1 = Species.objects.get(id=id)
    species = Species.objects.all()
    form = SpeciesForm(instance=taxa_1)
    if request.method == "POST":
        form = SpeciesForm(request.POST)
        if form.is_valid():
            try:
                if request.POST['id_taxon_2'] == '':
                    errors = form._errors.setdefault("id_taxa", ErrorList())
                    errors.append(u"Debe seleccionar taxón para unir")
                    return render(request, 'catalog/merge_taxa.html',
                                  {'form': form, 'taxa_1': taxa_1, 'id_taxon_1': id, 'species': species})
                else:
                    taxon_1 = Species.objects.get(id=id)
                    taxon_1_genus_preview = taxon_1.genus
                    taxon_1_specificEpithet_preview = taxon_1.specificEpithet
                    taxon_1_scientificNameAuthorship_preview = taxon_1.scientificNameAuthorship
                    taxon_1_subespecie_preview = taxon_1.subespecie
                    taxon_1_autoresSsp_preview = taxon_1.autoresSsp
                    taxon_1_variedad_preview = taxon_1.variedad
                    taxon_1_autoresVariedad_preview = taxon_1.autoresVariedad
                    taxon_1_forma_preview = taxon_1.forma
                    taxon_1_autoresForma_preview = taxon_1.autoresForma
                    taxon_1_scientificName_preview = taxon_1.scientificName
                    taxon_1_scientificNameDB_preview = taxon_1.scientificNameDB
                    taxon_1_scientificNameFull_preview = taxon_1.scientificNameFull

                    taxon_2_id = request.POST['id_taxon_2']
                    taxon_2 = Species.objects.get(id=taxon_2_id)
                    taxon_2_genus_preview = taxon_2.genus
                    taxon_2_specificEpithet_preview = taxon_2.specificEpithet
                    taxon_2_scientificNameAuthorship_preview = taxon_2.scientificNameAuthorship
                    taxon_2_subespecie_preview = taxon_2.subespecie
                    taxon_2_autoresSsp_preview = taxon_2.autoresSsp
                    taxon_2_variedad_preview = taxon_2.variedad
                    taxon_2_autoresVariedad_preview = taxon_2.autoresVariedad
                    taxon_2_forma_preview = taxon_2.forma
                    taxon_2_autoresForma_preview = taxon_2.autoresForma
                    taxon_2_scientificName_preview = taxon_2.scientificName
                    taxon_2_scientificNameDB_preview = taxon_2.scientificNameDB
                    taxon_2_scientificNameFull_preview = taxon_2.scientificNameFull

                    specie = form.save(commit=False)
                    genus = str(specie.genus).capitalize()
                    specificEpithet = str(specie.specificEpithet)
                    scientificName = genus + specificEpithet
                    scientificNameFull = genus + specificEpithet
                    scientificNameAuthorship = str(specie.scientificNameAuthorship)
                    subespecie = str(specie.subespecie)
                    autoresSsp = str(specie.autoresSsp)
                    variedad = str(specie.variedad)
                    autoresVariedad = str(specie.autoresVariedad)
                    forma = str(specie.forma)
                    autoresForma = str(specie.autoresForma)
                    if specie.scientificNameAuthorship != None:
                        scientificNameFull += " " + scientificNameAuthorship
                    if specie.subespecie != None:
                        scientificName += " subsp. " + subespecie
                    if specie.autoresSsp != None:
                        scientificNameFull += " subsp. " + subespecie + " " + autoresSsp
                    if specie.variedad != None:
                        scientificName += " var. " + variedad
                    if specie.autoresVariedad != None:
                        scientificNameFull += " var. " + variedad + " " + autoresVariedad
                    if specie.forma != None:
                        scientificName += " fma. " + forma
                    if specie.autoresForma != None:
                        scientificNameFull += " fma. " + forma + " " + autoresForma

                    specie_new = Species(
                        id_taxa=specie.id_taxa,
                        genus=specie.genus,
                        scientificName=scientificName,
                        scientificNameDB=scientificName.upper(),
                        scientificNameFull=scientificNameFull,
                        specificEpithet=specie.specificEpithet,
                        scientificNameAuthorship=specie.scientificNameAuthorship,
                        subespecie=specie.subespecie,
                        autoresSsp=specie.autoresSsp,
                        variedad=specie.variedad,
                        autoresVariedad=specie.autoresVariedad,
                        forma=specie.forma,
                        autoresForma=specie.autoresForma,
                        enArgentina=specie.enArgentina,
                        enBolivia=specie.enBolivia,
                        enPeru=specie.enPeru,
                        status=specie.status,
                        alturaMinima=specie.alturaMinima,
                        alturaMaxima=specie.alturaMaxima,
                        notas=specie.notas,
                        id_tipo=specie.id_tipo,
                        publicacion=specie.publicacion,
                        volumen=specie.volumen,
                        paginas=specie.paginas,
                        anio=specie.anio,
                        determined=True
                    )

                    specie_new.save()

                    common_names = request.POST.getlist('common_names')
                    for common_name in common_names:
                        specie_new.common_names.add(CommonName.objects.get(id=common_name))

                    synonymys = request.POST.getlist('synonymys')
                    for synonymy in synonymys:
                        specie_new.synonymys.add(Synonymy.objects.get(id=synonymy))

                    region = request.POST.getlist('region')
                    for region in region:
                        specie_new.region.add(Region.objects.get(id=region))

                    plant_habit = request.POST.getlist('plant_habit')
                    for habit in plant_habit:
                        specie_new.plant_habit.add(PlantHabit.objects.get(id=habit))

                    env_habit = request.POST.getlist('env_habit')
                    for habit in env_habit:
                        specie_new.env_habit.add(EnvironmentalHabit.objects.get(id=habit))

                    cycles = request.POST.getlist('cycle')
                    for cycle in cycles:
                        specie_new.cycle.add(Cycle.objects.get(id=cycle))

                    new_synonymy = Synonymy(
                        scientificName=taxon_1_scientificName_preview,
                        scientificNameDB=taxon_1_scientificNameDB_preview,
                        scientificNameFull=taxon_1_scientificNameFull_preview,
                        genus=taxon_1_genus_preview,
                        specificEpithet=taxon_1_specificEpithet_preview,
                        scientificNameAuthorship=taxon_1_scientificNameAuthorship_preview,
                        subespecie=taxon_1_subespecie_preview,
                        autoresSsp=taxon_1_autoresSsp_preview,
                        variedad=taxon_1_variedad_preview,
                        autoresVariedad=taxon_1_autoresVariedad_preview,
                        forma=taxon_1_forma_preview,
                        autoresForma=taxon_1_autoresForma_preview
                    )
                    new_synonymy.save()
                    specie_new.synonymys.add(new_synonymy)

                    new_synonymy = Synonymy(
                        scientificName=taxon_2_scientificName_preview,
                        scientificNameDB=taxon_2_scientificNameDB_preview,
                        scientificNameFull=taxon_2_scientificNameFull_preview,
                        genus=taxon_2_genus_preview,
                        specificEpithet=taxon_2_specificEpithet_preview,
                        scientificNameAuthorship=taxon_2_scientificNameAuthorship_preview,
                        subespecie=taxon_2_subespecie_preview,
                        autoresSsp=taxon_2_autoresSsp_preview,
                        variedad=taxon_2_variedad_preview,
                        autoresVariedad=taxon_2_autoresVariedad_preview,
                        forma=taxon_2_forma_preview,
                        autoresForma=taxon_2_autoresForma_preview
                    )
                    new_synonymy.save()
                    specie_new.synonymys.add(new_synonymy)

                    specie_new.save()

                    VoucherImported.objects.filter(scientificName=taxon_1.id).update(scientificName=specie_new.id)
                    VoucherImported.objects.filter(scientificName=taxon_2.id).update(scientificName=specie_new.id)

                    binnacle = Binnacle(
                        type_update="Mezcla",
                        model="Especie",
                        description="Se mezclan Especies " + taxon_1.scientificName + " y " + taxon_2.scientificName + " en " + specie_new.scientificName,
                        created_by=request.user
                    )
                    binnacle.save()

                    taxon_1.delete()
                    taxon_2.delete()

                    vouchers = VoucherImported.objects.filter(occurrenceID__voucher_state=7,
                                                              scientificName__id=specie_new.id)
                    for voucher in vouchers:
                        generate_etiquete(voucher.id)

                    CatalogView.refresh_view()
                    SynonymyView.refresh_view()
                    RegionDistributionView.refresh_view()
                    return redirect('list_taxa')

            except Exception as e:
                print(e)
                pass

    return render(request, 'catalog/merge_taxa.html',
                  {'form': form, 'taxa_1': taxa_1, 'id_taxon_1': id, 'species': species})


@login_required
def split_1_taxa(request, specie_id):
    taxa_1 = Species.objects.get(id=specie_id)
    form_taxa_1 = SpeciesForm(instance=taxa_1)
    if request.method == "POST":
        form_taxa_1 = SpeciesForm(request.POST)
        if form_taxa_1.is_valid():
            specie_1 = form_taxa_1.save(commit=False)

            new_synonymy = Synonymy.objects.create(
                scientificName=taxa_1.scientificName,
                scientificNameDB=taxa_1.scientificNameDB,
                scientificNameFull=taxa_1.scientificNameFull,
                genus=taxa_1.genus,
                specificEpithet=taxa_1.specificEpithet,
                scientificNameAuthorship=taxa_1.scientificNameAuthorship,
                subespecie=taxa_1.subespecie,
                autoresSsp=taxa_1.autoresSsp,
                variedad=taxa_1.variedad,
                autoresVariedad=taxa_1.autoresVariedad,
                forma=taxa_1.forma,
                autoresForma=taxa_1.autoresForma,
                created_at=taxa_1.created_at,
                created_by=taxa_1.created_by
            )

            logging.info("New synonym (id: {}) created from species `{}`".format(
                new_synonymy.id,
                taxa_1.scientificName,
            ))

            genus = str(specie_1.genus).capitalize()
            specificEpithet = str(specie_1.specificEpithet)
            scientificName = genus + specificEpithet
            scientificNameFull = genus + specificEpithet
            scientificNameAuthorship = str(specie_1.scientificNameAuthorship)
            subespecie = str(specie_1.subespecie)
            autoresSsp = str(specie_1.autoresSsp)
            variedad = str(specie_1.variedad)
            autoresVariedad = str(specie_1.autoresVariedad)
            forma = str(specie_1.forma)
            autoresForma = str(specie_1.autoresForma)
            if specie_1.scientificNameAuthorship != None:
                scientificNameFull += " " + scientificNameAuthorship
            if specie_1.subespecie != None:
                scientificName += " subsp. " + subespecie
            if specie_1.autoresSsp != None:
                scientificNameFull += " subsp. " + subespecie + " " + autoresSsp
            if specie_1.variedad != None:
                scientificName += " var. " + variedad
            if specie_1.autoresVariedad != None:
                scientificNameFull += " var. " + variedad + " " + autoresVariedad
            if specie_1.forma != None:
                scientificName += " fma. " + forma
            if specie_1.autoresForma != None:
                scientificNameFull += " fma. " + forma + " " + autoresForma

            taxa_1.genus = specie_1.genus
            taxa_1.scientificName = scientificName
            taxa_1.scientificNameDB = scientificName.upper()
            taxa_1.scientificNameFull = scientificNameFull
            taxa_1.specificEpithet = specie_1.specificEpithet
            taxa_1.scientificNameAuthorship = specie_1.scientificNameAuthorship
            taxa_1.subespecie = specie_1.subespecie
            taxa_1.autoresSsp = specie_1.autoresSsp
            taxa_1.variedad = specie_1.variedad
            taxa_1.autoresVariedad = specie_1.autoresVariedad
            taxa_1.forma = specie_1.forma
            taxa_1.autoresForma = specie_1.autoresForma
            taxa_1.status = specie_1.status
            taxa_1.enArgentina = specie_1.enArgentina
            taxa_1.enBolivia = specie_1.enBolivia
            taxa_1.enPeru = specie_1.enPeru
            taxa_1.status = specie_1.status
            taxa_1.alturaMinima = specie_1.alturaMinima
            taxa_1.alturaMaxima = specie_1.alturaMaxima
            taxa_1.notas = specie_1.notas
            taxa_1.id_tipo = specie_1.id_tipo
            taxa_1.publicacion = specie_1.publicacion
            taxa_1.volumen = specie_1.volumen
            taxa_1.paginas = specie_1.paginas
            taxa_1.anio = specie_1.anio
            taxa_1.determined = specie_1.determined

            plant_habit = request.POST.getlist('plant_habit')
            for habit in plant_habit:
                taxa_1.plant_habit.add(PlantHabit.objects.get(id=habit))

            env_habit = request.POST.getlist('env_habit')
            for habit in env_habit:
                taxa_1.env_habit.add(EnvironmentalHabit.objects.get(id=habit))

            cycles = request.POST.getlist('cycle')
            for cycle in cycles:
                taxa_1.cycle.add(Cycle.objects.get(id=cycle))

            common_names = request.POST.getlist('common_names')
            for common_name in common_names:
                taxa_1.common_names.add(CommonName.objects.get(id=common_name))

            synonymys = request.POST.getlist('synonymys')
            for synonymy in synonymys:
                taxa_1.synonymys.add(Synonymy.objects.get(id=synonymy))
            taxa_1.synonymys.add(new_synonymy)

            region = request.POST.getlist('region')
            for region in region:
                taxa_1.region.add(Region.objects.get(id=region))

            taxa_1.save()
            logging.info("Species `{}` updated to `{}`".format(
                taxa_1.id,
                taxa_1.scientificName
            ))

            binnacle = Binnacle(
                type_update="División 1",
                model="Especie",
                description="Se divide en una nueva Especie {} en {}".format(
                    new_synonymy.scientificName,
                    taxa_1.scientificName
                ),
                created_by=request.user
            )
            binnacle.save()

            vouchers = VoucherImported.objects.filter(occurrenceID__voucher_state=7, scientificName__id=taxa_1.id)
            logging.info("Updating name on images")
            update_voucher_name.delay([voucher.id for voucher in vouchers])

            CatalogView.refresh_view()
            SynonymyView.refresh_view()
            RegionDistributionView.refresh_view()

            return redirect('list_taxa')

    return render(request, 'catalog/split_1_taxa.html',
                  {'form_taxa_1': form_taxa_1, 'taxa_1': taxa_1, 'id_taxon_1': specie_id})


@login_required
def split_2_taxa(request, id):
    taxa_1 = Species.objects.get(id=id)
    form_taxa_1 = SpeciesForm(instance=taxa_1, prefix='form_taxa_1')
    form_taxa_2 = SpeciesForm(instance=taxa_1, prefix='form_taxa_2')
    if request.method == "POST":
        form_taxa_1 = SpeciesForm(request.POST, prefix='form_taxa_1')
        form_taxa_2 = SpeciesForm(request.POST, prefix='form_taxa_2')
        if form_taxa_1.is_valid() and form_taxa_2.is_valid():
            specie_1 = form_taxa_1.save(commit=False)
            specie_2 = form_taxa_2.save(commit=False)

            genus = str(specie_1.genus).capitalize()
            specificEpithet = str(specie_1.specificEpithet)
            scientificName = genus + specificEpithet
            scientificNameFull = genus + specificEpithet
            scientificNameAuthorship = str(specie_1.scientificNameAuthorship)
            subespecie = str(specie_1.subespecie)
            autoresSsp = str(specie_1.autoresSsp)
            variedad = str(specie_1.variedad)
            autoresVariedad = str(specie_1.autoresVariedad)
            forma = str(specie_1.forma)
            autoresForma = str(specie_1.autoresForma)
            if specie_1.scientificNameAuthorship != None:
                scientificNameFull += " " + scientificNameAuthorship
            if specie_1.subespecie != None:
                scientificName += " subsp. " + subespecie
            if specie_1.autoresSsp != None:
                scientificNameFull += " subsp. " + subespecie + " " + autoresSsp
            if specie_1.variedad != None:
                scientificName += " var. " + variedad
            if specie_1.autoresVariedad != None:
                scientificNameFull += " var. " + variedad + " " + autoresVariedad
            if specie_1.forma != None:
                scientificName += " fma. " + forma
            if specie_1.autoresForma != None:
                scientificNameFull += " fma. " + forma + " " + autoresForma

            specie_new_1 = Species(
                id_taxa=specie_1.id_taxa,
                genus=specie_1.genus,
                scientificName=scientificName,
                scientificNameDB=scientificName.upper(),
                scientificNameFull=scientificNameFull,
                specificEpithet=specie_1.specificEpithet,
                scientificNameAuthorship=specie_1.scientificNameAuthorship,
                subespecie=specie_1.subespecie,
                autoresSsp=specie_1.autoresSsp,
                variedad=specie_1.variedad,
                autoresVariedad=specie_1.autoresVariedad,
                forma=specie_1.forma,
                autoresForma=specie_1.autoresForma,
                enArgentina=specie_1.enArgentina,
                enBolivia=specie_1.enBolivia,
                enPeru=specie_1.enPeru,
                habit=specie_1.habit,
                ciclo=specie_1.ciclo,
                status=specie_1.status,
                alturaMinima=specie_1.alturaMinima,
                alturaMaxima=specie_1.alturaMaxima,
                notas=specie_1.notas,
                id_tipo=specie_1.id_tipo,
                publicacion=specie_1.publicacion,
                volumen=specie_1.volumen,
                paginas=specie_1.paginas,
                anio=specie_1.anio,
                determined=True
            )

            specie_new_1.save()

            common_names = request.POST.getlist('form_taxa_1-common_names')
            for common_name in common_names:
                specie_new_1.common_names.add(CommonName.objects.get(id=common_name))

            synonymys = request.POST.getlist('form_taxa_1-synonymys')
            for synonymy in synonymys:
                specie_new_1.synonymys.add(Synonymy.objects.get(id=synonymy))

            region = request.POST.getlist('form_taxa_1-region')
            for region in region:
                specie_new_1.region.add(Region.objects.get(id=region))

            taxon_1 = Species.objects.get(id=id)
            taxon_1_genus_preview = taxon_1.genus
            taxon_1_specificEpithet_preview = taxon_1.specificEpithet
            taxon_1_scientificNameAuthorship_preview = taxon_1.scientificNameAuthorship
            taxon_1_subespecie_preview = taxon_1.subespecie
            taxon_1_autoresSsp_preview = taxon_1.autoresSsp
            taxon_1_variedad_preview = taxon_1.variedad
            taxon_1_autoresVariedad_preview = taxon_1.autoresVariedad
            taxon_1_forma_preview = taxon_1.forma
            taxon_1_autoresForma_preview = taxon_1.autoresForma
            taxon_1_scientificName_preview = taxon_1.scientificName
            taxon_1_scientificNameDB_preview = taxon_1.scientificNameDB
            taxon_1_scientificNameFull_preview = taxon_1.scientificNameFull

            new_synonymy = Synonymy(
                scientificName=taxon_1_scientificName_preview,
                scientificNameDB=taxon_1_scientificNameDB_preview,
                scientificNameFull=taxon_1_scientificNameFull_preview,
                genus=taxon_1_genus_preview,
                specificEpithet=taxon_1_specificEpithet_preview,
                scientificNameAuthorship=taxon_1_scientificNameAuthorship_preview,
                subespecie=taxon_1_subespecie_preview,
                autoresSsp=taxon_1_autoresSsp_preview,
                variedad=taxon_1_variedad_preview,
                autoresVariedad=taxon_1_autoresVariedad_preview,
                forma=taxon_1_forma_preview,
                autoresForma=taxon_1_autoresForma_preview
            )
            new_synonymy.save()
            specie_new_1.synonymys.add(new_synonymy)
            specie_new_1.save()

            VoucherImported.objects.filter(scientificName=taxon_1.id).update(scientificName=specie_new_1.id)

            vouchers = VoucherImported.objects.filter(occurrenceID__voucher_state=7, scientificName__id=specie_new_1.id)
            for voucher in vouchers:
                generate_etiquete(voucher.id)

            specie_2 = form_taxa_2.save(commit=False)

            genus = str(specie_2.genus).capitalize()
            specificEpithet = str(specie_2.specificEpithet)
            scientificName = genus + specificEpithet
            scientificNameFull = genus + specificEpithet
            scientificNameAuthorship = str(specie_2.scientificNameAuthorship)
            subespecie = str(specie_2.subespecie)
            autoresSsp = str(specie_2.autoresSsp)
            variedad = str(specie_2.variedad)
            autoresVariedad = str(specie_2.autoresVariedad)
            forma = str(specie_2.forma)
            autoresForma = str(specie_2.autoresForma)
            if specie_2.scientificNameAuthorship != None:
                scientificNameFull += " " + scientificNameAuthorship
            if specie_2.subespecie != None:
                scientificName += " subsp. " + subespecie
            if specie_2.autoresSsp != None:
                scientificNameFull += " subsp. " + subespecie + " " + autoresSsp
            if specie_2.variedad != None:
                scientificName += " var. " + variedad
            if specie_2.autoresVariedad != None:
                scientificNameFull += " var. " + variedad + " " + autoresVariedad
            if specie_2.forma != None:
                scientificName += " fma. " + forma
            if specie_2.autoresForma != None:
                scientificNameFull += " fma. " + forma + " " + autoresForma

            specie_new_2 = Species(
                id_taxa=specie_2.id_taxa,
                genus=specie_2.genus,
                scientificName=scientificName,
                scientificNameDB=scientificName.upper(),
                scientificNameFull=scientificNameFull,
                specificEpithet=specie_2.specificEpithet,
                scientificNameAuthorship=specie_2.scientificNameAuthorship,
                subespecie=specie_2.subespecie,
                autoresSsp=specie_2.autoresSsp,
                variedad=specie_2.variedad,
                autoresVariedad=specie_2.autoresVariedad,
                forma=specie_2.forma,
                autoresForma=specie_2.autoresForma,
                enArgentina=specie_2.enArgentina,
                enBolivia=specie_2.enBolivia,
                enPeru=specie_2.enPeru,
                habit=specie_2.habit,
                ciclo=specie_2.ciclo,
                status=specie_2.status,
                alturaMinima=specie_2.alturaMinima,
                alturaMaxima=specie_2.alturaMaxima,
                notas=specie_2.notas,
                id_tipo=specie_2.id_tipo,
                publicacion=specie_2.publicacion,
                volumen=specie_2.volumen,
                paginas=specie_2.paginas,
                anio=specie_2.anio,
                determined=True
            )

            specie_new_2.save()

            common_names = request.POST.getlist('form_taxa_2-common_names')
            for common_name in common_names:
                specie_new_2.common_names.add(CommonName.objects.get(id=common_name))

            synonymys = request.POST.getlist('form_taxa_2-synonymys')
            for synonymy in synonymys:
                specie_new_2.synonymys.add(Synonymy.objects.get(id=synonymy))

            region = request.POST.getlist('form_taxa_2-region')
            for region in region:
                specie_new_2.region.add(Region.objects.get(id=region))

            specie_new_2.synonymys.add(new_synonymy)
            specie_new_2.save()

            binnacle = Binnacle(
                type_update="División 2",
                model="Especie",
                description="Se divide en dos nuevas Especies " + taxon_1.scientificName + " en " + specie_new_1.scientificName + " y " + specie_new_2.scientificName,
                created_by=request.user
            )
            binnacle.save()

            taxon_1.delete()

            CatalogView.refresh_view()
            SynonymyView.refresh_view()
            RegionDistributionView.refresh_view()

            return redirect('list_taxa')

    return render(request, 'catalog/split_2_taxa.html',
                  {'form_taxa_1': form_taxa_1, 'form_taxa_2': form_taxa_2, 'taxa_1': taxa_1, 'id_taxon_1': id})


@login_required
def get_taxa(request, id):
    taxa = Species.objects.get(id=id)
    data = serializers.serialize('json', [taxa, ])
    json_data = json.loads(data)
    json_data[0]['fields']['id'] = id
    json_data[0]['fields']['genus_name'] = taxa.genus.name
    json_data[0]['fields']['status_name'] = taxa.status.name
    common_names = ''
    common_names_id = []
    for common_name in taxa.common_names.all():
        common_names += str(common_name) + ', '
        common_names_id.append(common_name.id)
    json_data[0]['fields']['common_names'] = common_names
    json_data[0]['fields']['common_names_2'] = common_names_id
    synonymys = ''
    synonymys_id = []
    for synonymy in taxa.synonymys.all():
        synonymys += str(synonymy) + ', '
        synonymys_id.append(synonymy.id)
    json_data[0]['fields']['synonymys'] = synonymys
    json_data[0]['fields']['synonymys_2'] = synonymys_id
    plant_habit = ''
    plant_habit_id = []
    for habit in taxa.plant_habit.all():
        plant_habit += str(habit) + ', '
        plant_habit_id.append(habit.id)
    json_data[0]['fields']['plant_habit'] = plant_habit
    json_data[0]['fields']['plant_habit_2'] = plant_habit_id
    env_habit = ''
    env_habit_id = []
    for habit in taxa.env_habit.all():
        env_habit += str(habit) + ', '
        env_habit_id.append(habit.id)
    json_data[0]['fields']['env_habit'] = env_habit
    json_data[0]['fields']['env_habit_2'] = env_habit_id
    cycles = ''
    cycle_id = []
    for cycle in taxa.cycle.all():
        cycles += str(cycle) + ', '
        cycle_id.append(cycle.id)
    json_data[0]['fields']['cycle'] = cycles
    json_data[0]['fields']['cycle_2'] = cycle_id
    regions = ''
    region_id = []
    for region in taxa.region.all():
        regions += str(region) + ', '
        region_id.append(region.id)
    json_data[0]['fields']['region'] = regions
    json_data[0]['fields']['region_2'] = region_id
    return HttpResponse(json.dumps(json_data), content_type="application/json")


@login_required
def list_synonymy(request):
    return render(request, 'catalog/list_catalog.html', {
        'table_url': reverse('synonymy_table'),
        'rank_name': 'scientificNameFull',
        'parent_rank': 'species',
        'update_rank_url': reverse('update_synonymy', kwargs={"id": 0}),
        'rank_title': 'Sinónimos',
        'rank_name_title': 'Nombre Científico Completo',
        'parent_rank_title': 'Especie',
        'deletable': 1,
    })


@login_required
def synonymy_table(request):
    sort_by_func = {
        0: 'scientificNameFull',
        1: 'species__scientificName',
        2: 'created_by__username',
        3: 'created_at',
        4: 'updated_at',
    }
    return __catalog_table__(
        request, Synonymy, SynonymysSerializer,
        sort_by_func, "synonyms"
    )


def create_synonymy(request):
    if request.method == 'POST':
        form = SynonymyForm(request.POST)
        html_instructions = ""
        if form.is_valid():
            try:
                synonymy = form.save()
                genus = str(synonymy.genus).capitalize()
                specificEpithet = str(synonymy.specificEpithet)
                scientificName = genus + " " + specificEpithet
                scientificNameFull = genus + " " + specificEpithet
                scientificNameAuthorship = str(synonymy.scientificNameAuthorship)
                subespecie = str(synonymy.subespecie)
                autoresSsp = str(synonymy.autoresSsp)
                variedad = str(synonymy.variedad)
                autoresVariedad = str(synonymy.autoresVariedad)
                forma = str(synonymy.forma)
                autoresForma = str(synonymy.autoresForma)
                if synonymy.scientificNameAuthorship != None:
                    scientificNameFull += " " + scientificNameAuthorship
                if synonymy.subespecie != None:
                    scientificName += " subsp. " + subespecie
                if synonymy.autoresSsp != None:
                    scientificNameFull += " subsp. " + subespecie + " " + autoresSsp
                if synonymy.variedad != None:
                    scientificName += " var. " + variedad
                if synonymy.autoresVariedad != None:
                    scientificNameFull += " var. " + variedad + " " + autoresVariedad
                if synonymy.forma != None:
                    scientificName += " fma. " + forma
                if synonymy.autoresForma != None:
                    scientificNameFull += " fma. " + forma + " " + autoresForma
                synonymy.scientificName = scientificName
                synonymy.scientificNameFull = scientificNameFull
                synonymy.scientificNameDB = scientificName.upper()
                synonymy.save()
                SynonymyView.refresh_view()
                binnacle = Binnacle(type_update="Nuevo", model="Sinónimo",
                                    description="Se crea Sinónimo " + synonymy.scientificName, created_by=request.user)
                binnacle.save()
                return redirect('list_synonymy')
            except Exception as e:
                print(e)
                pass
    else:
        form = SynonymyForm()
    return render(request, 'catalog/create_synonymy.html', {'form': form})


def update_synonymy(request, id):
    synonymy_preview = Synonymy.objects.get(id=id)
    genus_preview = synonymy_preview.genus
    specificEpithet_preview = synonymy_preview.specificEpithet
    scientificNameAuthorship_preview = synonymy_preview.scientificNameAuthorship
    subespecie_preview = synonymy_preview.subespecie
    autoresSsp_preview = synonymy_preview.autoresSsp
    variedad_preview = synonymy_preview.variedad
    autoresVariedad_preview = synonymy_preview.autoresVariedad
    forma_preview = synonymy_preview.forma
    autoresForma_preview = synonymy_preview.autoresForma
    scientificName_preview = synonymy_preview.scientificName
    scientificNameDB_preview = synonymy_preview.scientificNameDB
    scientificNameFull_preview = synonymy_preview.scientificNameFull
    form = SynonymyForm(instance=synonymy_preview)
    if request.method == "POST":
        form = SynonymyForm(request.POST, instance=synonymy_preview)
        if form.is_valid():
            try:
                synonymy = form.save()
                genus = str(synonymy.genus).capitalize()
                specificEpithet = str(synonymy.specificEpithet)
                scientificName = genus + " " + specificEpithet
                scientificNameFull = genus + " " + specificEpithet
                scientificNameAuthorship = str(synonymy.scientificNameAuthorship)
                subespecie = str(synonymy.subespecie)
                autoresSsp = str(synonymy.autoresSsp)
                variedad = str(synonymy.variedad)
                autoresVariedad = str(synonymy.autoresVariedad)
                forma = str(synonymy.forma)
                autoresForma = str(synonymy.autoresForma)
                if synonymy.scientificNameAuthorship != None:
                    scientificNameFull += " " + scientificNameAuthorship
                if synonymy.subespecie != None:
                    scientificName += " subsp. " + subespecie
                if synonymy.autoresSsp != None:
                    scientificNameFull += " subsp. " + subespecie + " " + autoresSsp
                if synonymy.variedad != None:
                    scientificName += " var. " + variedad
                if synonymy.autoresVariedad != None:
                    scientificNameFull += " var. " + variedad + " " + autoresVariedad
                if synonymy.forma != None:
                    scientificName += " fma. " + forma
                if synonymy.autoresForma != None:
                    scientificNameFull += " fma. " + forma + " " + autoresForma
                synonymy.scientificName = scientificName
                synonymy.scientificNameFull = scientificNameFull
                synonymy.scientificNameDB = scientificName.upper()
                synonymy.save()
                SynonymyView.refresh_view()
                binnacle = Binnacle(type_update="Actualización", model="Sinónimo",
                                    description="Se actualiza Sinónimo " + synonymy.scientificName,
                                    created_by=request.user)
                binnacle.save()
                return redirect('list_synonymy')
            except Exception as e:
                print(e)
                pass
    return render(request, 'catalog/update_synonymy.html', {'form': form, 'id': id})


def delete_synonymy(request, id):
    synonymy = Synonymy.objects.get(id=id)
    try:
        binnacle = Binnacle(type_update="Eliminación", model="Sinónimo",
                            description="Se elimina Sinónimo " + synonymy.scientificName, created_by=request.user)
        binnacle.save()
        logging.info("Synonym to be deleted {}:{}".format(
            synonymy.id,
            synonymy.scientificNameFull
        ))
        synonymy.delete()
        SynonymyView.refresh_view()
    except Exception as e:
        logging.error("Error deleting synonym {}:{}".format(
            synonymy.id,
            synonymy.scientificNameFull
        ))
        logging.error(e, exc_info=True)
    return redirect('list_synonymy')


@login_required
def list_binnacle(request):
    binnacles = Binnacle.objects.all()
    return render(request, 'catalog/list_binnacle.html', {'binnacles': binnacles})


def update_binnacle(request, id):
    binnacle = Binnacle.objects.get(id=id)
    if request.method == 'POST':
        form = BinnacleForm(request.POST, instance=binnacle)
        if form.is_valid():
            form.save()
            return redirect('list_binnacle')
    else:
        form = BinnacleForm(instance=binnacle)
    return render(request, 'catalog/update_binnacle.html', {'form': form, 'id': id})


@login_required
def list_common_name(request):
    return render(request, 'catalog/list_catalog.html', {
        'table_url': reverse('common_name_table'),
        'rank_name': 'name',
        'parent_rank': 'species',
        'update_rank_url': reverse('update_common_name', kwargs={"id": 0}),
        'rank_title': 'Nombre Común',
        'rank_name_title': 'Nombre',
        'parent_rank_title': 'Especie',
        'deletable': 1,
    })


@login_required
def common_name_table(request):
    sort_by_func = {
        0: 'name',
        1: 'species__scientificName',
        2: 'created_by__username',
        3: 'created_at',
        4: 'updated_at',
    }
    return __catalog_table__(
        request, CommonName, CommonNameSerializer,
        sort_by_func, "divisions"
    )


@login_required
def create_common_name(request):
    if request.method == 'POST':
        form = CommonNameForm(request.POST)
        html_instructions = ""
        if form.is_valid():
            try:
                new_common_name = form.save()
                binnacle = Binnacle(type_update="Nuevo", model="Nombre Común",
                                    description="Se crea Nombre Común " + new_common_name.name, created_by=request.user)
                binnacle.save()
                CatalogView.refresh_view()
                SynonymyView.refresh_view()
                RegionDistributionView.refresh_view()
                return redirect('list_common_name')
            except Exception as e:
                print(e)
                pass
    else:
        form = CommonNameForm()
    return render(request, 'catalog/create_common_name.html', {'form': form})


def update_common_name(request, id):
    common_name = CommonName.objects.get(id=id)
    if request.method == 'POST':
        form = CommonNameForm(request.POST, instance=common_name)
        if form.is_valid():
            new_common_name = form.save()
            binnacle = Binnacle(type_update="Actualización", model="Nombre Común",
                                description="Se actualiza Nombre Común " + common_name.name + " en " + new_common_name.name,
                                created_by=request.user)
            binnacle.save()
            CatalogView.refresh_view()
            SynonymyView.refresh_view()
            RegionDistributionView.refresh_view()
            return redirect('list_common_name')
    else:
        form = CommonNameForm(instance=common_name)

    return render(request, 'catalog/update_common_name.html', {'form': form, 'id': id})


def delete_common_name(request, id):
    common_name = CommonName.objects.get(id=id)
    try:
        binnacle = Binnacle(type_update="Eliminación", model="Nombre Común",
                            description="Se elimina Nombre Común " + common_name.name, created_by=request.user)
        binnacle.save()
        common_name.delete()
        CatalogView.refresh_view()
    except:
        pass
    return redirect('list_common_name')
