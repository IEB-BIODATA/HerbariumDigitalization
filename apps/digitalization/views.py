# -*- coding: utf-8 -*-
import csv
import glob
import hashlib
import json
import logging
import os
import subprocess
import textwrap
import urllib.request
from datetime import datetime, date
from http import HTTPStatus
from io import BytesIO
from pathlib import Path
from typing import Tuple, Union
import numpy
import pytz
import qrcode
import tablib
from PIL import Image, ImageFont, ImageDraw
from django.contrib.auth.decorators import login_required
from django.contrib.gis.geos import GEOSGeometry
from django.core import serializers
from django.core.files import File
from django.core.files.base import ContentFile
from django.core.files.uploadedfile import InMemoryUploadedFile
from django.core.paginator import Paginator
from django.db.models import Q
from django.http import HttpResponse, HttpResponseBadRequest, HttpResponseServerError, HttpResponseRedirect, \
    JsonResponse
from django.shortcuts import render, redirect
from django.template.loader import get_template
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST, require_GET
from rest_framework.request import Request
from xhtml2pdf import pisa

from apps.catalog.models import Species, CatalogView
from .forms import LoadPriorityVoucherForm, LoadColorProfileForm, VoucherImportedForm, GalleryImageForm, LicenceForm
from .models import BiodataCode, Herbarium, GeneratedPage, VoucherImported, PriorityVouchersFile, VouchersView, \
    GalleryImage, BannerImage
from .vouchers import PriorityVouchers
from ..api.decorators import backend_authenticated
from ..api.serializers import MinimizedVoucherSerializer


class HttpResponsePreconditionFailed(HttpResponse):
    status_code = HTTPStatus.PRECONDITION_FAILED


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
        herbarium = Herbarium.objects.get(id=herbarium_input)
        quantity_pages_input = request.POST['quantity_pages_input']
        col = 5
        row = 7
        qr_per_page = col * row
        num_qrs = qr_per_page * int(quantity_pages_input)
        vouchers = VoucherImported.objects.filter(occurrenceID__qr_generated=False, herbarium=herbarium).order_by(
            '-priority', 'scientificName__genus__family__name', 'scientificName__scientificName', 'catalogNumber')[
                   :num_qrs]
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
                    biodata_code = voucher.occurrenceID
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
        # biodata_codes=BiodataCode.objects.filter(page=page).order_by('-catalogNumber')
        vouchers = VoucherImported.objects.filter(occurrenceID__page=page).order_by('priority',
                                                                                    'scientificName__genus__family__name',
                                                                                    'scientificName__scientificName',
                                                                                    'catalogNumber')
        for voucher in vouchers:
            code = voucher.occurrenceID.code.split(':')
            print_code = code[1] + ' ' + litering_by_three(code[2])
            data_code = {'code': voucher.occurrenceID.code}
            qr.add_data(data_code)
            qr.make(fit=True)
            img = qr.make_image(fill_color="black", back_color="white")
            img.save('media/qr/' + voucher.occurrenceID.code + '.jpg')
            qr.clear()
            code_list.append(voucher.occurrenceID.code)
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
        priority_vouchers = VoucherImported.objects.filter(occurrenceID__page=page).order_by('priority',
                                                                                             'scientificName__genus__family__name',
                                                                                             'scientificName__scientificName',
                                                                                             'catalogNumber')
        result = render_to_pdf('digitalization/template_list_priority_voucher.html',
                               {'pagesize': 'letter', 'page_date': page.created_at, 'page_id': page.id,
                                'priority_vouchers': priority_vouchers})
        return HttpResponse(result, content_type='application/pdf')


@login_required
def load_priority_vouchers_file(request):
    files = PriorityVouchersFile.objects.filter(herbarium__herbariummember__user__id=request.user.id).order_by(
        'created_at')
    form = LoadPriorityVoucherForm(current_user=request.user)
    return render(request, 'digitalization/load_priority_vouchers_file.html', {'form': form, 'files': files})


def load_vouchers(file_vouchers, user):
    priority_vouchers = PriorityVouchers(file_vouchers, user)
    response = priority_vouchers.import_to_db()
    return {'response': response}


