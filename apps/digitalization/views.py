# -*- coding: utf-8 -*-
import csv
import glob
import hashlib
import json
import logging
import os
from datetime import datetime, date
from http import HTTPStatus
from io import BytesIO
from pathlib import Path
from typing import Tuple, Union

import numpy
import pytz
import qrcode
import tablib
from PIL import Image
from celery.result import AsyncResult
from django.contrib.auth.decorators import login_required
from django.contrib.gis.geos import GEOSGeometry
from django.core import serializers
from django.core.files import File
from django.core.files.base import ContentFile
from django.db.models import Q, Count
from django.http import HttpResponse, HttpResponseBadRequest, HttpResponseServerError, HttpResponseRedirect, \
    HttpResponseForbidden
from django.shortcuts import render, redirect
from django.template.loader import get_template
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST, require_GET
from xhtml2pdf import pisa

from apps.catalog.models import Species, CatalogView
from web.utils import paginated_table
from .forms import LoadColorProfileForm, VoucherImportedForm, GalleryImageForm, LicenceForm, PriorityVoucherForm
from .models import BiodataCode, Herbarium, GeneratedPage, VoucherImported, PriorityVouchersFile, VouchersView, \
    GalleryImage, BannerImage, VOUCHER_STATE
from .storage_backends import PrivateMediaStorage
from .tasks import process_pending_vouchers, upload_priority_vouchers
from ..api.decorators import backend_authenticated
from ..api.serializers import MinimizedVoucherSerializer, CatalogViewSerializer, GeneratedPageSerializer, \
    PriorityVouchersSerializer


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
    return render(request, 'digitalization/load_priority_vouchers_file.html', {'form': empty_form},)


@login_required
@require_GET
def priority_vouchers_table(request):
    files = PriorityVouchersFile.objects.filter(herbarium__herbariummember__user__id=request.user.id)
    sort_by_func = {0: 'herbarium__name', 1: 'created_at',
                    2: 'created_by__username', 3: 'file', }
    search_value = request.GET.get("search[value]", None)
    search_query = Q()
    if search_value:
        search_query = (
                Q(herbarium__name=search_value) |
                Q(created_at=search_value) |
                Q(created_by__username=search_value) |
                Q(file=search_value)
        )

    return paginated_table(
        request, files, PriorityVouchersSerializer,
        sort_by_func, "priority vouchers", search_query
    )


@login_required
def qr_generator(request):
    herbariums = Herbarium.objects.filter(herbariummember__user__id=request.user.id)
    generated_pages = GeneratedPage.objects.filter(herbarium__herbariummember__user__id=request.user.id).order_by('-id')
    return render(request, 'digitalization/qr_generator.html',
                  {'herbariums': herbariums, 'generated_pages': generated_pages})


def render_to_pdf(template_src, context_dict):
    template = get_template(template_src)
    html = template.render(context_dict)
    result = BytesIO()
    pdf = pisa.pisaDocument(
        src=BytesIO(html.encode('UTF-8')),
        dest=result,
        encoding='UTF-8'
    )
    if pdf.err:
        return 'We had some errors <pre>' + html + '</pre>'
    return result.getvalue()


def delete_tmp_qr():
    files = glob.glob('media/qr/*.jpg', recursive=True)
    for f in files:
        try:
            os.remove(f)
        except OSError as e:
            print("Error: %s : %s" % (f, e.strerror))


def litering_by_three(a):
    return a[0] + ' ' + a[1:4] + ' ' + a[4:7]


#  replace (↑) with you character like ","

