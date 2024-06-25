# -*- coding: utf-8 -*-
import hashlib
import json
import logging
import os
import shutil
from datetime import datetime, date
from http import HTTPStatus
from typing import Tuple, Union, Dict

import numpy
import pytz
import qrcode
import tablib
from celery.result import AsyncResult
from django.contrib.auth.decorators import login_required
from django.contrib.gis.geos import GEOSGeometry
from django.core import serializers
from django.core.files.base import ContentFile
from django.db import transaction
from django.db.models import Q, Count, CharField, Case, When, Value
from django.db.models.functions import Cast
from django.http import HttpResponse, HttpResponseBadRequest, HttpResponseServerError, HttpResponseRedirect, \
    HttpResponseForbidden, HttpRequest, JsonResponse
from django.shortcuts import render, redirect
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST, require_GET

from apps.catalog.models import Species, CatalogView
from intranet.utils import paginated_table
from .forms import LoadColorProfileForm, VoucherImportedForm, GalleryImageForm, LicenceForm, PriorityVoucherForm, \
    GeneratedPageForm
from .models import BiodataCode, GeneratedPage, VoucherImported, PriorityVouchersFile, VouchersView, \
    GalleryImage, BannerImage, VOUCHER_STATE, PostprocessingLog
from .serializers import PriorityVouchersSerializer, GeneratedPageSerializer, VoucherSerializer, \
    SpeciesGallerySerializer, GallerySerializer, PostprocessingLogSerializer
from .storage_backends import PrivateMediaStorage
from .tasks import process_pending_vouchers, upload_priority_vouchers, etiquette_picture, get_taken_by
from .utils import render_to_pdf
from ..catalog.serializers import CatalogViewSerializer


class HttpResponsePreconditionFailed(HttpResponse):
    status_code = HTTPStatus.PRECONDITION_FAILED


@login_required
def load_priority_vouchers_file(request):
    empty_form = PriorityVoucherForm(current_user=request.user)
    if request.method == "POST":
        form = PriorityVoucherForm(request.user, request.POST, request.FILES)
        if form.is_valid():
            priority_voucher = form.save()
            priority_voucher.created_by = request.user
            priority_voucher.created_at = datetime.now(tz=pytz.timezone('America/Santiago'))
            priority_voucher.save()
            task_id = upload_priority_vouchers.delay(priority_voucher.id)
        else:
            task_id = None
            logging.error("Error uploading priority voucher by {}".format(request.user))
        return render(request, 'digitalization/load_priority_vouchers_file.html', {'form': form, 'task_id': task_id})
    return render(request, 'digitalization/load_priority_vouchers_file.html', {'form': empty_form})


@login_required
@require_GET
def priority_vouchers_table(request):
    files = PriorityVouchersFile.objects.filter(herbarium__herbariummember__user__id=request.user.id)
    sort_by_func = {0: 'herbarium__name', 1: 'created_at',
                    2: 'created_by__username', 3: 'file', }
    search_value: str = request.GET.get("search[value]", None)
    search_query = Q()
    if search_value:
        search_query = (
                Q(herbarium__name__icontains=search_value) |
                Q(created_at__icontains=search_value) |  # TODO: To search in same display format
                Q(created_by__username__icontains=search_value) |
                Q(file__icontains=search_value) |
                Q(voucherimported__biodata_code__code=search_value)
        )
        if search_value.isdigit():
            search_query = search_query | Q(voucherimported__catalog_number=int(search_value))

    return paginated_table(
        request, files, PriorityVouchersSerializer,
        sort_by_func, "priority vouchers", search_query
    )


@login_required
@csrf_exempt
@require_POST
def pdf_error_data(request):
    data_errors = json.loads(json.dumps(request.POST.dict()))
    logging.debug(f"Requesting PDF of errors: {data_errors}")
    columns = 11
    registers = int(len(data_errors) / columns)
    indexes = list()
    for idx, value in enumerate(data_errors):
        if idx >= registers:
            break
        value_str = str(value)
        index = value_str[value_str.find('[') + len('['):value_str.rfind(']')]
        indexes.append(int(index))
    data_list = list()
    for i in indexes:
        data_list.append({
            'catalog_number': data_errors['catalogNumber[' + str(i) + ']'],
            'recorded_by': data_errors['recordedBy[' + str(i) + ']'],
            'record_number': data_errors['recordNumber[' + str(i) + ']'],
            'scientific_name': data_errors['scientificName[' + str(i) + ']'],
            'locality': data_errors['locality[' + str(i) + ']']
        })
    result = render_to_pdf(
        'digitalization/template_list_priority_voucher.html',
        {
            'pagesize': 'A4',
            'page_date': date.today(),
            'priority_vouchers': data_list
        }
    )
    return HttpResponse(result, content_type='application/pdf')


