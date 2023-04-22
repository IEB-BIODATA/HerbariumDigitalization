import json
import logging
import re
import textwrap

import pandas as pd
import tablib
from PIL import Image, ImageFont, ImageDraw
from django.contrib.auth.decorators import login_required
from django.core import serializers
from django.forms.utils import ErrorList
from django.http import HttpResponse
from django.shortcuts import render, redirect

from apps.digitalization.models import VoucherImported
from .forms import DivisionForm, ClassForm, OrderForm, FamilyForm, GenusForm, SpeciesForm, SynonymyForm, BinnacleForm, \
    CommonNameForm
from .models import Species, CatalogView, SynonymyView, RegionDistributionView, Division, Class_name, Order, Family, \
    Genus, Synonymy, Region, CommonName, Binnacle


def generate_etiquete(id):
    voucher = VoucherImported.objects.get(id=id)
    file = urllib.request.urlretrieve(voucher.image.url, voucher.occurrenceID.code.replace(':', '_') + '.jpg')
    voucher_image = Image.open(voucher.occurrenceID.code.replace(':', '_') + '.jpg')
    voucher_image_editable = ImageDraw.Draw(voucher_image)
    herbarium_code = voucher.herbarium.collection_code
    herbarium_name = voucher.herbarium.name
    scientificNameFull = voucher.scientificName.scientificNameFull
    family = voucher.scientificName.genus.family.name.title()
    catalogNumber = voucher.catalogNumber
    recordNumber = voucher.recordNumber
    recordedBy = voucher.recordedBy
    locality = voucher.locality
    identifiedBy = voucher.identifiedBy
    dateIdentified = voucher.dateIdentified
    georeferencedDate = voucher.georeferencedDate.strftime('%d-%m-%Y')
    organismRemarks = voucher.organismRemarks
    if herbarium_code == 'CONC':
        delta_x = 0
        delta_y = 230
        shape = [(2046 + delta_x, 4384 + delta_y), (3915 + delta_x, 5528 + delta_y)]
        voucher_image_editable.rectangle(shape, fill='#d7d6e0', outline="black", width=4)
        title_font = ImageFont.truetype('static/font/arial.ttf', 70)
        voucher_image_editable.text((((4000 - 2150) / 2) + 2150 + delta_x, 4530 + delta_y), herbarium_name, (0, 0, 0),
                                    anchor="ms", font=title_font, stroke_width=2, stroke_fill="black")
        number_font = ImageFont.truetype('static/font/arial.ttf', 55)
        voucher_image_editable.text((2250 + delta_x, 4660 + delta_y), herbarium_code + ' ' + str(catalogNumber),
                                    (0, 0, 0), font=number_font, stroke_width=2, stroke_fill="black")
        scientificName_font = ImageFont.truetype('static/font/arial_italic.ttf', 48)
        voucher_image_editable.text((((4000 - 2150) / 2) + 2150 + delta_x, 4810 + delta_y), scientificNameFull + ' ',
                                    (0, 0, 0), anchor="ms", font=scientificName_font)
        normal_font = ImageFont.truetype('static/font/arial.ttf', 48)
        voucher_image_editable.text((((4000 - 2150) / 2) + 2150 + delta_x, 4870 + delta_y), family, (0, 0, 0),
                                    anchor="ms", font=normal_font)

        if locality:
            voucher_image_editable.text((2250 + delta_x, 4980 + delta_y), locality, (0, 0, 0), font=normal_font)

        voucher_image_editable.text((2250 + delta_x, 5130 + delta_y), 'Fecha Col. ' + georeferencedDate, (0, 0, 0),
                                    font=normal_font)
        voucher_image_editable.text((2900 + delta_x, 5130 + delta_y), 'Leg. ' + recordedBy + ' ' + recordNumber,
                                    (0, 0, 0), font=normal_font)

        if dateIdentified:
            voucher_image_editable.text((2250 + delta_x, 5200 + delta_y), 'Fecha Det. ' + str(dateIdentified),
                                        (0, 0, 0), font=normal_font)

        if identifiedBy:
            voucher_image_editable.text((2900 + delta_x, 5200 + delta_y), 'Det. ' + str(identifiedBy), (0, 0, 0),
                                        font=normal_font)

        if organismRemarks and organismRemarks != 'nan':
            observation = textwrap.fill(str(organismRemarks), width=60, break_long_words=False)
            voucher_image_editable.text((2250 + delta_x, 5350 + delta_y), 'Obs.: ' + observation, (0, 0, 0),
                                        font=normal_font)
    else:
        shape = [(2150, 4650), (4000, 5690)]
        voucher_image_editable.rectangle(shape, fill='#d7d6e0', outline="black", width=4)
        title_font = ImageFont.truetype('static/font/arial.ttf', 70)
        voucher_image_editable.text((((4000 - 2150) / 2) + 2150, 4800), herbarium_name, (0, 0, 0), anchor="ms",
                                    font=title_font, stroke_width=2, stroke_fill="black")
        number_font = ImageFont.truetype('static/font/arial.ttf', 55)
        voucher_image_editable.text((2250, 4900), herbarium_code + ' ' + str(catalogNumber), (0, 0, 0),
                                    font=number_font, stroke_width=2, stroke_fill="black")
        scientificName_font = ImageFont.truetype('static/font/arial_italic.ttf', 48)
        voucher_image_editable.text((((4000 - 2150) / 2) + 2150, 5000), scientificNameFull, (0, 0, 0), anchor="ms",
                                    font=scientificName_font)
        normal_font = ImageFont.truetype('static/font/arial.ttf', 48)
        voucher_image_editable.text((((4000 - 2150) / 2) + 2150, 5070), family, (0, 0, 0), anchor="ms",
                                    font=normal_font)

        if locality:
            voucher_image_editable.text((2250, 5170), locality, (0, 0, 0), font=normal_font)

        voucher_image_editable.text((2250, 5270), 'Fecha Col. ' + georeferencedDate, (0, 0, 0), font=normal_font)
        voucher_image_editable.text((2900, 5270), 'Leg. ' + recordedBy + ' ' + recordNumber, (0, 0, 0),
                                    font=normal_font)

        if dateIdentified:
            voucher_image_editable.text((2250, 5340), 'Fecha Det. ' + str(dateIdentified), (0, 0, 0), font=normal_font)

        if identifiedBy:
            voucher_image_editable.text((2900, 5340), 'Det. ' + str(identifiedBy), (0, 0, 0), font=normal_font)

        if organismRemarks and organismRemarks != 'nan':
            observation = textwrap.fill(str(organismRemarks), width=60, break_long_words=False)
            voucher_image_editable.text((2250, 5440), 'Obs.: ' + observation, (0, 0, 0), font=normal_font)

    voucher_image.save(voucher_image.filename.replace(".jpg", "_public.jpg"))
    buffer = BytesIO()
    voucher_image.save(buffer, "JPEG")
    image_file = InMemoryUploadedFile(buffer, None, voucher_image.filename, 'image/jpeg', buffer.tell, None)
    voucher.image_public.save(voucher_image.filename, image_file)
    voucher.save()
    return voucher_image.filename.replace(".jpg", "_public.jpg")


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