@login_required
@require_POST
def code_generator(request):
    if request.method == 'POST':
        herbarium_input = request.POST['herbarium_input']
        logging.debug(herbarium_input)
        herbarium = Herbarium.objects.get(id=herbarium_input)
        quantity_pages_input = request.POST['quantity_pages_input']
        logging.debug("Pages required {}".format(quantity_pages_input))
        col = 5
        row = 7
        qr_per_page = col * row
        num_qrs = qr_per_page * int(quantity_pages_input)
        vouchers = VoucherImported.objects.filter(biodata_code__qr_generated=False, herbarium=herbarium).order_by(
            '-priority', 'scientific_name__genus__family__name', 'scientific_name__scientific_name', 'catalog_number'
        )
        logging.debug(vouchers)
        logging.debug(vouchers[:num_qrs])
        vouchers = vouchers[:num_qrs]
        if vouchers.count() > 0:
            generated_pages_count = GeneratedPage.objects.filter(herbarium=herbarium, terminated=False).count()
            if generated_pages_count == 0:
                generated_page = GeneratedPage(
                    name=str(quantity_pages_input) + ' páginas - ' + str(vouchers.count()) + ' códigos - Fecha:' + str(
                        datetime.now(tz=pytz.timezone('America/Santiago')).strftime('%d-%m-%Y %H:%M')),
                    herbarium=herbarium, created_by=request.user,
                    created_at=datetime.now(tz=pytz.timezone('America/Santiago')))
                generated_page.save()
                for voucher in vouchers:
                    biodata_code = voucher.biodata_code
                    biodata_code.qr_generated = True
                    biodata_code.page = generated_page
                    biodata_code.save()
                count_pages = GeneratedPage.objects.all().count()
                data = {'result': 'OK', 'pages': count_pages,
                        'generated_page': {'id': generated_page.id, 'herbarium': generated_page.herbarium.name,
                                           'Total': num_qrs, 'created_by': str(generated_page.created_by),
                                           'created_at': generated_page.created_at.strftime(
                                               '%d de %B de %Y a las %H:%M')}}
            else:
                data = {'result': 'error', 'type': 'no terminated'}
        else:
            data = {'result': 'error', 'type': 'no data'}
        return HttpResponse(json.dumps(data), content_type="application/json")


@login_required
@require_GET
def historical_page_download(request):
    if request.method == 'GET':
        historical_page_id = request.GET['historical_page_id']
        page = GeneratedPage.objects.get(pk=historical_page_id)
        col = 5
        row = 7
        qr_per_page = col * row
        qr = qrcode.QRCode(
            version=1,
            error_correction=qrcode.constants.ERROR_CORRECT_L,
            box_size=10,
            border=0,
        )
        code_list = []
        print_code_list = []
        # biodata_codes=BiodataCode.objects.filter(page=page).order_by('-catalog_number')
        vouchers = VoucherImported.objects.filter(biodata_code__page=page).order_by('priority',
                                                                                    'scientific_name__genus__family__name',
                                                                                    'scientific_name__scientific_name',
                                                                                    'catalog_number')
        for voucher in vouchers:
            code = voucher.biodata_code.code.split(':')
            print_code = code[1] + ' ' + litering_by_three(code[2])
            data_code = {'code': voucher.biodata_code.code}
            qr.add_data(data_code)
            qr.make(fit=True)
            img = qr.make_image(fill_color="black", back_color="white")
            img.save('media/qr/' + voucher.biodata_code.code + '.jpg')
            qr.clear()
            code_list.append(voucher.biodata_code.code)
            print_code_list.append(print_code)
        codes_list = zip(code_list, print_code_list)
        result = render_to_pdf('digitalization/template_qr.html',
                               {'pagesize': 'A5', 'codes_list': codes_list, 'col': col, 'page_date': page.created_at,
                                'page_id': page.id})
        delete_tmp_qr()
        return HttpResponse(result, content_type='application/pdf')


@login_required
@require_GET
def historical_priority_voucher_page_download(request):
    if request.method == 'GET':
        historical_page_id = request.GET['historical_page_id']
        page = GeneratedPage.objects.get(pk=historical_page_id)
        priority_vouchers = VoucherImported.objects.filter(biodata_code__page=page).order_by(
            'priority',
            'scientific_name__genus__family__name',
            'scientific_name__scientific_name',
            'catalog_number'
        )
        result = render_to_pdf('digitalization/template_list_priority_voucher.html',
                               {'pagesize': 'letter', 'page_date': page.created_at, 'page_id': page.id,
                                'priority_vouchers': priority_vouchers})
        return HttpResponse(result, content_type='application/pdf')


@login_required
def mark_vouchers(request):
    generated_pages = GeneratedPage.objects.filter(herbarium__herbariummember__user__id=request.user.id).order_by(
        'created_at')
    return render(request, 'digitalization/mark_vouchers.html', {'generated_pages': generated_pages})