@login_required
@csrf_exempt
@require_POST
def xls_error_data(request):
    data_errors = json.loads(json.dumps(request.POST.dict()))
    logging.debug(f"Requesting XLS of errors: {data_errors}")
    data = list()
    indexes = list()
    columns = 11
    headers = [
        'catalogNumber', 'recordNumber', 'recordedBy', 'otherCatalogNumbers', 'locality',
        'verbatimElevation', 'decimalLatitude', 'decimalLongitude',
        'georeferencedDate', 'scientificName',
    ]
    if any("similarity" in item for item in data_errors.keys()):
        columns = 14
        headers += ['similarity', 'scientificNameSimilarity', 'synonymySimilarity', ]
    elif any("assertion" in item for item in data_errors.keys()):
        columns = 12
        headers += ['assertion', ]
    registers = int(len(data_errors) / columns)
    for idx, value in enumerate(data_errors):
        if idx >= registers:
            break
        value_str = str(value)
        index = value_str[value_str.find('[') + len('['):value_str.rfind(']')]
        indexes.append(int(index))
    for i in indexes:
        datum = [
            data_errors['catalogNumber[' + str(i) + ']'],
            data_errors['recordNumber[' + str(i) + ']'],
            data_errors['recordedBy[' + str(i) + ']'],
            data_errors['otherCatalogNumbers[' + str(i) + ']'],
            data_errors['locality[' + str(i) + ']'],
            data_errors['verbatimElevation[' + str(i) + ']'],
            data_errors['decimalLatitude[' + str(i) + ']'],
            data_errors['decimalLongitude[' + str(i) + ']'],
            data_errors['georeferencedDate[' + str(i) + ']'],
            data_errors['scientificName[' + str(i) + ']'],
        ]
        if any("similarity" in item for item in data_errors.keys()):
            datum += [
                data_errors['similarity[' + str(i) + ']'],
                data_errors['scientificNameSimilarity[' + str(i) + ']'],
                data_errors['synonymySimilarity[' + str(i) + ']']
            ]
        elif any("assertion" in item for item in data_errors.keys()):
            datum += [
                data_errors['assertion[' + str(i) + ']'],
            ]
        data.append(datum)
    data = tablib.Dataset(*data, headers=headers)
    response = HttpResponse(data.xlsx, content_type='application/vnd.ms-Excel')
    response['Content-Disposition'] = "attachment; filename=vouchers_error.xlsx"
    return response


@login_required
def qr_generator(request):
    form = GeneratedPageForm(request.user)
    if request.method == "POST":
        info = {"state": "ok", "type": "undetermined"}
        page_form = GeneratedPageForm(request.user, request.POST)
        if page_form.is_valid():
            with transaction.atomic():
                try:
                    generated_page = page_form.save(commit=False)
                    logging.debug(f"Generating QR for {generated_page.herbarium.name}")
                    quantity_pages = request.POST['quantity_pages']
                    col = 5
                    row = 7
                    qr_per_page = col * row
                    num_qrs = qr_per_page * int(quantity_pages)
                    logging.debug(f"Pages required {quantity_pages} with {num_qrs} qr codes")
                    vouchers = VoucherImported.objects.filter(
                        biodata_code__qr_generated=False,
                        herbarium=generated_page.herbarium
                    ).order_by(
                        '-priority', 'scientific_name__genus__family__name', 'scientific_name__scientific_name',
                        'catalog_number'
                    )[:num_qrs]
                    if vouchers.count() == 0:
                        info["type"] = "no data"
                        raise ValueError("There are not vouchers left")
                    if GeneratedPage.objects.filter(
                            herbarium=generated_page.herbarium,
                            finished=False
                    ).count() != 0:
                        info["type"] = "not finished"
                        raise RuntimeError("There are sessions not finished")
                    generated_page.created_by = request.user
                    generated_page.save(quantity_pages)
                    for voucher in vouchers:
                        biodata_code = voucher.biodata_code
                        biodata_code.qr_generated = True
                        biodata_code.page = generated_page
                        biodata_code.save()
                    generated_page.save(quantity_pages)
                    logging.info(f"Created session '{generated_page.name}' ({generated_page.id}) "
                                 f"with {generated_page.qr_count} QR codes")
                except Exception as e:
                    logging.error(e, exc_info=True)
                    info["state"] = "error"
            request.session["form_data"] = info
            return redirect("qr_generator")
        else:
            form = page_form
    info = request.session.pop("form_data", None)
    return render(request, 'digitalization/qr_generator.html', {
        'form': form, "info": info
    })