@login_required
@require_POST
def upload_priority_vouchers_file(request):
    if request.method == 'POST':
        form = LoadPriorityVoucherForm(request.user, request.POST, request.FILES)
        if form.is_valid():
            logging.info("Upload priority voucher valid")
            file_form = form.save()
            file_form.created_by = request.user
            file_form.created_at = datetime.now(tz=pytz.timezone('America/Santiago'))
            logging.info("Loading vouchers...")
            data = load_vouchers(file_form, request.user)
            if json.loads(data['response'])['result'] == 'error':
                logging.error("Error on load")
                logging.error(data['response'])
                file_form.delete()
            else:
                logging.info("Priority vouchers upload correctly")
                file_form.save()
            return HttpResponse(json.dumps(data), content_type="application/json")
        else:
            logging.error("Error uploading priority voucher by {}".format(request.user))
            logging.error(form.errors)
            return HttpResponseBadRequest(content=form.errors)


@login_required
def mark_vouchers(request):
    generated_pages = GeneratedPage.objects.filter(herbarium__herbariummember__user__id=request.user.id).order_by(
        'created_at')
    return render(request, 'digitalization/mark_vouchers.html', {'generated_pages': generated_pages})


@login_required
@csrf_exempt
@require_GET
def get_vouchers(request):
    if request.method == 'GET':
        page_id = request.GET['page_id']
        page = GeneratedPage.objects.get(pk=page_id)
        state_voucher = int(request.GET['voucher_state'])
        if state_voucher == -1:
            biodata_codes = VoucherImported.objects.filter(
                Q(occurrenceID__voucher_state=0) | Q(occurrenceID__voucher_state=1) | Q(occurrenceID__voucher_state=2),
                occurrenceID__page=page).order_by('scientificName', 'catalogNumber')
        else:
            biodata_codes = VoucherImported.objects.filter(occurrenceID__page=page,
                                                           occurrenceID__voucher_state=state_voucher).order_by(
                'scientificName__scientificName', 'catalogNumber')
        data = serializers.serialize('json', biodata_codes, fields=(
            'catalogNumber', 'recordedBy', 'recordNumber', 'scientificName', 'locality',))
        json_data = json.loads(data)
        for index, value in enumerate(json_data):
            value['fields']['voucherState'] = biodata_codes[index].occurrenceID.voucher_state
            value['fields']['scientificNameStr'] = biodata_codes[index].scientificName.scientificName
        return HttpResponse(json.dumps({'page': page.name, 'data': json_data}), content_type="application/json")


@login_required
@csrf_exempt
@require_GET
def set_state(request):
    data = {'result': 'Error'}
    if request.method == 'GET':
        pk_voucher = request.GET['pk_voucher']
        state_voucher = request.GET['state_voucher']
        voucher = VoucherImported.objects.get(pk=pk_voucher)
        biodata_codes = BiodataCode.objects.get(pk=voucher.occurrenceID.id)
        biodata_codes.voucher_state = state_voucher
        biodata_codes.save()
        data = {'result': 'OK'}
        if state_voucher == '0':
            biodata_codes.page = None
            biodata_codes.qr_generated = False
            biodata_codes.save()
    return HttpResponse(json.dumps(data), content_type="application/json")


@csrf_exempt
@require_POST
def set_digitalization_state(request):
    data = {'result': 'Error'}
    if request.method == 'POST':
        code_voucher = request.POST['code_voucher']
        state = request.POST['state']
        biodata_codes = BiodataCode.objects.filter(code=code_voucher)[0]
        biodata_codes.voucher_state = state
        biodata_codes.save()
        data = {'result': 'OK'}
    return HttpResponse(json.dumps(data), content_type="application/json")


