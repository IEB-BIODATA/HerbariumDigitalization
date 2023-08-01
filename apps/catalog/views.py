import re
import tablib
import json
import logging
import pandas as pd
import datetime as dt
from typing import Dict, Type
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.core import serializers
from django.core.paginator import Paginator
from django.db.models import Q
from django import forms
from django.forms.utils import ErrorList
from django.http import HttpResponse, JsonResponse, HttpRequest, HttpResponseServerError
from django.shortcuts import render, redirect
from django.urls import reverse
from rest_framework.serializers import SerializerMetaclass

from apps.digitalization.models import VoucherImported
from .forms import DivisionForm, ClassForm, OrderForm, FamilyForm, GenusForm, SpeciesForm, SynonymyForm, BinnacleForm, \
    CommonNameForm
from .models import Species, CatalogView, SynonymyView, RegionDistributionView, Division, ClassName, Order, Family, \
    Genus, Synonymy, Region, CommonName, Binnacle, PlantHabit, EnvironmentalHabit, Cycle, TaxonomicModel, \
    ConservationState
from .utils import generate_etiquete
from .tasks import update_voucher_name
from ..api.serializers import DivisionSerializer, ClassSerializer, OrderSerializer, \
    FamilySerializer, GenusSerializer, SynonymysSerializer, CommonNameSerializer, SpeciesSerializer, \
    CatalogViewSerializer

MANY_RELATIONS = [
    ("common_names", "nombres comunes", CommonName),
    ("synonymys", "sinónimos", Synonymy),
    ("plant_habit", "hábito", PlantHabit),
    ("env_habit", "forma de vida", EnvironmentalHabit),
    ("cycle", "ciclo de vida", Cycle),
    ("region", "región", Region),
    ("conservation_state", "estado de conservación", ConservationState),
]


@login_required
def catalog_download(request):
    if request.method == "GET":
        headers1 = ["id", "id_taxa", "kingdom", "division", "class_name", "order", "family", "genus", "scientificName",
                    "scientificNameFull"
            , "specificEpithet", "scientificNameAuthorship", "subespecie", "autoresSsp", "variedad", "autoresVariedad",
                    "forma", "autoresForma"
            , "enArgentina", "enBolivia", "enPeru", "habit", "ciclo", "status", "alturaMinima", "alturaMaxima",
                    "notas", "id_tipo"
            , "publicacion", "volumen", "paginas", "anio", "determined", "id_taxa_origin"]
        headers2 = ["id", "specie_id", "id_taxa", "specie scientificName", "synonymy id", "synonymy scientificName",
                    "scientificNameFull", "genus", "specificEpithet", "scientificNameAuthorship"
            , "subespecie", "autoresSsp", "variedad", "autoresVariedad", "forma", "autoresForma"]
        headers3 = ["id", "specie_id", "id_taxa", "specie scientificName", "region name", "region key"]
        species = CatalogView.objects.values_list("id", "id_taxa", "kingdom", "division", "class_name", "order",
                                                  "family", "genus", "scientificName", "scientificNameFull"
                                                  , "specificEpithet", "scientificNameAuthorship", "subespecie",
                                                  "autoresSsp", "variedad", "autoresVariedad", "forma", "autoresForma"
                                                  , "enArgentina", "enBolivia", "enPeru", "habit", "ciclo", "status",
                                                  "alturaMinima", "alturaMaxima", "notas", "id_tipo"
                                                  , "publicacion", "volumen", "paginas", "anio", "determined",
                                                  "id_taxa_origin").order_by("id")
        synonymys = SynonymyView.objects.values_list("id", "specie_id", "id_taxa", "specie_scientificname",
                                                     "synonymy_id", "scientificName", "scientificNameFull", "genus",
                                                     "specificEpithet", "scientificNameAuthorship"
                                                     , "subespecie", "autoresSsp", "variedad", "autoresVariedad",
                                                     "forma", "autoresForma").order_by("id")
        region = RegionDistributionView.objects.values_list("id", "specie_id", "id_taxa",
                                                            "specie_scientificname", "region_name",
                                                            "region_key").order_by("id")
        databook = tablib.Databook()
        data_set1 = tablib.Dataset(*species, headers=headers1, title="Species")
        data_set2 = tablib.Dataset(*synonymys, headers=headers2, title="Synonymys")
        data_set3 = tablib.Dataset(*region, headers=headers3, title="Region Distribution")
        databook.add_sheet(data_set1)
        databook.add_sheet(data_set2)
        databook.add_sheet(data_set3)
        response = HttpResponse(databook.xlsx, content_type="application/vnd.ms-Excel")
        response["Content-Disposition"] = "attachment; filename=catalog.xlsx"
        return response