@login_required
@require_GET
def session_table_qr(request):
    sort_by_func = {
        0: 'id',
        1: 'herbarium.name',
        2: 'created_by',
        3: 'created_at',
        4: 'qr_count_annotation',
        5: 'finished_annotation',
    }
    search_query = Q()
    search_value: str = request.GET.get("search[value]", None)
    if search_value:
        search_query = (
                Q(id_annotation__icontains=search_value) |
                Q(herbaium__name__icontains=search_value) |
                Q(created_at__icontains=search_value) |
                Q(created_by__username__icontains=search_value) |
                Q(finished_annotation__icontains=search_value) |
                Q(biodatacode__code=search_value)
        )
        if search_value.isdigit():
            search_query = (
                    search_query |
                    Q(qr_count_annotation=int(search_value)) |
                    Q(biodatacode__catalog_number=int(search_value))
            )
    return render_session_table(request, sort_by_func, search_query)


@login_required
@require_GET
def session_table(request):
    sort_by_func = {
        0: 'id',
        1: 'created_by',
        2: 'created_at',
        3: 'stateless_count_annotation',
        4: 'found_count_annotation',
        5: 'not_found_count_annotation',
        6: 'digitalized_annotation'
    }
    search_query = Q()
    search_value: str = request.GET.get("search[value]", None)
    if search_value:
        search_query = (
                Q(id_annotation__icontains=search_value) |
                Q(created_by__username__icontains=search_value) |
                Q(created_at__icontains=search_value) |
                Q(biodatacode__code=search_value)
        )
        if search_value.isdigit():
            search_query = search_query | Q(biodatacode__catalog_number=int(search_value))
    return render_session_table(request, sort_by_func, search_query)


def render_session_table(request: HttpRequest, sort_by_func: Dict[int, str], search_query: Q) -> HttpResponse:
    entries = GeneratedPage.objects.filter(
        herbarium__herbariummember__user__id=request.user.id
    ).annotate(
        stateless_count_annotation=Count('biodatacode', filter=Q(biodatacode__voucher_state=0)),
        found_count_annotation=Count('biodatacode', filter=Q(biodatacode__voucher_state=1)),
        not_found_count_annotation=Count('biodatacode', filter=Q(biodatacode__voucher_state=2)),
        digitalized_annotation=Count(
            'biodatacode', filter=Q(biodatacode__voucher_state=7) | Q(biodatacode__voucher_state=8)
        ),
        qr_count_annotation=Count('biodatacode', filter=Q(biodatacode__qr_generated=True)),
        finished_annotation=Case(
            When(finished=True, then=Value("Sí")),
            default=Value("No"),
            output_field=CharField(),
        ),
        id_annotation=Cast('id', CharField())
    )
    return paginated_table(
        request, entries, GeneratedPageSerializer,
        sort_by_func, "generated pages", search_query
    )


@login_required
@require_GET
def priority_vouchers_page_download(request: HttpRequest, page_id: int):
    page = GeneratedPage.objects.get(pk=page_id)
    priority_vouchers = VoucherImported.objects.filter(
        biodata_code__page=page
    ).order_by(
        'priority',
        'scientific_name__genus__family__name',
        'scientific_name__scientific_name',
        'catalog_number'
    )
    result = render_to_pdf(
        'digitalization/template_list_priority_voucher.html', {
            'pagesize': 'letter',
            'page_date': page.created_at,
            'page_id': page.id,
            'priority_vouchers': priority_vouchers
        }
    )
    return HttpResponse(result, content_type='application/pdf')