@login_required
@require_GET
def session_table(request):
    entries = GeneratedPage.objects.filter(
        herbarium__herbariummember__user__id=request.user.id
    ).annotate(
        stateless_count_annotation=Count('biodatacode', filter=Q(biodatacode__voucher_state=0)),
        found_count_annotation=Count('biodatacode', filter=Q(biodatacode__voucher_state=1)),
        not_found_count_annotation=Count('biodatacode', filter=Q(biodatacode__voucher_state=2)),
        digitalized_annotation=Count(
            'biodatacode', filter=Q(biodatacode__voucher_state=7) | Q(biodatacode__voucher_state=8)
        )
    )
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
    search_value = request.GET.get("search[value]", None)
    if search_value:
        search_query = (
                Q(created_by__icontains=search_value) |
                Q(created_at__icontains=search_value)
        )
    return paginated_table(
        request, entries, GeneratedPageSerializer,
        sort_by_func, "generated_pages", search_query
    )


@login_required
@csrf_exempt
@require_POST
def csv_error_data(request):
    if request.method == 'POST':
        response = HttpResponse(content_type='text/csv',
                                headers={'Content-Disposition': 'attachment; filename=vouchers_error.csv'}, )
        writer = csv.writer(response)
        data_errors = json.loads(json.dumps(request.POST.dict()))
        colums = 11
        registers = int(len(data_errors) / colums)
        indexes = []
        for idx, value in enumerate(data_errors):
            if idx >= registers:
                break
            value_str = str(value)
            index = value_str[value_str.find('[') + len('['):value_str.rfind(']')]
            indexes.append(int(index))
        data_list = []
        writer.writerow(['catalog_number', 'recorded_by', 'record_number', 'scientific_name', 'locality'])
        for i in indexes:
            writer.writerow([data_errors['catalog_number[' + str(i) + ']'], data_errors['recorded_by[' + str(i) + ']'],
                             data_errors['record_number[' + str(i) + ']'],
                             data_errors['scientific_name[' + str(i) + ']'],
                             data_errors['locality[' + str(i) + ']']])
        return response


@login_required
@csrf_exempt
@require_POST
def xls_error_data(request):
    if request.method == 'POST':
        data_errors = json.loads(json.dumps(request.POST.dict()))
        data = []
        try:
            similarity = data_errors['similarity[0]']
            colums = 14
            registers = int(len(data_errors) / colums)
            indexes = []
            for idx, value in enumerate(data_errors):
                if idx >= registers:
                    break
                value_str = str(value)
                index = value_str[value_str.find('[') + len('['):value_str.rfind(']')]
                indexes.append(int(index))
            headers = ['catalog_number', 'record_number', 'recorded_by', 'other_catalog_numbers', 'locality',
                       'verbatim_elevation', 'decimal_latitude', 'decimal_longitude', 'georeference_date',
                       'scientific_name', 'similarity', 'scientific_name_similarity', 'synonymy_similarity']
            for i in indexes:
                data.append(
                    [data_errors['catalog_number[' + str(i) + ']'], data_errors['record_number[' + str(i) + ']'],
                     data_errors['recorded_by[' + str(i) + ']'],
                     data_errors['other_catalog_numbers[' + str(i) + ']'],
                     data_errors['locality[' + str(i) + ']'], data_errors['verbatim_elevation[' + str(i) + ']'],
                     data_errors['decimal_latitude[' + str(i) + ']'],
                     data_errors['decimal_longitude[' + str(i) + ']'],
                     data_errors['georeference_date[' + str(i) + ']'],
                     data_errors['scientific_name[' + str(i) + ']'], data_errors['similarity[' + str(i) + ']'],
                     data_errors['scientific_name_similarity[' + str(i) + ']'],
                     data_errors['synonymy_similarity[' + str(i) + ']']])
        except:
            colums = 11
            registers = int(len(data_errors) / colums)
            indexes = []
            for idx, value in enumerate(data_errors):
                if idx >= registers:
                    break
                value_str = str(value)
                index = value_str[value_str.find('[') + len('['):value_str.rfind(']')]
                indexes.append(int(index))
            headers = ['catalog_number', 'record_number', 'recorded_by', 'other_catalog_numbers', 'locality',
                       'verbatim_elevation', 'decimal_latitude', 'decimal_longitude', 'georeference_date',
                       'scientific_name']
            for i in indexes:
                data.append(
                    [data_errors['catalog_number[' + str(i) + ']'], data_errors['record_number[' + str(i) + ']'],
                     data_errors['recorded_by[' + str(i) + ']'],
                     data_errors['other_catalog_numbers[' + str(i) + ']'],
                     data_errors['locality[' + str(i) + ']'], data_errors['verbatim_elevation[' + str(i) + ']'],
                     data_errors['decimal_latitude[' + str(i) + ']'],
                     data_errors['decimal_longitude[' + str(i) + ']'],
                     data_errors['georeference_date[' + str(i) + ']'],
                     data_errors['scientific_name[' + str(i) + ']']])
        data = tablib.Dataset(*data, headers=headers)
        response = HttpResponse(data.xlsx, content_type='application/vnd.ms-Excel')
        response['Content-Disposition'] = "attachment; filename=vouchers_error.xlsx"
        return response