def __catalog_table__(
        request: HttpRequest,
        model: Type[TaxonomicModel],
        serializer: SerializerMetaclass,
        sort_by_func: Dict[int, str],
        model_name: str,
        add_searchable: Q = None
) -> JsonResponse:
    entries = model.objects.all()
    search_value = request.GET.get("search[value]", None)
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
    sort_by = int(request.GET.get("order[0][column]", 4))
    sort_type = request.GET.get("order[0][dir]", "desc")

    if sort_by in sort_by_func:
        logging.debug("Order by {} ({}) in {} order".format(
            sort_by,
            sort_by_func[sort_by],
            "ascending" if sort_type == "asc" else "descending"
        ))
        entries = entries.order_by(
            ("" if sort_type == "asc" else "-") + sort_by_func[sort_by]
        )

    length = int(request.GET.get("length", 10))
    start = int(request.GET.get("start", 0))
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
        "draw": int(request.GET.get("draw", 0)),
        "recordsTotal": entries.count(),
        "recordsFiltered": paginator.count,
        "data": data
    })


def __create_catalog__(
        form: forms.ModelForm,
        user: User,
        request: HttpRequest = None
) -> bool:
    if form.is_valid():
        try:
            new_model = form.save(commit=False)
            new_model.save(user=user)
            if request:
                if new_model.__class__.__name__ == "Species":
                    for relation, _, many_model in MANY_RELATIONS:
                        for identifier in request.POST.getlist(relation):
                            getattr(new_model, relation).add(many_model.objects.get(id=identifier))
            CatalogView.refresh_view()
            SynonymyView.refresh_view()
            RegionDistributionView.refresh_view()
            return True
        except Exception as e:
            logging.error(e, exc_info=True)
            return False
    else:
        return False


def __update_catalog__(
        form: forms.ModelForm,
        user: User,
        request: HttpRequest = None
) -> bool:
    if form.is_valid():
        try:
            new_model = form.save(commit=False)
            if request:
                if new_model.__class__.__name__ == "Species":
                    changes = list()
                    for relation, relation_name, many_model in MANY_RELATIONS:
                        for old_relation in getattr(new_model, relation).all():
                            if str(old_relation.id) not in request.POST.getlist(relation):
                                getattr(new_model, relation).remove(old_relation)
                                changes.append("Se elimina '{}' de '{}'".format(old_relation, relation_name))
                        for identifier in request.POST.getlist(relation):
                            if not getattr(new_model, relation).filter(id=identifier).exists():
                                new_relation = many_model.objects.get(id=identifier)
                                getattr(new_model, relation).add(new_relation)
                                changes.append("Se añade '{}' a '{}'".format(new_relation, relation_name))
                    if len(changes) > 0:
                        Binnacle.update_entry(repr(new_model), new_model, user, notes=". ".join(changes))
            new_model.save(user=user)
            CatalogView.refresh_view()
            SynonymyView.refresh_view()
            RegionDistributionView.refresh_view()
            return True
        except Exception as e:
            logging.error(e, exc_info=True)
            return False
    else:
        return False