@login_required
@require_GET
def qr_page_download(request: HttpRequest, page_id: int):
    os.makedirs(os.path.join("tmp", "qr"), exist_ok=True)

    def delete_tmp_qr():
        try:
            shutil.rmtree(os.path.join("tmp", "qr"))
        except OSError as e:
            logging.error(f"Error deleting qr temp folder: {e}", exc_info=True)

    page = GeneratedPage.objects.get(pk=page_id)
    col = 5
    row = 7
    qr = qrcode.QRCode(
        version=1,
        error_correction=qrcode.constants.ERROR_CORRECT_L,
        box_size=10,
        border=0,
    )
    code_list = []
    print_code_list = []
    vouchers = VoucherImported.objects.filter(
        biodata_code__page=page
    ).order_by(
        'priority',
        'scientific_name__genus__family__name',
        'scientific_name__scientific_name',
        'catalog_number'
    )

    for voucher in vouchers:
        code = voucher.biodata_code.code.split(':')
        listing_by_three = (lambda a: f"{a[0]} {a[1:4]} {a[4:7]}")(code[2])
        print_code = f"{code[1]} {listing_by_three}"
        data_code = voucher.biodata_code.code.replace(":", "_")
        qr.add_data({'code': voucher.biodata_code.code})
        qr.make(fit=True)
        img = qr.make_image(fill_color="black", back_color="white")
        temp_file = os.path.join("tmp", "qr", f"{data_code}.jpg")
        logging.debug(f"Writing temporal file `{temp_file}`")
        img.save(temp_file)
        qr.clear()
        code_list.append(data_code)
        print_code_list.append(print_code)
    codes_list = zip(code_list, print_code_list)
    result = render_to_pdf(
        'digitalization/template_qr.html', {
            'pagesize': 'A5',
            'codes_list': codes_list,
            'col': col,
            'row': row,
            'page_date': page.created_at,
            'page_id': page.id
        }
    )
    delete_tmp_qr()
    return HttpResponse(result, content_type='application/pdf')


@login_required
def mark_vouchers(request):
    generated_pages = GeneratedPage.objects.filter(herbarium__herbariummember__user__id=request.user.id).order_by(
        'created_at')
    return render(request, 'digitalization/mark_vouchers.html', {'generated_pages': generated_pages})


@login_required
@require_GET
def control_vouchers(request):
    voucher_state = int(request.GET.get('voucher_state', 2))
    state_name = "All"
    for voucher, name in VOUCHER_STATE:
        if voucher == voucher_state:
            state_name = name
            break
    return render(request, 'digitalization/control_vouchers.html', {
        'voucher_state': voucher_state,
        'state_name': state_name,
    })


@login_required
@require_GET
def vouchers_table(request, voucher_state: str):
    voucher_state = int(voucher_state)
    voucher_filter = (
            Q(herbarium__herbariummember__user=request.user) &
            Q(biodata_code__qr_generated=True)
    )
    if voucher_state != -1:
        voucher_filter = voucher_filter & Q(biodata_code__voucher_state=voucher_state)
    entries = VoucherImported.objects.filter(voucher_filter).order_by(
        'scientific_name__scientific_name', 'catalog_number',
    )
    sort_by_func = {
        1: 'biodata_code__page__created_at',
        2: 'herbarium__name',
        3: 'biodata_code__code',
        4: 'catalog_number',
        5: 'scientific_name__scientific_name',
        6: 'recorded_by',
        7: 'record_number',
        8: 'locality',
    }
    search_query = Q()
    search_value: str = request.GET.get("search[value]", None)
    if search_value:
        search_query = (
                Q(biodata_code__page__created_at__icontains=search_value) |
                Q(herbarium__name__icontains=search_value) |
                Q(biodata_code__code__icontains=search_value) |
                Q(catalog_number__icontains=search_value) |
                Q(scientific_name__scientific_name__icontains=search_value) |
                Q(recorded_by__icontains=search_value) |
                Q(record_number__icontains=search_value) |
                Q(locality__icontains=search_value)
        )
    return paginated_table(
        request, entries, VoucherSerializer,
        sort_by_func, "voucher imported", search_query
    )


@login_required
def get_vouchers_to_validate(request, page_id, voucher_state):
    page = GeneratedPage.objects.get(id=int(page_id))
    filters = (
            Q(herbarium__herbariummember__user__id=request.user.id) &
            Q(biodata_code__page=page)
    )
    if int(voucher_state) != -1:
        filters &= Q(biodata_code__voucher_state=int(voucher_state))
    biodata_codes = VoucherImported.objects.filter(filters)
    search_query = Q()
    search_value = request.GET.get("search[value]", None)
    if search_value:
        search_query = (
                Q(catalog_number__icontains=search_value) |
                Q(scientific_name__scientific_name__icontains=search_value) |
                Q(recorded_by__icontains=search_value) |
                Q(record_number__icontains=search_value) |
                Q(locality__icontains=search_value)
        )

    sort_by_func = {
        1: "catalog_number",
        2: "scientific_name__scientific_name",
        3: "recorded_by",
        4: "record_number",
        5: "locality",
    }
    return paginated_table(
        request, biodata_codes, VoucherSerializer,
        sort_by_func, "biodata code", search_query
    )