@csrf_exempt
@require_GET
def get_digitalization_state(request):
    data = {'result': 'Error'}
    if request.method == 'GET':
        code_voucher = request.GET['code_voucher']
        biodata_codes = BiodataCode.objects.filter(code=code_voucher)[0]
        data = {'result': 'OK', 'id_page': biodata_codes.page.id,
                'date': biodata_codes.page.created_at.strftime('%d-%m-%Y'),
                'color_profile': str(biodata_codes.page.color_profile.file.url),
                'herbarium': biodata_codes.herbarium.collection_code}
    return HttpResponse(json.dumps(data), content_type="application/json")


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
        writer.writerow(['catalogNumber', 'recordedBy', 'recordNumber', 'scientificName', 'locality'])
        for i in indexes:
            writer.writerow([data_errors['catalogNumber[' + str(i) + ']'], data_errors['recordedBy[' + str(i) + ']'],
                             data_errors['recordNumber[' + str(i) + ']'], data_errors['scientificName[' + str(i) + ']'],
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
            headers = ['catalogNumber', 'recordNumber', 'recordedBy', 'otherCatalogNumbers', 'locality',
                       'verbatimElevation', 'decimalLatitude', 'decimalLongitude', 'georeferencedDate',
                       'scientificName', 'similarity', 'scientificName_similarity', 'synonymy_similarity']
            for i in indexes:
                data.append([data_errors['catalogNumber[' + str(i) + ']'], data_errors['recordNumber[' + str(i) + ']'],
                             data_errors['recordedBy[' + str(i) + ']'],
                             data_errors['otherCatalogNumbers[' + str(i) + ']'],
                             data_errors['locality[' + str(i) + ']'], data_errors['verbatimElevation[' + str(i) + ']'],
                             data_errors['decimalLatitude[' + str(i) + ']'],
                             data_errors['decimalLongitude[' + str(i) + ']'],
                             data_errors['georeferencedDate[' + str(i) + ']'],
                             data_errors['scientificName[' + str(i) + ']'], data_errors['similarity[' + str(i) + ']'],
                             data_errors['scientificName_similarity[' + str(i) + ']'],
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
            headers = ['catalogNumber', 'recordNumber', 'recordedBy', 'otherCatalogNumbers', 'locality',
                       'verbatimElevation', 'decimalLatitude', 'decimalLongitude', 'georeferencedDate',
                       'scientificName']
            for i in indexes:
                data.append([data_errors['catalogNumber[' + str(i) + ']'], data_errors['recordNumber[' + str(i) + ']'],
                             data_errors['recordedBy[' + str(i) + ']'],
                             data_errors['otherCatalogNumbers[' + str(i) + ']'],
                             data_errors['locality[' + str(i) + ']'], data_errors['verbatimElevation[' + str(i) + ']'],
                             data_errors['decimalLatitude[' + str(i) + ']'],
                             data_errors['decimalLongitude[' + str(i) + ']'],
                             data_errors['georeferencedDate[' + str(i) + ']'],
                             data_errors['scientificName[' + str(i) + ']']])
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
            data_list.append({'catalogNumber': data_errors['catalogNumber[' + str(i) + ']'],
                              'recordedBy': data_errors['recordedBy[' + str(i) + ']'],
                              'recordNumber': data_errors['recordNumber[' + str(i) + ']'],
                              'scientificName': data_errors['scientificName[' + str(i) + ']'],
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
                                                           occurrenceID__qr_generated=True).order_by('scientificName',
                                                                                                     'catalogNumber')
        else:
            biodata_codes = VoucherImported.objects.filter(herbarium__herbariummember__user__id=request.user.id,
                                                           occurrenceID__qr_generated=True,
                                                           occurrenceID__voucher_state=state_voucher).order_by(
                'scientificName', 'catalogNumber')
        data = serializers.serialize('json', biodata_codes, fields=(
            'occurrenceID', 'catalogNumber', 'recordedBy', 'recordNumber', 'scientificName', 'locality',))
        json_data = json.loads(data)
        for index, value in enumerate(json_data):
            value['fields']['id'] = biodata_codes[index].id
            value['fields']['voucherStateID'] = biodata_codes[index].occurrenceID.voucher_state
            value['fields']['voucherStateName'] = str(biodata_codes[index].occurrenceID.get_voucher_state_display())
            value['fields']['Herbarium'] = biodata_codes[index].occurrenceID.herbarium.name
            value['fields']['scientificName'] = biodata_codes[index].scientificName.scientificName
            value['fields']['PageDate'] = biodata_codes[index].occurrenceID.page.created_at.strftime('%d-%m-%Y %H:%M')
        return HttpResponse(json.dumps({'data': json_data}), content_type="application/json")
    vouchers = VoucherImported.objects.filter(herbarium__herbariummember__user__id=request.user.id,
                                              occurrenceID__qr_generated=True, occurrenceID__voucher_state=2).order_by(
        'scientificName', 'catalogNumber')
    return render(request, 'digitalization/control_vouchers.html', {'vouchers': vouchers})


@login_required
def get_vouchers_to_validate(request, page_id, voucher_state):
    logging.debug("Testing this view!")
    if request.method == 'GET':
        try:
            page = GeneratedPage.objects.get(id=int(page_id))
            filters = {
                "herbarium__herbariummember__user__id": request.user.id,
                "occurrenceID__qr_generated": True,
                "occurrenceID__page": page,
            }
            if int(voucher_state) != -1:
                filters["occurrenceID__voucher_state"] = int(voucher_state)
            biodata_codes = VoucherImported.objects.filter(
                **filters
            ).order_by('scientificName', 'catalogNumber')
            search_value = request.GET.get("search[value]", None)
            if search_value:
                logging.debug("Searching with {}".format(search_value))
            logging.debug(request.GET.__dict__)
            length = int(request.GET.get("length", 10))
            start = int(request.GET.get("start", 0))
            paginator = Paginator(biodata_codes, length)
            page_number = start // length + 1
            page_obj = paginator.get_page(page_number)

            data = MinimizedVoucherSerializer(
                page_obj,
                many=True,
                context={"request": Request(request)}
            ).data
            """
            json_data = json.loads(data)
            for index, value in enumerate(json_data):
                value['fields']['id'] = biodata_codes[index].id
                value['fields']['voucherStateID'] = biodata_codes[index].occurrenceID.voucher_state
                value['fields']['voucherStateName'] = str(biodata_codes[index].occurrenceID.get_voucher_state_display())
                value['fields']['Herbarium'] = biodata_codes[index].occurrenceID.herbarium.name
                value['fields']['PageDate'] = biodata_codes[index].occurrenceID.page.created_at.strftime('%d-%m-%Y %H:%M')
                value['fields']['scientificNameStr'] = biodata_codes[index].scientificName.scientificName
                value['fields']['image_voucher_thumb_url'] = biodata_codes[index].image_voucher_thumb_url()
                value['fields']['image_voucher_url'] = biodata_codes[index].image_voucher_url()
                value['fields']['image_voucher_jpg_raw_url'] = biodata_codes[index].image_voucher_jpg_raw_url()
                value['fields']['image_voucher_jpg_raw_url_public'] = biodata_codes[
                    index].image_voucher_jpg_raw_url_public()
                value['fields']['image_voucher_cr3_raw_url'] = biodata_codes[index].image_voucher_cr3_raw_url()
                """
            return JsonResponse({
                "draw": int(request.GET.get("draw", 0)),
                'page': page.name,
                "recordsTotal": biodata_codes.count(),
                "recordsFiltered": paginator.count,
                'data': data
            })
        except Exception as e:
            logging.error("Error getting vouchers to validate: {}".format(e), exc_info=True)
            return HttpResponseServerError()
    else:
        data = {"result": "{} HTTP Method not implemented".format(request.method)}
        return JsonResponse({'data': data})



@login_required
@require_POST
@csrf_exempt
def upload_color_profile_file(request):
    if request.method == 'POST':
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
                data = {'result': 'ok', 'url': color_profile.file.url}
            except Exception as e:
                logging.error("Error on uploading profile color")
                logging.error(e, exc_info=True)
                data = {'result': 'error'}
        else:
            data = {'result': 'error'}
        return HttpResponse(json.dumps(data), content_type="application/json")


@login_required
@require_GET
def terminate_session(request):
    if request.method == 'GET':
        try:
            page_id = request.GET['page_id']
            page = GeneratedPage.objects.get(pk=page_id)
            codes = BiodataCode.objects.filter(voucher_state=0, page=page)
            for code in codes:
                code.qr_generated = False
                code.page = None
                code.save()
            page.terminated = True
            page.save()
            data = {'result': 'ok'}
        except:
            data = {'result': 'error'}
        return HttpResponse(json.dumps(data), content_type="application/json")


@login_required
def validate_vouchers(request):
    generated_pages = GeneratedPage.objects.filter(herbarium__herbariummember__user__id=request.user.id).order_by(
        '-created_at')
    return render(request, 'digitalization/validate_vouchers.html', {'generated_pages': generated_pages})


@require_POST
@backend_authenticated
def upload_images(request):
    if request.method == 'POST':
        code_voucher = request.POST['code_voucher']
        image = request.FILES['image']
        image_resized_10 = request.FILES['image_resized_10']
        image_resized_60 = request.FILES['image_resized_60']
        image_public = request.FILES['image_public']
        image_public_resized_10 = request.FILES['image_public_resized_10']
        image_public_resized_60 = request.FILES['image_public_resized_60']
        image_raw = request.FILES['image_raw']
        image_content = ContentFile(image.read())
        image_resized_10_content = ContentFile(image_resized_10.read())
        image_resized_60_content = ContentFile(image_resized_60.read())
        image_public_content = ContentFile(image_public.read())
        image_public_resized_10_content = ContentFile(image_public_resized_10.read())
        image_public_resized_60_content = ContentFile(image_public_resized_60.read())
        image_raw_content = ContentFile(image_raw.read())
        voucher_imported = VoucherImported.objects.filter(occurrenceID__code=code_voucher)[0]
        voucher_imported.image.save(image.name, image_content)
        voucher_imported.image_resized_10.save(image_resized_10.name, image_resized_10_content)
        voucher_imported.image_resized_60.save(image_resized_60.name, image_resized_60_content)
        voucher_imported.image_public.save(image_public.name, image_public_content)
        voucher_imported.image_public_resized_10.save(image_public_resized_10.name, image_public_resized_10_content)
        voucher_imported.image_public_resized_60.save(image_public_resized_60.name, image_public_resized_60_content)
        voucher_imported.image_raw.save(image_raw.name, image_raw_content)
        voucher_imported.save()
        return HttpResponse(json.dumps({'result': 'ok'}), content_type="application/json")
    else:
        return HttpResponse({'result': 'error'}, status=400)


@require_POST
@backend_authenticated
def upload_gallery(request):
    if request.method == 'POST':
        image = request.FILES['image']
        image_content = ContentFile(image.read())
        species, response = get_species(request.POST["scientificName"])
        if response is not None:
            return response
        logging.debug("Uploading gallery image for {}".format(species.scientificName))
        candid_hash = hashlib.sha256(image_content.read()).hexdigest()
        image_content.seek(0)
        prev_gallery = GalleryImage.objects.filter(scientificName=species[0])
        for prev_image in prev_gallery:
            prev_hash = hashlib.sha256(ContentFile(prev_image.image.read()).read()).hexdigest()
            if candid_hash == prev_hash:
                return HttpResponsePreconditionFailed("Image already saved and associated with species")
        parameters = {
            "upload_at": datetime.now(),
            "scientificName": species[0],
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
    species = Species.objects.filter(scientificNameFull=scientific_name_full)
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
        species, response = get_species(request.POST["scientificName"])
        if response is not None:
            return response
        logging.debug("Uploading banner for {}".format(species.scientificName))
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
def upload_gallery_image(request):
    return render(request, 'digitalization/update_gallery.html', {'species': CatalogView.objects.all()})


@login_required
def modify_gallery(request, catalog_id):
    specie = Species.objects.filter(id=catalog_id).first()
    gallery = GalleryImage.objects.filter(scientificName=specie)
    return render(request, 'digitalization/modify_gallery.html', {
        'species': specie,
        'gallery': gallery,
    })


@login_required
def gallery_image(request, gallery_id):
    gallery = GalleryImage.objects.filter(id=gallery_id).first()
    catalog_id = gallery.scientificName.id
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
        'specie': gallery.scientificName,
        'gallery': gallery,
    })


@login_required
def new_gallery_image(request, catalog_id):
    specie = Species.objects.filter(id=catalog_id).first()
    form = GalleryImageForm(instance=None)
    form.fields["scientificName"].initial = specie
    if request.method == "POST":
        form = GalleryImageForm(request.POST, request.FILES)
        if form.is_valid():
            form.scientificName = specie
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
    catalog_id = image.scientificName.id
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


@require_GET
@csrf_exempt
def get_voucher_info(request):
    if request.method == 'GET':
        code_voucher = request.GET['code_voucher']
        voucher_imported = VoucherImported.objects.filter(occurrenceID__code=code_voucher)[0]
        herbarium_code = voucher_imported.herbarium.collection_code
        herbarium_name = voucher_imported.herbarium.name.upper()
        scientificNameFull = voucher_imported.scientificName.scientificNameFull
        family = voucher_imported.scientificName.genus.family.name.upper()
        catalogNumber = voucher_imported.occurrenceID.catalogNumber
        recordNumber = voucher_imported.recordNumber
        recordedBy = voucher_imported.recordedBy
        locality = voucher_imported.locality
        identifiedBy = voucher_imported.identifiedBy
        dateIdentified = voucher_imported.dateIdentified
        if voucher_imported.georeferencedDate:
            georeferencedDate = voucher_imported.georeferencedDate.strftime('%d-%m-%Y')
        else:
            georeferencedDate = ''
        organismRemarks = voucher_imported.organismRemarks
        data = {'code_voucher': code_voucher, 'herbarium_code': herbarium_code, 'herbarium_name': herbarium_name,
                'scientificNameFull': scientificNameFull, 'family': family, 'catalogNumber': catalogNumber,
                'recordNumber': recordNumber, 'recordedBy': recordedBy, 'locality': locality,
                'identifiedBy': identifiedBy, 'dateIdentified': dateIdentified, 'georeferencedDate': georeferencedDate,
                'organismRemarks': organismRemarks}
    else:
        data = {'result': 'error'}
    return HttpResponse(json.dumps(data), content_type="application/json")


@login_required
@require_POST
@csrf_exempt
def upload_raw_image(request):
    if request.method == 'POST':
        voucher_id = request.POST['voucher_id']
        image = request.FILES['image']
        image_content = ContentFile(image.read())
        voucher_imported = VoucherImported.objects.get(pk=voucher_id)
        voucher_imported.image_raw.save(image.name, image_content)
        data = {'result': 'ok', 'file_url': voucher_imported.image_raw.url}
        voucher_imported.save()
    else:
        data = {'result': 'error'}
    return HttpResponse(json.dumps(data), content_type="application/json")


@require_GET
@csrf_exempt
def get_pending_images(request):
    if request.method == 'GET':
        voucher_pending = VoucherImported.objects.filter(~Q(image_raw=''), Q(image=''))
        data = serializers.serialize('json', voucher_pending, fields=('image_raw',))
        json_data = json.loads(data)
        for index, value in enumerate(json_data):
            value['fields']['code_voucher'] = voucher_pending[index].occurrenceID.code
            value['fields']['image_raw'] = voucher_pending[index].image_raw.url
            value['fields']['herbarium_code'] = voucher_pending[index].herbarium.collection_code
            value['fields']['date'] = voucher_pending[index].occurrenceID.created_at.strftime('%d_%m_%Y')
        return HttpResponse(json.dumps(json_data), content_type="application/json")


@require_GET
@csrf_exempt
def process_pending_images(request):
    try:
        subprocess.call(['sudo', 'bash', '/home/ubuntu/postprocessing_pending.sh', '-p', 'True'])
        data = {'result': 'ok'}
    except:
        data = {'result': 'error'}
    return HttpResponse(json.dumps(data), content_type="application/json")


@login_required
def vouchers_download(request):
    if request.method == 'GET':
        logging.debug("Refreshing vouchers")
        VouchersView.refresh_view()
        logging.info("Generating voucher excel...")
        headers1 = ['id', 'file', 'code', 'voucher_state', 'collection_code', 'otherCatalogNumbers', 'catalogNumber',
                    'recordedBy',
                    'recordNumber', 'organismRemarks', 'scientificName', 'locality', 'verbatimElevation',
                    'decimalLatitude',
                    'decimalLongitude', 'identifiedBy', 'dateIdentified', 'decimalLatitude_public',
                    'decimalLongitude_public', 'priority']
        species = VouchersView.objects.values_list('id', 'file', 'code', 'voucher_state', 'collection_code',
                                                   'otherCatalogNumbers',
                                                   'catalogNumber', 'recordedBy', 'recordNumber', 'organismRemarks',
                                                   'scientificName', 'locality', 'verbatimElevation'
                                                   , 'decimalLatitude', 'decimalLongitude', 'identifiedBy',
                                                   'dateIdentified', 'decimalLatitude_public',
                                                   'decimalLongitude_public', 'priority').order_by('id')
        databook = tablib.Databook()
        data_set1 = tablib.Dataset(*species, headers=headers1, title='Vouchers')
        databook.add_sheet(data_set1)
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
            'specificEpithet', 'scientificName',
            'scientificNameFull', 'scientificNameDB', 'determined'
        ).order_by('id')
        databook = tablib.Databook()
        data_set = tablib.Dataset(*species, headers=headers, title='Catalog')
        databook.add_sheet(data_set)
        response = HttpResponse(databook.xlsx, content_type='application/vnd.ms-Excel')
        response['Content-Disposition'] = "attachment; filename=vochers.xlsx"
        logging.info("Catalog excel sent")
        return response


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
            if not numpy.isnan(voucher.decimalLatitude) and not numpy.isnan(voucher.decimalLongitude):
                voucher.point = GEOSGeometry(
                    'POINT(' + str(voucher.decimalLongitude) + ' ' + str(voucher.decimalLatitude) + ')', srid=4326)
                decimalLatitude_public = public_point(voucher.decimalLatitude)
                decimalLongitude_public = public_point(voucher.decimalLongitude)
                voucher.decimalLatitude_public = decimalLatitude_public
                voucher.decimalLongitude_public = decimalLongitude_public
                voucher.point_public = GEOSGeometry(
                    'POINT(' + str(decimalLongitude_public) + ' ' + str(decimalLatitude_public) + ')', srid=4326)
                voucher.save()
                if voucher.image:
                    filename = generate_etiquete(id)
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