def __delete_catalog__(model: TaxonomicModel, user: User):
    Binnacle.delete_entry(model, user)
    CatalogView.refresh_view()
    SynonymyView.refresh_view()
    RegionDistributionView.refresh_view()
    return


def __create_catalog_route__(
        request: HttpRequest,
        form_class: Type[forms.ModelForm],
        model_name: str,
        rank_title: str,
        rank_name: str,
        rank_name_label: str,
        parent_name: str,
        parent_name_label: str
) -> HttpResponse:
    if request.method == "POST":
        form = form_class(request.POST)
        if __create_catalog__(form, request.user):
            return redirect("list_{}".format(model_name))
    else:
        form = form_class()
    return render(request, "catalog/create_catalog.html", {
        "rank_title": rank_title,
        "create_rank_url": reverse("create_{}".format(model_name)),
        "rank_name_label": rank_name_label,
        "parent_name_label": parent_name_label,
        "form_name": form[rank_name],
        "form_parent": form[parent_name],
        "form": form,
        "list_url": reverse("list_{}".format(model_name))
    })


def __update_catalog_route__(
        request: HttpRequest,
        model: Type[TaxonomicModel],
        form_class: Type[forms.ModelForm],
        model_name: str,
        rank_title: str,
        rank_name: str,
        rank_name_label: str,
        parent_name: str,
        parent_name_label: str,
        identifier: int
) -> HttpResponse:
    entry = model.objects.get(id=identifier)
    if request.method == "POST":
        form = form_class(request.POST, instance=entry)
        if __update_catalog__(form, request.user):
            return redirect("list_{}".format(model_name))
    else:
        form = form_class(instance=entry)
    return render(request, "catalog/update_catalog.html", {
        "rank_title": rank_title,
        "id": identifier,
        "update_url": reverse(
            "update_{}".format(model_name),
            kwargs={
                "{}_id".format(model_name): identifier
            }
        ),
        "rank_name_label": rank_name_label,
        "parent_rank_label": parent_name_label,
        "form": form,
        "form_name": form[rank_name],
        "form_parent": form[parent_name],
        "list_url": reverse("list_{}".format(model_name))
    })


@login_required
def list_division(request):
    return render(request, "catalog/list_catalog.html", {
        "table_url": reverse("division_table"),
        "rank_name": "name",
        "parent_rank": "kingdom",
        "update_rank_url": reverse("update_division", kwargs={"division_id": 0}),
        "rank_title": "División",
        "create_rank_url": reverse("create_division"),
        "rank_name_title": "Nombre",
        "parent_rank_title": "Reino",
        "deletable": 0,
    })


@login_required
def division_table(request):
    sort_by_func = {
        0: "name",
        1: "kingdom__name",
        2: "created_by__username",
        3: "created_at",
        4: "updated_at",
    }
    return __catalog_table__(
        request, Division, DivisionSerializer,
        sort_by_func, "divisions"
    )


@login_required
def create_division(request):
    return __create_catalog_route__(
        request, DivisionForm,
        "division", "División",
        "name", "Nombre",
        "kingdom", "Reino"
    )


@login_required
def update_division(request, division_id):
    return __update_catalog_route__(
        request, Division, DivisionForm,
        "division", "División",
        "name", "Nombre", "kingdom", "Reino",
        division_id
    )


@login_required
def list_class(request):
    return render(request, "catalog/list_catalog.html", {
        "table_url": reverse("class_table"),
        "rank_name": "name",
        "parent_rank": "division",
        "update_rank_url": reverse("update_class", kwargs={"class_id": 0}),
        "rank_title": "Clase",
        "create_rank_url": reverse("create_class"),
        "rank_name_title": "Nombre",
        "parent_rank_title": "División",
        "deletable": 0,
    })


@login_required
def class_table(request):
    sort_by_func = {
        0: "name",
        1: "division__name",
        2: "created_by__username",
        3: "created_at",
        4: "updated_at",
    }
    return __catalog_table__(
        request, ClassName, ClassSerializer,
        sort_by_func, "classes"
    )