@login_required
@require_POST
def upload_color_profile_file(request):
    form = LoadColorProfileForm(request.POST, request.FILES)
    if form.is_valid():
        try:
            form.created_by = request.user
            form.created_at = datetime.now(tz=pytz.timezone('America/Santiago'))
            color_profile = form.save()
            generated_page_id = request.POST['generated_page_id']
            page = GeneratedPage.objects.get(pk=generated_page_id)
            if page.color_profile:
                page.color_profile.delete()
            page.color_profile = color_profile
            page.save()
            data = {'result': 'OK', 'url': color_profile.file.url}
        except Exception as e:
            logging.error("Error on uploading profile color")
            logging.error(e, exc_info=True)
            data = {'result': 'error', 'detail': str(e)}
    else:
        data = {'result': 'error'}
    return HttpResponse(json.dumps(data), content_type="application/json")


@login_required
@csrf_exempt
@require_POST
def set_state(request):
    if 'voucher_state' not in request.POST or 'biodata_code' not in request.POST:
        return HttpResponseBadRequest()
    voucher_state = int(request.POST['voucher_state'])
    biodata_codes = BiodataCode.objects.get(pk=request.POST['biodata_code'])
    display = -1
    for state, display in VOUCHER_STATE:
        if state == voucher_state:
            logging.debug(f"Setting {biodata_codes.code} ({biodata_codes.id}) to {display} ({voucher_state})")
            break
    if voucher_state in [7, 8]:
        logging.warning(f"'{display}' ({voucher_state}) is used just by system")
        return HttpResponseForbidden()
    try:
        biodata_codes.voucher_state = voucher_state
        data = {'result': 'OK'}
        if voucher_state == 0:
            biodata_codes.qr_generated = False
        else:
            biodata_codes.qr_generated = True
        biodata_codes.save()
    except Exception as e:
        data = {'result': 'Error', 'detail': str(e)}
        logging.error("Error setting voucher state")
        logging.error(e, exc_info=True)
    return HttpResponse(json.dumps(data), content_type="application/json")


@login_required
@csrf_exempt
@require_POST
def mark_all_page_as(request):
    if 'voucher_state' not in request.POST or 'generated_page_id' not in request.POST:
        return HttpResponseBadRequest()
    voucher_state = int(request.POST['voucher_state'])
    generated_page = GeneratedPage.objects.get(pk=request.POST['generated_page_id'])
    biodata_codes = BiodataCode.objects.filter(page=generated_page)
    display = -1
    for state, display in VOUCHER_STATE:
        if state == voucher_state:
            logging.debug(f"Setting {biodata_codes.count()} (Page {generated_page.pk}) to {display} ({voucher_state})")
            break
    if voucher_state in [7, 8]:
        logging.warning(f"'{display}' ({voucher_state}) is used just by system")
        return HttpResponseForbidden()
    data = dict()
    for bc in biodata_codes:
        try:
            bc.voucher_state = voucher_state
            data[bc.pk] = {'result': 'OK'}
            if voucher_state == 0:
                bc.qr_generated = False
            else:
                bc.qr_generated = True
            bc.save()
        except Exception as e:
            data[bc.pk] = {'result': 'Error', 'detail': str(e)}
            logging.error(f"Error setting voucher state on {bc.pk}")
            logging.error(e, exc_info=True)
    return HttpResponse(json.dumps(data), content_type="application/json")


@login_required
@require_POST
@csrf_exempt
def terminate_session(request):
    try:
        page_id = request.POST['page_id']
        page = GeneratedPage.objects.get(pk=page_id)
        codes = BiodataCode.objects.filter(voucher_state=0, page=page)
        for code in codes:
            code.qr_generated = False
            code.page = None
            code.save()
        page.finished = True
        page.save()
        data = {'result': 'OK'}
    except Exception as e:
        logging.error("Error terminating session")
        logging.error(e, exc_info=True)
        data = {'result': 'error', 'detail': str(e)}
    return HttpResponse(json.dumps(data), content_type="application/json")