@login_required
@csrf_exempt
@require_POST
def pdf_error_data(request):
    if request.method == 'POST':
        data_errors = json.loads(json.dumps(request.POST.dict()))
        colums = 11
        registers = int(len(data_errors) / colums)
        indexes = []
        for idx, value in enumerate(data_errors):
            if idx >= registers:
                break
            value_str = str(value)
            index = value_str[value_str.find('[') + len('['):value_str.rfind(']')]
            indexes.append(int(index))
        data_list = []
        for i in indexes:
            data_list.append({'catalog_number': data_errors['catalog_number[' + str(i) + ']'],
                              'recorded_by': data_errors['recorded_by[' + str(i) + ']'],
                              'record_number': data_errors['record_number[' + str(i) + ']'],
                              'scientific_name': data_errors['scientific_name[' + str(i) + ']'],
                              'locality': data_errors['locality[' + str(i) + ']']})
        result = render_to_pdf('digitalization/template_list_priority_voucher.html',
                               {'pagesize': 'A4', 'page_date': date.today(), 'priority_vouchers': data_list})
        return HttpResponse(result, content_type='application/pdf')


@login_required
@csrf_exempt
def control_vouchers(request):
    if request.method == 'GET' and 'state_voucher' in request.GET:
        state_voucher = int(request.GET['state_voucher'])
        if state_voucher == -1:
            biodata_codes = VoucherImported.objects.filter(herbarium__herbariummember__user__id=request.user.id,
                                                           biodata_code__qr_generated=True).order_by('scientific_name',
                                                                                                     'catalog_number')
        else:
            biodata_codes = VoucherImported.objects.filter(herbarium__herbariummember__user__id=request.user.id,
                                                           biodata_code__qr_generated=True,
                                                           biodata_code__voucher_state=state_voucher).order_by(
                'scientific_name', 'catalog_number')
        data = serializers.serialize('json', biodata_codes, fields=(
            'biodata_code', 'catalog_number', 'recorded_by', 'record_number', 'scientific_name', 'locality',))
        json_data = json.loads(data)
        for index, value in enumerate(json_data):
            value['fields']['id'] = biodata_codes[index].id
            value['fields']['voucher_state_id'] = biodata_codes[index].biodata_code.voucher_state
            value['fields']['voucher_state_name'] = str(biodata_codes[index].biodata_code.get_voucher_state_display())
            value['fields']['Herbarium'] = biodata_codes[index].biodata_code.herbarium.name
            value['fields']['scientific_name'] = biodata_codes[index].scientific_name.scientific_name
            value['fields']['PageDate'] = biodata_codes[index].biodata_code.page.created_at.strftime('%d-%m-%Y %H:%M')
        return HttpResponse(json.dumps({'data': json_data}), content_type="application/json")
    vouchers = VoucherImported.objects.filter(herbarium__herbariummember__user__id=request.user.id,
                                              biodata_code__qr_generated=True, biodata_code__voucher_state=2).order_by(
        'scientific_name', 'catalog_number')
    return render(request, 'digitalization/control_vouchers.html', {'vouchers': vouchers})


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
        request, biodata_codes, MinimizedVoucherSerializer,
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
        page.terminated = True
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