@login_required
def create_class(request):
    return __create_catalog_route__(
        request, ClassForm,
        "class", "Clase",
        "name", "Nombre",
        "division", "Division"
    )


@login_required
def update_class(request, class_id):
    return __update_catalog_route__(
        request, ClassName, ClassForm,
        "class", "Clase",
        "name", "Nombre", "division", "División",
        class_id
    )


@login_required
def list_order(request):
    return render(request, "catalog/list_catalog.html", {
        "table_url": reverse("order_table"),
        "rank_name": "name",
        "parent_rank": "class_name",
        "update_rank_url": reverse("update_order", kwargs={"order_id": 0}),
        "rank_title": "Orden",
        "rank_name_title": "Nombre",
        "create_rank_url": reverse("create_order"),
        "parent_rank_title": "Clase",
        "deletable": 0,
    })


@login_required
def order_table(request):
    sort_by_func = {
        0: "name",
        1: "class_name__name",
        2: "created_by__username",
        3: "created_at",
        4: "updated_at",
    }
    return __catalog_table__(
        request, Order, OrderSerializer,
        sort_by_func, "orders"
    )


@login_required
def create_order(request):
    return __create_catalog_route__(
        request, OrderForm,
        "order", "Orden",
        "name", "Nombre",
        "class", "Clase"
    )


@login_required
def update_order(request, order_id):
    return __update_catalog_route__(
        request, Order, OrderForm,
        "order", "Orden",
        "name", "Nombre", "class_name", "Clase",
        order_id
    )


@login_required
def list_family(request):
    return render(request, "catalog/list_catalog.html", {
        "table_url": reverse("family_table"),
        "rank_name": "name",
        "parent_rank": "order",
        "update_rank_url": reverse("update_family", kwargs={"family_id": 0}),
        "rank_title": "Familia",
        "rank_name_title": "Nombre",
        "create_rank_url": reverse("create_family"),
        "parent_rank_title": "Orden",
        "deletable": 0,
    })


@login_required
def family_table(request):
    sort_by_func = {
        0: "name",
        1: "order__name",
        2: "created_by__username",
        3: "created_at",
        4: "updated_at",
    }
    return __catalog_table__(
        request, Family, FamilySerializer,
        sort_by_func, "families"
    )


@login_required
def create_family(request):
    return __create_catalog_route__(
        request, FamilyForm,
        "family", "Familia",
        "name", "Nombre",
        "order", "Orden"
    )


@login_required
def update_family(request, family_id):
    return __update_catalog_route__(
        request, Family, FamilyForm,
        "family", "Familia",
        "name", "Nombre", "order", "Orden",
        family_id
    )


@login_required
def list_genus(request):
    return render(request, "catalog/list_catalog.html", {
        "table_url": reverse("genus_table"),
        "rank_name": "name",
        "parent_rank": "family",
        "update_rank_url": reverse("update_genus", kwargs={"genus_id": 0}),
        "rank_title": "Género",
        "rank_name_title": "Nombre",
        "create_rank_url": reverse("create_genus"),
        "parent_rank_title": "Familia",
        "deletable": 0,
    })


@login_required
def genus_table(request):
    sort_by_func = {
        0: "name",
        1: "family__name",
        2: "created_by__username",
        3: "created_at",
        4: "updated_at",
    }
    return __catalog_table__(
        request, Genus, GenusSerializer,
        sort_by_func, "genuses"
    )


@login_required
def create_genus(request):
    return __create_catalog_route__(
        request, GenusForm,
        "genus", "Género",
        "name", "Nombre",
        "family", "Familia"
    )