@login_required
def validate_vouchers(request):
    generated_pages = GeneratedPage.objects.filter(herbarium__herbariummember__user__id=request.user.id).order_by(
        '-created_at')
    return render(request, 'digitalization/validate_vouchers.html', {'generated_pages': generated_pages})


def get_species(scientific_name_full: str) -> Tuple[Union[Species, None], Union[HttpResponse, None]]:
    species = Species.objects.filter(scientific_name_full=scientific_name_full)
    if len(species) == 0:
        return None, HttpResponseBadRequest("Species not registered")
    if len(species) > 1:
        return None, HttpResponseServerError("More than one species found, check database")
    return species[0], None


@require_POST
def upload_banner(request):
    if request.method == "POST":
        banner = request.FILES['image']
        banner_content = ContentFile(banner.read())
        species, response = get_species(request.POST["scientific_name"])
        if response is not None:
            return response
        logging.debug("Uploading banner for {}".format(species.scientific_name))
        vouchers = VoucherImported.objects.filter(id=request.POST["voucher"])
        if vouchers.count() == 0:
            return HttpResponse({'info': 'No voucher found'}, status=400)
        try:
            banner_image = BannerImage(specie_id=species, image=vouchers.first())
            banner_image.banner.save(banner.name, banner_content)
            banner_image.save()
        except Exception as e:
            logging.error(e, exc_info=True)
            return HttpResponse({'info': e}, status=500)
        return HttpResponse({'result': 'ok'}, content_type="application/json")
    else:
        return HttpResponse({'result': 'error'}, status=400)


@login_required
def gallery_images(request):
    return render(request, 'digitalization/gallery_images.html')


@login_required
@require_GET
def gallery_table(request):
    search_value = request.GET.get("search[value]", None)
    search_query = Q()
    if search_value:
        search_query = (
                Q(division__name__icontains=search_value) |
                Q(class_name__name__icontains=search_value) |
                Q(order__name__icontains=search_value) |
                Q(family__name__icontains=search_value) |
                Q(scientific_name_full__icontains=search_value) |
                Q(updated_at__icontains=search_value)
        )

    sort_by_func = {
        0: "division__name",
        1: "class_name__name",
        2: "order__name",
        3: "family__name",
        4: "scientific_name_full",
        5: "gallery_images_annotation",
        6: "updated_at",
    }
    entries = Species.objects.all().annotate(
        gallery_images_annotation=Count('galleryimage')
    )

    return paginated_table(
        request, entries,
        SpeciesGallerySerializer, sort_by_func,
        "species", search_query
    )


@login_required
def species_gallery(request, species_id: int):
    species = Species.objects.get(pk=species_id)
    gallery = GalleryImage.objects.filter(scientific_name=species)
    return render(request, 'digitalization/species_gallery.html', {
        'species': species,
        'gallery': [GallerySerializer(image).data for image in gallery],
    })


@login_required
def new_gallery_image(request, species_id: int) -> HttpResponse:
    species = Species.objects.get(pk=species_id)
    form = GalleryImageForm(instance=None)
    if request.method == "POST":
        form = GalleryImageForm(request.POST, request.FILES)
        if form.is_valid():
            gallery = form.save(commit=False)
            gallery.upload_by = request.user
            gallery.scientific_name = species
            gallery.save()
            gallery.generate_thumbnail()
            logging.debug("Added new image gallery {}".format(gallery))
            return redirect('species_gallery', species_id=species_id)
        else:
            logging.warning("Form is not valid: {}".format(form.errors), exc_info=True)
    return render(request, 'digitalization/gallery_image.html', {
        'form': form,
        'species': species,
    })


@login_required
def modify_gallery_image(request, gallery_id):
    gallery = GalleryImage.objects.get(pk=gallery_id)
    species = gallery.scientific_name
    form = GalleryImageForm(instance=gallery)
    if request.method == "POST":
        form = GalleryImageForm(request.POST, request.FILES, instance=gallery)
        if form.is_valid():
            gallery = form.save()
            gallery.generate_thumbnail()
            logging.debug("Gallery modified {}".format(gallery))
            return redirect('species_gallery', species_id=species.id)
        else:
            logging.warning("Form is not valid: {}".format(form.errors), exc_info=True)
    return render(request, 'digitalization/gallery_image.html', {
        'form': form,
        'species': species,
        'gallery': gallery,
    })


