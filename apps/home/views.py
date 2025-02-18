# -*- coding: utf-8 -*-
import logging
import os
import zipfile

import dwca.terms as dwc

from django.conf import settings
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.db.models import Count
from django.db.models import Q
from django.db.models.functions import ExtractDay, ExtractMonth, ExtractYear
from django.http import HttpResponse
from django.shortcuts import render, redirect
from django.utils import translation
from django.utils.html import smart_urlquote
from dwca import DarwinCoreArchive
from dwca.classes import Taxon
from eml.types import ResponsibleParty, OrganizationName, I18nString, PositionName
from xml_common.utils import Language as EMLLanguage

from apps.digitalization.models import BiodataCode, Herbarium
from apps.home.forms import ProfileForm, UserForm
from apps.home.models import Profile


@login_required
def index(request):
    count_total_codes = BiodataCode.objects.filter(
        qr_generated=True
    ).order_by('page__created_at__date').annotate(
        day=ExtractDay('page__created_at'),
        month=ExtractMonth('page__created_at'),
        year=ExtractYear('page__created_at'),
    ).values('day', 'month', 'year').annotate(count=Count('*')).values('day', 'month', 'year', 'count')
    count_scanned_codes = BiodataCode.objects.filter(
        Q(qr_generated=True, voucher_state=1) |
        Q(qr_generated=True, voucher_state=7) |
        Q(qr_generated=True, voucher_state=8)
    ).order_by('page__created_at__date').annotate(
        day=ExtractDay('page__created_at'),
        month=ExtractMonth('page__created_at'),
        year=ExtractYear('page__created_at'),
    ).values('day', 'month', 'year').annotate(count=Count('*')).values('day', 'month', 'year', 'count')
    herbariums = [herbarium.collection_code for herbarium in Herbarium.objects.all()]
    stands = []
    digitalized = []
    for herbarium in herbariums:
        stands.append(BiodataCode.objects.filter(
            herbarium__collection_code=herbarium, voucher_state=0
        ).count())
        digitalized.append(BiodataCode.objects.filter(
            Q(voucher_state=1) | Q(voucher_state=7) | Q(voucher_state=8),
            herbarium__collection_code=herbarium
        ).count())
    max_total_codes = max([i['count'] for i in count_total_codes])
    bar_max = max(stands + digitalized)
    return render(
        request,
        'index.html',
        {
            'count_total_codes': count_total_codes,
            'y_max': int(max_total_codes * 1.05),
            'bar_max': int(bar_max * 1.1),
            'count_scanned_codes': count_scanned_codes,
            'herbariums': herbariums,
            'stands': stands,
            'digitalized': digitalized,
        }
    )


@login_required
def preference(request):
    user = User.objects.get(pk=request.user.pk)
    profile = Profile.objects.get(user=user)
    if request.method == "POST":
        user_form = UserForm(request.POST, instance=user)
        profile_form = ProfileForm(request.POST, instance=profile)
        if user_form.is_valid() and profile_form.is_valid():
            user = user_form.save(commit=True)
            new_password = user_form.cleaned_data["new_password"]
            if new_password is not None and len(new_password) != 0:
                logging.debug("Setting new password")
                user.set_password(new_password)
                user.save()
            profile_form.save(commit=True)
            return redirect("index")
        else:
            return render(request, "registration/preference.html", {
                "user_form": user_form,
                "profile_form": profile_form,
            })
    elif request.method == "GET":
        user_form = UserForm(instance=user)
        profile_form = ProfileForm(instance=profile)
        return render(request, "registration/preference.html", {
            "user_form": user_form,
            "profile_form": profile_form,
        })


@login_required()
def test_view(request):
    return render(request, "test.html")


@login_required()
def download_dwc_archive(request):
    return render(request, "download_dwc_archive.html")


@login_required()
def download_dwc_catalog(request):
    catalog = DarwinCoreArchive("https://catalogoplantas.udec.cl/")
    catalog.generate_eml("eml.xml")
    catalog.metadata.initialize_resource(
        "Catalogue of Vacular Plants of Chile",
        ResponsibleParty(
            organization_name=OrganizationName(I18nString("Departamento de Botánica, Facultad de Ciencias Naturales y Oceanográficas, Universidad de Concepción", EMLLanguage.ESP))
        ),
        contact=[
            ResponsibleParty(position_name=PositionName("Informatics Researcher"))
        ]
    )
    core = Taxon(
        0, "taxon.tsv", [
            dwc.TaxonID(0), dwc.ParentNameUsageID(1), dwc.AcceptedNameUsageID(2),
            dwc.OriginalNameUsageID(3), dwc.ScientificNameID(4), dwc.DWCDataset(5),
            dwc.TaxonomicStatus(6), dwc.TaxonRank(7), dwc.TaxonRemarks(8), dwc.ScientificName(9),
            dwc.Phylum(10), dwc.Kingdom(11), dwc.DWCClass(12), dwc.Order(13), dwc.Family(14), dwc.Genus(15),
            dwc.GenericName(16), dwc.InfragenericEpithet(17), dwc.SpecificEpithet(18),
            dwc.InfraspecificEpithet(19), dwc.ScientificNameAuthorship(20),
            dwc.NameAccordingTo(21), dwc.NamePublishedIn(22),
            dwc.NomenclaturalCode(23), dwc.NomenclaturalStatus(24)
        ], fields_terminated_by="\t", ignore_header_lines=1
    )
    catalog.core = core
    zip_filename = "tmp/data.zip"
    catalog.to_file(zip_filename)

    with open(zip_filename, "rb") as zip_file:
        response = HttpResponse(zip_file.read(), content_type="application/zip")
        response["Content-Disposition"] = f"attachment; filename={smart_urlquote(zip_filename)}"

    os.remove(zip_filename)

    return response

class ProfileLanguageMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request, *args, **kwargs):
        try:
            if request.user.is_authenticated:
                profile = Profile.objects.get_or_create(user=request.user)
                if profile[1]:
                    profile[0].save()
                translation.activate(profile[0].language)
            else:
                translation.activate(settings.LANGUAGE_CODE)
                logging.debug(f"No user, using default '{translation.get_language()}'")
        except Exception as e:
            logging.error(f"Error getting user language: {e}", exc_info=True)
        response = self.get_response(request)
        translation.deactivate()
        return response