@login_required
def update_genus(request, genus_id):
    genus = Genus.objects.get(id=genus_id)
    if request.method == "POST":
        genus_name = request.POST["genus_name"]
        family = Family.objects.get(id=request.POST["family_id"])
        total_species = Species.objects.filter(genus=genus)
        selected_species = list(filter(lambda x: "specie_id_" in x, request.POST))
        if len(selected_species) < total_species.count():
            genus = Genus(name=genus_name, family=family)
        else:
            genus.name = genus_name
            genus.family = family
        genus.save(user=request.user)
        for species_id in selected_species:
            species = Species.objects.get(id=int(species_id.replace("specie_id_", "")))
            species.genus = genus
            previous_author = species.scientificNameAuthorship
            regexp = re.compile("\((.+)\)")
            if regexp.search(previous_author):
                previous_author = regexp.search(previous_author).group(0)
                author = previous_author + " " + request.POST["author_name"]
            else:
                author = "(" + previous_author + ") " + request.POST["author_name"]
            species.scientificNameAuthorship = author
            species.save(user=request.user)
        CatalogView.refresh_view()
        SynonymyView.refresh_view()
        RegionDistributionView.refresh_view()
        return redirect("list_genus")
    else:
        form = GenusForm(instance=genus)
    return render(request, "catalog/update_genus.html", {
        "form": form,
        "id": genus_id
    })


def proposal_genus(request, genus_id):
    species = Species.objects.filter(genus=genus_id)
    prev_genus = Genus.objects.get(id=genus_id)
    proposal = []
    genus = request.POST["name"]
    prev_genus.name = genus
    family = request.POST["family"]
    author = request.POST["author"]
    for specie in species:
        specie.genus = prev_genus
        scientific_name_authorship = str(specie.scientificNameAuthorship)
        regexp = re.compile("\((.+)\)")
        if regexp.search(scientific_name_authorship):
            previous_autor = regexp.search(scientific_name_authorship).group(0)
            specie.scientificNameAuthorship = previous_autor + " " + author
        else:
            specie.scientificNameAuthorship = "(" + scientific_name_authorship + ") " + author
        specie.__update_scientific_name__()
        proposal.append([
            specie.id, specie.scientificName, specie.scientificNameFull, specie.scientificNameAuthorship
        ])
    result = pd.DataFrame(proposal, columns=["id", "scientificName", "scientificNameFull", "scientificNameAuthorship"])
    return HttpResponse(
        json.dumps({
            "data": result.to_json(),
            "genus": genus,
            "family": family,
            "author": author
        }),
        content_type="application/json"
    )


def update_genus_family(request, genus_id):
    genus = Genus.objects.get(id=genus_id)
    if request.method == "POST":
        form = GenusForm(request.POST, instance=genus)
        if __update_catalog__(form, request.user):
            return redirect("list_genus")
    else:
        form = GenusForm(instance=genus)
    return render(request, "catalog/update_genus_family.html", {
        "form": form, "id": genus_id
    })


@login_required
def list_taxa(request):
    return render(request, "catalog/list_taxa.html")


@login_required
def taxa_table(request):
    sort_by_func = {
        0: "division",
        1: "class_name",
        2: "order",
        3: "family",
        4: "scientificNameFull",
        5: "created_by",
        6: "created_at",
        7: "updated_at",
        8: "status",
        9: "determined"
    }
    search_value = request.GET.get("search[value]", None)
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
    if request.method == "POST":
        form = SpeciesForm(request.POST)
        if __create_catalog__(form, request.user, request):
            return redirect("list_taxa")
    else:
        form = SpeciesForm()
    return render(request, "catalog/create_taxa.html", {"form": form})