@login_required
def delete_gallery_image(request, gallery_id: int) -> HttpResponse:
    image = GalleryImage.objects.get(pk=gallery_id)
    species = image.scientific_name.id
    logging.info("Deleting {} image".format(image.image.name))
    try:
        image.image.delete()
    except Exception as e:
        logging.error("Error deleting image {}".format(image.image.url))
        logging.error(e, exc_info=True)
    logging.info("Deleting {} model".format(image))
    image.delete()
    return redirect('species_gallery', species_id=species)


@login_required
def new_licence(request):
    form = LicenceForm(instance=None)
    prev_page = request.headers["Referer"]
    if request.method == "POST":
        prev_page = request.POST['next']
        form = LicenceForm(request.POST)
        if form.is_valid():
            licence = form.save(commit=False)
            licence.added_by = request.user
            licence.save()
            logging.info("New licence saved: {}".format(licence))
            return HttpResponseRedirect(prev_page)
    return render(request, "digitalization/new_licence.html", {
        "prev_page": prev_page,
        "form": form,
    })


@login_required
@require_POST
@csrf_exempt
def upload_raw_image(request):
    if request.method == 'POST':
        voucher_id = request.POST['voucher_id']
        logging.debug(voucher_id)
        image = request.FILES['image']
        voucher_imported = VoucherImported.objects.get(pk=voucher_id)
        try:
            voucher_imported.upload_raw_image(image)
            data = {'result': 'ok', 'file_url': voucher_imported.image_raw.url}
        except Exception as e:
            logging.warning("Voucher {} could not save".format(voucher_id))
            logging.warning(e, exc_info=True)
    else:
        return HttpResponseBadRequest("Wrong Http Method")
    return HttpResponse(json.dumps(data), content_type="application/json")


@login_required
def upload_temporal_image(request) -> HttpResponse:
    try:
        temporal_image = request.FILES["image"]
        image_content = ContentFile(temporal_image.read())
        private_storage = PrivateMediaStorage()
        saved_temporal = private_storage.save(f"temporal/{temporal_image.name}", image_content)
        return JsonResponse({
            "temporal_image": saved_temporal,
            "image_url": private_storage.url(saved_temporal),
        })
    except Exception as e:
        logging.error(f"Error uploading temporal file: {e}", exc_info=True)
        return HttpResponseServerError()


@require_GET
@login_required
def extract_taken_by(request: HttpRequest, image_file: str) -> HttpResponse:
    task_id = get_taken_by.delay(f"temporal/{image_file}")
    return HttpResponse(task_id)


@require_GET
@login_required
def get_pending_images(request):
    if request.method == 'GET':
        voucher_pending = VoucherImported.objects.filter(
            (~Q(image_raw='') & Q(image='')) | Q(biodata_code__voucher_state=8)
        )
        data = serializers.serialize('json', voucher_pending, fields=('image_raw',))
        json_data = json.loads(data)
        for index, value in enumerate(json_data):
            value['fields']['code_voucher'] = voucher_pending[index].biodata_code.code
            value['fields']['image_raw'] = voucher_pending[index].image_raw.url
            value['fields']['herbarium_code'] = voucher_pending[index].herbarium.collection_code
            value['fields']['date'] = voucher_pending[index].biodata_code.created_at.strftime('%d_%m_%Y')
        return HttpResponse(json.dumps(json_data), content_type="application/json")


@require_GET
@login_required
def get_pending_vouchers(request):
    pending_voucher = VoucherImported.objects.filter(biodata_code__voucher_state=8)
    return HttpResponse(json.dumps({
        "count": pending_voucher.count(),
        "vouchers": [voucher.id for voucher in pending_voucher],
    }), content_type="application/json")


@csrf_exempt
@require_POST
@login_required
def process_pending_images(request):
    task_id = process_pending_vouchers.delay(
        request.POST.getlist('pendingImages[]'),
        request.user.id
    )
    return HttpResponse(task_id)


@require_GET
@login_required
def get_progress(request, task_id: str):
    result = AsyncResult(task_id)
    return HttpResponse(json.dumps({
        'state': result.state,
        'details': result.info,
    }), content_type="application/json")


@require_GET
@login_required
def get_task_log(request, task_id: str):
    return HttpResponse(PrivateMediaStorage().url(f"{task_id}.log"))


