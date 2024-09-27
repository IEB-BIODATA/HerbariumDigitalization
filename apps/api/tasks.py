from django.template.loader import get_template
from tempfile import NamedTemporaryFile

import logging
import pandas as pd
from celery import shared_task
from django.http import QueryDict
from django.utils.translation import gettext_lazy as _, get_language, activate
from typing import Dict, List
from urllib.parse import urlencode

from apps.api.utils import filter_query_set, filter_by_geo
from apps.catalog.models import Species, Synonymy, DownloadSearchRegistration, Genus, Kingdom, Division, ClassName, \
    Order, Family, CommonName, ConservationStatus, Cycle, PlantHabit, Region, Status
from intranet.utils import send_mail


@shared_task(name='request_download')
def request_download(params: Dict[str, List[str]], request_user: int):
    request_user: DownloadSearchRegistration = DownloadSearchRegistration.objects.get(pk=request_user)
    query_params = QueryDict(urlencode(params, doseq=True))
    default_language = get_language()
    lang = query_params.get('lang', default_language)
    activate(lang)
    species_queryset = filter_query_set(Species.objects.all(), query_params)
    species_queryset = species_queryset.filter(
        filter_by_geo(query_params, "voucherimported__point__within")
    ).distinct()
    species_list = [
        (
            species.unique_taxon_id, species.scientific_name, species.scientific_name_full,
            species.division.name, species.classname.name, species.order.name,
            species.family.name, "accepted", species.unique_taxon_id
        )
        for species in species_queryset
    ]
    species_filter = query_params.get("species_filter", "false").lower() == "true"
    if not species_filter:
        synonyms_queryset = filter_query_set(Synonymy.objects.all(), query_params)
        synonyms_queryset = synonyms_queryset.filter(
            filter_by_geo(query_params, "species__voucherimported__point__within")
        ).distinct()
        synonyms_list = [
            (
                species.unique_taxon_id, species.scientific_name, species.scientific_name_full,
                species.species.division.name, species.species.classname.name, species.species.order.name,
                species.species.family.name, "synonym", species.species.unique_taxon_id
            ) if species.species is not None else (
                species.unique_taxon_id, species.scientific_name, species.scientific_name_full,
                "", "", "", "", "synonym", ""
            )
            for species in synonyms_queryset
        ]
    else:
        synonyms_list = list()
    data = pd.DataFrame(species_list + synonyms_list, columns=[
        "id", "scientificName", "scientificNameFull",
        "division", "class", "order",
        "family", "taxonomicStatus", "acceptedSpeciesId"
    ])
    params = [{
        "label": _("Geometry"),
        "parameters": query_params.getlist("geometry", []),
    }]
    for name, label, rank_model in [
        ("kingdom", _("Kingdom"), Kingdom),
        ("division", _("Division"), Division),
        ("classname", _("Class"), ClassName),
        ("order", _("Order"), Order),
        ("family", _("Family"), Family),
        ("genus", _("Genus"), Genus),
    ]:
        params.append({
            "label": label, "parameters": [
                rank_model.objects.get(unique_taxon_id=rank).name for rank in query_params.getlist(name, [])
            ]
        })
    for name, label, attr_model in [
        ("common_name", _("Common Name"), CommonName),
        ("conservation_status", _("Conservation Status"), ConservationStatus),
        ("cycle", _("Cycle"), Cycle),
        ("plant_habit", _("Plant Habit"), PlantHabit),
        ("env_habit", _("Environmental Habit"), PlantHabit),
        ("region", _("Region"), Region),
        ("status", _("Status"), Status),
    ]:
        params.append({
            "label": label, "parameters": [
                attr_model.objects.get(id=attr).name for attr in query_params.getlist(name, [])
            ]
        })
    template = get_template("others/download_mail.html").render({
        "name": request_user.name,
        "params": params,
        "species_found": len(species_list),
        "synonyms_found": len(synonyms_list),
    })
    with NamedTemporaryFile(delete=True, suffix=f".{request_user.get_format_display()}") as file:
        if request_user.format in [0, 2]:
            sep = {0: ",", 2: "\t"}[request_user.format]
            data.to_csv(file.name, index=False, sep=sep)
        else:
            data.to_excel(file.name, index=False)
        try:
            send_mail(template, request_user.mail, _("Species List"), attachment_path=file.name)
            request_user.request_status = True
            request_user.save()
        except Exception as e:
            logging.warning(e, exc_info=True)
    return len(data)