@require_POST
@backend_authenticated
def upload_gallery(request):
    if request.method == 'POST':
        image = request.FILES['image']
        image_content = ContentFile(image.read())
        species, response = get_species(request.POST["scientific_name"])
        if response is not None:
            return response
        logging.debug("Uploading gallery image for {}".format(species.scientific_name))
        candid_hash = hashlib.sha256(image_content.read()).hexdigest()
        image_content.seek(0)
        prev_gallery = GalleryImage.objects.filter(scientific_name=species[0])
        for prev_image in prev_gallery:
            prev_hash = hashlib.sha256(ContentFile(prev_image.image.read()).read()).hexdigest()
            if candid_hash == prev_hash:
                return HttpResponsePreconditionFailed("Image already saved and associated with species")
        parameters = {
            "upload_at": datetime.now(),
            "scientific_name": species[0],
            "upload_by": request.user,
        }
        if "licence" in request.POST:
            parameters["licence"] = request.POST["licence"]
        if "taken_by" in request.POST:
            parameters["taken_by"] = request.POST["taken_by"]
        gallery_image = GalleryImage(**parameters)
        gallery_image.image.save(image.name, image_content)
        gallery_image.save()
        return HttpResponse(json.dumps({'result': 'ok'}), content_type="application/json")
    else:
        return HttpResponse({'result': 'error'}, status=400)


def get_species(scientific_name_full: str) -> Tuple[Union[Species, None], Union[HttpResponse, None]]:
    species = Species.objects.filter(scientific_name_full=scientific_name_full)
    if len(species) == 0:
        return None, HttpResponseBadRequest("Species not registered")
    if len(species) > 1:
        return None, HttpResponseServerError("More than one species found, check database")
    return species[0], None


@require_POST
@backend_authenticated
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
def modify_gallery_image(request):
    return render(request, 'digitalization/modify_gallery_image.html')


@login_required
def gallery_table(request):
    search_value = request.GET.get("search[value]", None)
    search_query = Q()
    if search_value:
        search_query = (
                Q(division__icontains=search_value) |
                Q(class_name__icontains=search_value) |
                Q(order__icontains=search_value) |
                Q(family__icontains=search_value) |
                Q(scientific_name_full__icontains=search_value) |
                Q(updated_at__icontains=search_value)
        )

    sort_by_func = {
        0: "division",
        1: "class_name",
        2: "order",
        3: "family",
        4: "scientific_name_full",
        5: "updated_at",
    }
    entries = CatalogView.objects.all()

    return paginated_table(
        request, entries,
        CatalogViewSerializer, sort_by_func,
        "catalog", search_query
    )


@login_required
def modify_gallery(request, species_id):
    specie = Species.objects.filter(id=species_id).first()
    gallery = GalleryImage.objects.filter(scientific_name=specie)
    return render(request, 'digitalization/modify_gallery.html', {
        'species': specie,
        'gallery': gallery,
    })


@login_required
def gallery_image(request, gallery_id):
    gallery = GalleryImage.objects.filter(id=gallery_id).first()
    catalog_id = gallery.scientific_name.id
    form = GalleryImageForm(instance=gallery)
    if request.method == "POST":
        form = GalleryImageForm(request.POST, request.FILES, instance=gallery)
        if form.is_valid():
            gallery = form.save()
            logging.debug("Gallery modified {}".format(gallery))
            return redirect('modify_gallery', catalog_id=catalog_id)
        else:
            logging.warning("Form is not valid: {}".format(form.errors))
    return render(request, 'digitalization/gallery_image.html', {
        'form': form,
        'specie': gallery.scientific_name,
        'gallery': gallery,
    })