@login_required
def list_division(request):
    division = Division.objects.all()
    return render(request, 'catalog/list_division.html', {'division': division})


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
    classes = Class_name.objects.all()
    return render(request, 'catalog/list_class.html', {'classes': classes})


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
    class_name = Class_name.objects.get(id=id)
    if request.method == 'POST':
        form = ClassForm(request.POST, instance=class_name)
        if form.is_valid():
            new_class = form.save()
            binnacle = Binnacle(type_update="Actualización", model="Clase",
                                description="Se actualiza Clase " + class_name.name + " en " + new_class.name,
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
    order = Order.objects.all()
    return render(request, 'catalog/list_order.html', {'order': order})


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
                                description="Se actualiza order " + order.name + " en " + new_order.name,
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
    family = Family.objects.all()
    return render(request, 'catalog/list_family.html', {'family': family})


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
    genus = Genus.objects.all()
    return render(request, 'catalog/list_genus.html', {'genus': genus})


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
    species = CatalogView.objects.all()
    return render(request, 'catalog/list_taxa.html', {'species': species})


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


def update_taxa(request, id):
    species = Species.objects.get(id=id)
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
    return render(request, 'catalog/update_taxa.html', {'form': form, 'id': id})


def delete_taxa(request, id):
    species = Species.objects.get(id=id)
    try:
        species.delete()
        CatalogView.refresh_view()
        SynonymyView.refresh_view()
        RegionDistributionView.refresh_view()
    except:
        pass
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
                        habit=specie.habit,
                        ciclo=specie.ciclo,
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
def split_1_taxa(request, id):
    taxa_1 = Species.objects.get(id=id)
    form_taxa_1 = SpeciesForm(instance=taxa_1)
    if request.method == "POST":
        form_taxa_1 = SpeciesForm(request.POST)
        if form_taxa_1.is_valid():
            specie_1 = form_taxa_1.save(commit=False)

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

            common_names = request.POST.getlist('common_names')
            for common_name in common_names:
                specie_new_1.common_names.add(CommonName.objects.get(id=common_name))

            synonymys = request.POST.getlist('synonymys')
            for synonymy in synonymys:
                specie_new_1.synonymys.add(Synonymy.objects.get(id=synonymy))

            region = request.POST.getlist('region')
            for region in region:
                specie_new_1.region.add(Region.objects.get(id=region))

            taxon_1 = Species.objects.get(id=id)

            specie_new_1.save()

            binnacle = Binnacle(
                type_update="División 1",
                model="Especie",
                description="Se divide en una nueva Especie " + taxon_1.scientificName + " en " + specie_new_1.scientificName,
                created_by=request.user
            )
            binnacle.save()

            VoucherImported.objects.filter(scientificName=taxon_1.id).update(scientificName=specie_new_1.id)

            vouchers = VoucherImported.objects.filter(occurrenceID__voucher_state=7, scientificName__id=specie_new_1.id)
            for voucher in vouchers:
                generate_etiquete(voucher.id)

            CatalogView.refresh_view()
            SynonymyView.refresh_view()
            RegionDistributionView.refresh_view()

            return redirect('list_taxa')

    return render(request, 'catalog/split_1_taxa.html',
                  {'form_taxa_1': form_taxa_1, 'taxa_1': taxa_1, 'id_taxon_1': id})


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
    json_data[0]['fields']['habit_name'] = taxa.habit.name
    json_data[0]['fields']['genus_name'] = taxa.genus.name
    json_data[0]['fields']['ciclo_name'] = taxa.ciclo.name
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
    region = ''
    region_id = []
    for region in taxa.region.all():
        region += str(region) + ', '
        region_id.append(region.id)
    json_data[0]['fields']['region'] = region
    json_data[0]['fields']['region_2'] = region_id
    return HttpResponse(json.dumps(json_data), content_type="application/json")


@login_required
def list_synonymy(request):
    synonymys = Synonymy.objects.all()
    return render(request, 'catalog/list_synonymy.html', {'synonymys': synonymys})


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
        synonymy.delete()
        SynonymyView.refresh_view()
    except:
        pass
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
    common_names = CommonName.objects.all()
    return render(request, 'catalog/list_common_name.html', {'common_names': common_names})


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