def update_taxa(request, species_id):
    species = Species.objects.get(id=species_id)
    warnings = False
    warning_text = ""
    gallery_warning = species.galleryimage_set.exists()
    voucher_warning = species.voucherimported_set.exists()
    synonymy_warning = species.synonymys.exists()
    if gallery_warning or voucher_warning or synonymy_warning:
        warnings = True
        warning_text = "Esta especie no puede ser eliminada debido a que está asociada a {}{}{}".format(
            "galería " if gallery_warning else "",
            "scans " if voucher_warning else "",
            "sinónimos" if synonymy_warning else "",
        )
    if request.method == "POST":
        form = SpeciesForm(request.POST, instance=species)
        if __update_catalog__(form, request.user, request=request):
            return redirect("list_taxa")
    else:
        form = SpeciesForm(instance=species)
    return render(request, "catalog/update_taxa.html", {
        "form": form,
        "id": species_id,
        "species_name": species.scientificNameFull,
        "warnings": warnings,
        "warning_text": warning_text,
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
    return redirect("list_taxa")


@login_required
def merge_taxa(request, id):
    taxa_1 = Species.objects.get(id=id)
    species = Species.objects.all()
    form = SpeciesForm(instance=taxa_1)
    if request.method == "POST":
        form = SpeciesForm(request.POST)
        if form.is_valid():
            try:
                if request.POST["id_taxon_2"] == "":
                    errors = form._errors.setdefault("id_taxa", ErrorList())
                    errors.append(u"Debe seleccionar taxón para unir")
                    return render(request, "catalog/merge_taxa.html",
                                  {"form": form, "taxa_1": taxa_1, "id_taxon_1": id, "species": species})
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

                    taxon_2_id = request.POST["id_taxon_2"]
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

                    common_names = request.POST.getlist("common_names")
                    for common_name in common_names:
                        specie_new.common_names.add(CommonName.objects.get(id=common_name))

                    synonymys = request.POST.getlist("synonymys")
                    for synonymy in synonymys:
                        specie_new.synonymys.add(Synonymy.objects.get(id=synonymy))

                    region = request.POST.getlist("region")
                    for region in region:
                        specie_new.region.add(Region.objects.get(id=region))

                    plant_habit = request.POST.getlist("plant_habit")
                    for habit in plant_habit:
                        specie_new.plant_habit.add(PlantHabit.objects.get(id=habit))

                    env_habit = request.POST.getlist("env_habit")
                    for habit in env_habit:
                        specie_new.env_habit.add(EnvironmentalHabit.objects.get(id=habit))

                    cycles = request.POST.getlist("cycle")
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
                    return redirect("list_taxa")

            except Exception as e:
                print(e)
                pass

    return render(request, "catalog/merge_taxa.html",
                  {"form": form, "taxa_1": taxa_1, "id_taxon_1": id, "species": species})


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

            plant_habit = request.POST.getlist("plant_habit")
            for habit in plant_habit:
                taxa_1.plant_habit.add(PlantHabit.objects.get(id=habit))

            env_habit = request.POST.getlist("env_habit")
            for habit in env_habit:
                taxa_1.env_habit.add(EnvironmentalHabit.objects.get(id=habit))

            cycles = request.POST.getlist("cycle")
            for cycle in cycles:
                taxa_1.cycle.add(Cycle.objects.get(id=cycle))

            common_names = request.POST.getlist("common_names")
            for common_name in common_names:
                taxa_1.common_names.add(CommonName.objects.get(id=common_name))

            synonymys = request.POST.getlist("synonymys")
            for synonymy in synonymys:
                taxa_1.synonymys.add(Synonymy.objects.get(id=synonymy))
            taxa_1.synonymys.add(new_synonymy)

            region = request.POST.getlist("region")
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

            return redirect("list_taxa")

    return render(request, "catalog/split_1_taxa.html",
                  {"form_taxa_1": form_taxa_1, "taxa_1": taxa_1, "id_taxon_1": specie_id})


@login_required
def split_2_taxa(request, id):
    taxa_1 = Species.objects.get(id=id)
    form_taxa_1 = SpeciesForm(instance=taxa_1, prefix="form_taxa_1")
    form_taxa_2 = SpeciesForm(instance=taxa_1, prefix="form_taxa_2")
    if request.method == "POST":
        form_taxa_1 = SpeciesForm(request.POST, prefix="form_taxa_1")
        form_taxa_2 = SpeciesForm(request.POST, prefix="form_taxa_2")
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

            common_names = request.POST.getlist("form_taxa_1-common_names")
            for common_name in common_names:
                specie_new_1.common_names.add(CommonName.objects.get(id=common_name))

            synonymys = request.POST.getlist("form_taxa_1-synonymys")
            for synonymy in synonymys:
                specie_new_1.synonymys.add(Synonymy.objects.get(id=synonymy))

            region = request.POST.getlist("form_taxa_1-region")
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

            common_names = request.POST.getlist("form_taxa_2-common_names")
            for common_name in common_names:
                specie_new_2.common_names.add(CommonName.objects.get(id=common_name))

            synonymys = request.POST.getlist("form_taxa_2-synonymys")
            for synonymy in synonymys:
                specie_new_2.synonymys.add(Synonymy.objects.get(id=synonymy))

            region = request.POST.getlist("form_taxa_2-region")
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

            return redirect("list_taxa")

    return render(request, "catalog/split_2_taxa.html",
                  {"form_taxa_1": form_taxa_1, "form_taxa_2": form_taxa_2, "taxa_1": taxa_1, "id_taxon_1": id})


@login_required
def get_taxa(request, id):
    taxa = Species.objects.get(id=id)
    data = serializers.serialize("json", [taxa, ])
    json_data = json.loads(data)
    json_data[0]["fields"]["id"] = id
    json_data[0]["fields"]["genus_name"] = taxa.genus.name
    json_data[0]["fields"]["status_name"] = taxa.status.name
    common_names = ""
    common_names_id = []
    for common_name in taxa.common_names.all():
        common_names += str(common_name) + ", "
        common_names_id.append(common_name.id)
    json_data[0]["fields"]["common_names"] = common_names
    json_data[0]["fields"]["common_names_2"] = common_names_id
    synonymys = ""
    synonymys_id = []
    for synonymy in taxa.synonymys.all():
        synonymys += str(synonymy) + ", "
        synonymys_id.append(synonymy.id)
    json_data[0]["fields"]["synonymys"] = synonymys
    json_data[0]["fields"]["synonymys_2"] = synonymys_id
    plant_habit = ""
    plant_habit_id = []
    for habit in taxa.plant_habit.all():
        plant_habit += str(habit) + ", "
        plant_habit_id.append(habit.id)
    json_data[0]["fields"]["plant_habit"] = plant_habit
    json_data[0]["fields"]["plant_habit_2"] = plant_habit_id
    env_habit = ""
    env_habit_id = []
    for habit in taxa.env_habit.all():
        env_habit += str(habit) + ", "
        env_habit_id.append(habit.id)
    json_data[0]["fields"]["env_habit"] = env_habit
    json_data[0]["fields"]["env_habit_2"] = env_habit_id
    cycles = ""
    cycle_id = []
    for cycle in taxa.cycle.all():
        cycles += str(cycle) + ", "
        cycle_id.append(cycle.id)
    json_data[0]["fields"]["cycle"] = cycles
    json_data[0]["fields"]["cycle_2"] = cycle_id
    regions = ""
    region_id = []
    for region in taxa.region.all():
        regions += str(region) + ", "
        region_id.append(region.id)
    json_data[0]["fields"]["region"] = regions
    json_data[0]["fields"]["region_2"] = region_id
    return HttpResponse(json.dumps(json_data), content_type="application/json")


@login_required
def list_synonymy(request):
    return render(request, "catalog/list_catalog.html", {
        "table_url": reverse("synonymy_table"),
        "rank_name": "scientificNameFull",
        "parent_rank": "species",
        "update_rank_url": reverse("update_synonymy", kwargs={"synonymy_id": 0}),
        "rank_title": "Sinónimos",
        "rank_name_title": "Nombre Científico Completo",
        "create_rank_url": reverse("create_synonymy"),
        "parent_rank_title": "Especie",
        "deletable": 1,
    })


@login_required
def synonymy_table(request):
    sort_by_func = {
        0: "scientificNameFull",
        1: "species",
        2: "created_by__username",
        3: "created_at",
        4: "updated_at",
    }
    return __catalog_table__(
        request, Synonymy, SynonymysSerializer,
        sort_by_func, "synonyms"
    )


def create_synonymy(request):
    if request.method == "POST":
        form = SynonymyForm(request.POST)
        if __create_catalog__(form, request.user):
            return redirect("list_synonymy")
    else:
        form = SynonymyForm()
    return render(request, "catalog/create_synonymy.html", {
        "form": form
    })


def update_synonymy(request, synonymy_id):
    synonymy = Synonymy.objects.get(id=synonymy_id)
    if request.method == "POST":
        form = SynonymyForm(request.POST, instance=synonymy)
        if __update_catalog__(form, request.user):
            return redirect("list_synonymy")
    else:
        form = SynonymyForm(instance=synonymy)
    return render(request, "catalog/update_synonymy.html", {
        "form": form, "id": synonymy_id
    })


def delete_synonymy(request, synonymy_id):
    synonymy = Synonymy.objects.get(id=synonymy_id)
    try:
        __delete_catalog__(synonymy, request.user)
        return redirect("list_synonymy")
    except Exception as e:
        logging.error(e, exc_info=True)
        return HttpResponseServerError()


@login_required
def list_binnacle(request):
    binnacles = Binnacle.objects.all()
    return render(request, "catalog/list_binnacle.html", {"binnacles": binnacles})


def update_binnacle(request, binnacle_id):
    binnacle = Binnacle.objects.get(id=binnacle_id)
    if request.method == "POST":
        form = BinnacleForm(request.POST, instance=binnacle)
        if form.is_valid():
            binnacle = form.save(commit=False)
            binnacle.updated_at = dt.datetime.now()
            binnacle.save()
            return redirect("list_binnacle")
    else:
        form = BinnacleForm(instance=binnacle)
    return render(request, "catalog/update_binnacle.html", {"form": form, "id": binnacle_id})


@login_required
def list_common_name(request):
    return render(request, "catalog/list_catalog.html", {
        "table_url": reverse("common_name_table"),
        "rank_name": "name",
        "parent_rank": "species",
        "update_rank_url": reverse("update_common_name", kwargs={"common_id": 0}),
        "rank_title": "Nombre Común",
        "rank_name_title": "Nombre",
        "create_rank_url": reverse("create_common_name"),
        "parent_rank_title": "Especie",
        "deletable": 1,
    })


@login_required
def common_name_table(request):
    sort_by_func = {
        0: "name",
        1: "species__scientificName",
        2: "created_by__username",
        3: "created_at",
        4: "updated_at",
    }
    return __catalog_table__(
        request, CommonName, CommonNameSerializer,
        sort_by_func, "divisions"
    )


@login_required
def create_common_name(request):
    if request.method == "POST":
        form = CommonNameForm(request.POST)
        if __create_catalog__(form, request.user):
            return redirect("list_common_name")
    else:
        form = CommonNameForm()
    return render(request, "catalog/create_common_name.html", {
        "form": form
    })


def update_common_name(request, common_id):
    common_name = CommonName.objects.get(id=common_id)
    if request.method == "POST":
        form = CommonNameForm(request.POST, instance=common_name)
        if __update_catalog__(form, request.user):
            return redirect("list_common_name")
    else:
        form = CommonNameForm(instance=common_name)
    return render(request, "catalog/update_common_name.html", {
        "form": form, "id": common_id
    })


def delete_common_name(request, common_id):
    common_name = CommonName.objects.get(id=common_id)
    try:
        __delete_catalog__(common_name, request.user)
        return redirect("list_common_name")
    except Exception as e:
        logging.error(e, exc_info=True)
        return HttpResponseServerError