@login_required
def new_gallery_image(request, catalog_id):
    specie = Species.objects.filter(id=catalog_id).first()
    form = GalleryImageForm(instance=None)
    form.fields["scientific_name"].initial = specie
    if request.method == "POST":
        form = GalleryImageForm(request.POST, request.FILES)
        if form.is_valid():
            form.scientific_name = specie
            gallery = form.save(commit=False)
            gallery.upload_by = request.user
            gallery.save()
            logging.debug("Added new image gallery {}".format(gallery))
            return redirect('modify_gallery', catalog_id=catalog_id)
        else:
            logging.warning("Form is not valid: {}".format(form.errors))
    return render(request, 'digitalization/gallery_image.html', {
        'form': form,
        'specie': specie,
        'gallery': None,
    })


@login_required
def delete_gallery_image(request, gallery_id):
    image = GalleryImage.objects.filter(id=gallery_id).first()
    catalog_id = image.scientific_name.id
    logging.info("Deleting {} image".format(image.image.name))
    try:
        image.image.delete()
    except Exception as e:
        logging.error("Error deleting image {}".format(image.image.url))
        logging.error(e, exc_info=True)
    logging.info("Deleting {} model".format(image))
    image.delete()
    return redirect('modify_gallery', catalog_id=catalog_id)


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


@require_GET
@login_required
def get_pending_images(request):
    if request.method == 'GET':
        voucher_pending = VoucherImported.objects.filter(~Q(image_raw=''), Q(image=''))
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
    pending_voucher = VoucherImported.objects.filter(
        Q(biodata_code__voucher_state=8) | ((~Q(image_raw='')) & Q(image=''))
    )
    return HttpResponse(json.dumps({
        "count": pending_voucher.count(),
        "vouchers": [voucher.id for voucher in pending_voucher],
    }), content_type="application/json")


@csrf_exempt
@require_POST
@login_required
def process_pending_images(request):
    task_id = process_pending_vouchers.delay(request.POST.getlist('pendingImages[]'))
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
            Q(voucher_state=1) | Q(voucher_state=7) | Q(voucher_state=8)
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


def public_point(point):
    integer = int(point)
    min_grade = point - integer
    min = min_grade * 60
    min_round = round(min) - 1
    public_point = integer + min_round / 60
    return (public_point)


def update_voucher(request, id):
    voucher = VoucherImported.objects.get(id=id)
    if request.method == 'POST':
        form = VoucherImportedForm(request.POST, instance=voucher)
        if form.is_valid():
            voucher = form.save()
            if not numpy.isnan(voucher.decimal_latitude) and not numpy.isnan(voucher.decimal_longitude):
                voucher.point = GEOSGeometry(
                    'POINT(' + str(voucher.decimal_longitude) + ' ' + str(voucher.decimal_latitude) + ')', srid=4326)
                decimal_latitude_public = public_point(voucher.decimal_latitude)
                decimal_longitude_public = public_point(voucher.decimal_longitude)
                voucher.decimal_latitude_public = decimal_latitude_public
                voucher.decimal_longitude_public = decimal_longitude_public
                voucher.point_public = GEOSGeometry(
                    'POINT(' + str(decimal_longitude_public) + ' ' + str(decimal_latitude_public) + ')', srid=4326)
                voucher.save()
                if voucher.image:
                    filename = ""  # generate_etiquette(id)
                    voucher_image = Image.open(filename)
                    path = Path(filename)
                    with path.open(mode='rb') as f:
                        voucher.image_public = File(f, name=filename)
                        voucher.save()
                    filename_60 = filename.replace(".jpg", "_resized_60.jpg")
                    voucher_image.save(filename_60, quality=50)
                    path = Path(filename_60)
                    with path.open(mode='rb') as f:
                        voucher.image_public_resized_60 = File(f, name=filename_60)
                        voucher.save()
                    filename_10 = filename.replace(".jpg", "_resized_10.jpg")
                    voucher_image.save(filename_10, quality=20)
                    path = Path(filename_10)
                    with path.open(mode='rb') as f:
                        voucher.image_public_resized_10 = File(f, name=filename_10)
                        voucher.save()
                    os.remove(filename.replace("_public.jpg", ".jpg"))
                    os.remove(filename)
                    os.remove(filename_60)
                    os.remove(filename_10)

            return redirect('control_vouchers')
    else:
        form = VoucherImportedForm(instance=voucher)

    return render(request, 'digitalization/update_voucher.html', {'form': form, 'id': id})