@login_required
@require_GET
def vouchers_download(request):
    if request.method == 'GET':
        logging.debug("Refreshing vouchers")
        VouchersView.refresh_view()
        logging.info("Generating voucher excel...")
        headers = [
            'id', 'file', 'code', 'voucher_state', 'collection_code',
            'other_catalog_numbers', 'catalog_number',
            'recorded_by', 'record_number', 'organism_remarks',
            'scientific_name', 'locality', 'verbatim_elevation',
            'decimal_latitude', 'decimal_longitude',
            'identified_by', 'identified_date',
            'decimal_latitude_public', 'decimal_longitude_public',
            'priority',
        ]
        logging.debug("Filtering voucher according to state")
        species = VouchersView.objects.values_list(*headers).filter(
            Q(voucher_state=1) | Q(voucher_state=3) | Q(voucher_state=4) | Q(voucher_state=7) | Q(voucher_state=8)
        ).order_by('id')
        databook = tablib.Databook()
        data_set = tablib.Dataset(*species, headers=headers, title='Vouchers')
        databook.add_sheet(data_set)
        response = HttpResponse(databook.xlsx, content_type='application/vnd.ms-Excel')
        response['Content-Disposition'] = "attachment; filename=vochers.xlsx"
        logging.info("Voucher excel sent")
        return response


@login_required
def download_catalog(request):
    if request.method == 'GET':
        logging.info("Generating catalog excel...")
        headers = [
            'id', 'id taxa',
            'Family', 'Genus', 'Species',
            'Scientific Name', 'Scientific Name Full',
            'Scientific Name DB', 'Determined'
        ]
        species = Species.objects.values_list(
            'id', 'id_taxa', 'genus__family__name', 'genus__name',
            'specific_epithet', 'scientific_name',
            'scientific_name_full', 'scientific_name_db', 'determined'
        ).order_by('id')
        databook = tablib.Databook()
        data_set = tablib.Dataset(*species, headers=headers, title='Catalog')
        databook.add_sheet(data_set)
        response = HttpResponse(databook.xlsx, content_type='application/vnd.ms-Excel')
        response['Content-Disposition'] = "attachment; filename=vochers.xlsx"
        logging.info("Catalog excel sent")
        return response


@login_required
def update_voucher(request, voucher_id):
    voucher = VoucherImported.objects.get(id=voucher_id)
    if request.method == 'POST':
        form = VoucherImportedForm(request.POST, instance=voucher)
        if form.is_valid():
            voucher = form.save()
            if not numpy.isnan(voucher.decimal_latitude) and not numpy.isnan(voucher.decimal_longitude):
                voucher.point = GEOSGeometry(
                    'POINT(' + str(voucher.decimal_longitude) + ' ' + str(voucher.decimal_latitude) + ')', srid=4326)
                decimal_latitude_public = VoucherImported.public_point(voucher.decimal_latitude)
                decimal_longitude_public = VoucherImported.public_point(voucher.decimal_longitude)
                voucher.decimal_latitude_public = decimal_latitude_public
                voucher.decimal_longitude_public = decimal_longitude_public
                voucher.point_public = GEOSGeometry(
                    'POINT(' + str(decimal_longitude_public) + ' ' + str(decimal_latitude_public) + ')', srid=4326)
                voucher.save()
                if voucher.image and voucher.biodata_code.voucher_state == 7:
                    etiquette_picture.delay(int(voucher.pk))
            return redirect('control_vouchers')
    else:
        form = VoucherImportedForm(instance=voucher)

    return render(request, 'digitalization/update_voucher.html', {'form': form, 'id': voucher_id})


@login_required
def postprocessing_log(request) -> HttpResponse:
    return render(request, 'digitalization/postprocessing_log.html')


@login_required
def postprocessing_log_table(request) -> JsonResponse:
    sort_by_func = {
        0: "date",
        1: "file",
        2: "found_images",
        3: "processed_images",
        4: "failed_images",
        5: "scheduled",
        6: "created_by__username",
    }
    search_query = Q()
    search_value = request.GET.get("search[value]", None)
    if search_value:
        search_query = (
            Q(file__icontainse=search_value) |
            Q(created_by__username__icontains=search_value)
        )
    entries = PostprocessingLog.objects.all()
    return paginated_table(
        request, entries, PostprocessingLogSerializer,
        sort_by_func, "Postprocessing Log", search_query
    )
