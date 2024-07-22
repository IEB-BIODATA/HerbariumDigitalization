import os

import datetime as dt
import logging
from typing import Type

import tablib
from django import forms
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.db.models import Q
from django.http import HttpResponse, JsonResponse, HttpRequest, HttpResponseServerError
from django.shortcuts import render, redirect
from django.urls import reverse
from django.utils.translation import gettext_lazy as _
from rest_framework.serializers import SerializerMetaclass

from intranet.utils import paginated_table
from .forms import DivisionForm, ClassForm, OrderForm, FamilyForm, GenusForm, SpeciesForm, SynonymyForm, BinnacleForm, \
    CommonNameForm
from .models import Species, CatalogView, SynonymyView, RegionDistributionView, Division, ClassName, Order, Family, \
    Genus, Synonymy, Region, CommonName, Binnacle, PlantHabit, EnvironmentalHabit, Cycle, TaxonomicModel, \
    ConservationState, FinderView
from .serializers import DivisionSerializer, ClassSerializer, OrderSerializer, FamilySerializer, GenusSerializer, \
    CatalogViewSerializer, SpeciesSerializer, SynonymsSerializer, BinnacleSerializer, CommonNameSerializer
from ..digitalization.storage_backends import PrivateMediaStorage
from ..digitalization.utils import TaskProcessLogger

MANY_RELATIONS = [
    ("common_names", "nombres comunes", CommonName),
    ("synonyms", "sinónimos", Synonymy),
    ("plant_habit", "hábito", PlantHabit),
    ("env_habit", "forma de vida", EnvironmentalHabit),
    ("cycle", "ciclo de vida", Cycle),
    ("region", "región", Region),
    ("conservation_state", "estado de conservación", ConservationState),
]


@login_required
def catalog_download(request):
    if request.method == "GET":
        headers1 = ["id", "id_taxa", "kingdom", "division", "classname", "order", "family", "genus", "scientific_name",
                    "scientific_name_full"
            , "specific_epithet", "scientific_name_authorship", "subspecies", "ssp_authorship", "variety", "variety_authorship",
                    "form", "form_authorship"
            , "in_argentina", "in_bolivia", "in_peru", "habit", "ciclo", "status", "minimum_height", "maximum_height",
                    "notes", "type_id"
            , "publication", "volume", "pages", "year", "determined", "id_taxa_origin"]
        headers2 = ["id", "specie_id", "id_taxa", "specie scientific_name", "synonymy id", "synonymy scientific_name",
                    "scientific_name_full", "genus", "specific_epithet", "scientific_name_authorship"
            , "subspecies", "ssp_authorship", "variety", "variety_authorship", "form", "form_authorship"]
        headers3 = ["id", "specie_id", "id_taxa", "specie scientific_name", "region name", "region key"]
        species = CatalogView.objects.values_list("id", "id_taxa", "kingdom", "division", "classname", "order",
                                                  "family", "genus", "scientific_name", "scientific_name_full"
                                                  , "specific_epithet", "scientific_name_authorship", "subspecies",
                                                  "ssp_authorship", "variety", "variety_authorship", "form", "form_authorship"
                                                  , "in_argentina", "in_bolivia", "in_peru", "habit", "ciclo", "status",
                                                  "minimum_height", "maximum_height", "notes", "type_id"
                                                  , "publication", "volume", "pages", "year", "determined",
                                                  "id_taxa_origin").order_by("id")
        synonyms = SynonymyView.objects.values_list("id", "specie_id", "id_taxa", "specie_scientific_name",
                                                     "synonymy_id", "scientific_name", "scientific_name_full", "genus",
                                                     "specific_epithet", "scientific_name_authorship"
                                                     , "subspecies", "ssp_authorship", "variety", "variety_authorship",
                                                     "form", "form_authorship").order_by("id")
        region = RegionDistributionView.objects.values_list("id", "specie_id", "id_taxa",
                                                            "specie_scientific_name", "region_name",
                                                            "region_key").order_by("id")
        databook = tablib.Databook()
        data_set1 = tablib.Dataset(*species, headers=headers1, title="Species")
        data_set2 = tablib.Dataset(*synonyms, headers=headers2, title="Synonymys")
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
        sort_by_func: dict[int, str],
        model_name: str,
        add_searchable: Q = None
) -> JsonResponse:
    search_query = Q()
    search_value = request.GET.get("search[value]", None)
    if search_value:
        search_query = (
                model.get_query_name(search_value) |
                model.get_parent_query(search_value) |
                model.get_created_by_query(search_value) |
                Q(created_at__icontains=search_value) |
                Q(updated_at__icontains=search_value)
        )
        if add_searchable:
            search_query = search_query | add_searchable
    entries = model.objects.all()

    return paginated_table(
        request, entries,
        serializer, sort_by_func,
        model_name, search_query
    )


def __create_catalog__(
        form: forms.ModelForm,
        user: User,
        request: HttpRequest = None
) -> int:
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
            FinderView.refresh_view()
            SynonymyView.refresh_view()
            RegionDistributionView.refresh_view()
            return new_model.id
        except Exception as e:
            logging.error(e, exc_info=True)
            return -1
    else:
        return -1


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
            FinderView.refresh_view()
            SynonymyView.refresh_view()
            RegionDistributionView.refresh_view()
            return True
        except Exception as e:
            logging.error(e, exc_info=True)
            return False
    else:
        logging.warning("Error on {}: {}".format(
            form.instance,
            form.errors.as_data()
        ))
        return False


def __delete_catalog__(model: TaxonomicModel, user: User):
    Binnacle.delete_entry(model, user)
    CatalogView.refresh_view()
    FinderView.refresh_view()
    SynonymyView.refresh_view()
    RegionDistributionView.refresh_view()
    return


def __create_catalog_route__(
        request: HttpRequest,
        form_class: Type[forms.ModelForm],
        model_name: str,
        rank_title: str,
) -> HttpResponse:
    if request.method == "POST":
        form = form_class(request.POST)
        if __create_catalog__(form, request.user) != -1:
            return redirect("list_{}".format(model_name))
    else:
        form = form_class()
    return render(request, "catalog/create_catalog.html", {
        "rank_title": rank_title,
        "create_rank_url": reverse("create_{}".format(model_name)),
        "form": form,
        "list_url": reverse("list_{}".format(model_name))
    })


def __update_catalog_route__(
        request: HttpRequest,
        model: Type[TaxonomicModel],
        form_class: Type[forms.ModelForm],
        model_name: str,
        rank_title: str,
        identifier: int
) -> HttpResponse:
    entry = model.objects.get(unique_taxon_id=identifier)
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
        "form": form,
        "list_url": reverse("list_{}".format(model_name))
    })


@login_required
def list_division(request):
    return render(request, "catalog/list_catalog.html", {
        "table_url": reverse("division_table"),
        "rank_name": "name",
        "parent_rank": "kingdom",
        "update_rank_url": reverse("update_division", kwargs={"division_id": 0}),
        "rank_title": _("Division"),
        "create_rank_url": reverse("create_division"),
        "rank_name_title": _("Name"),
        "parent_rank_title": _("Kingdom"),
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
        "division", _("Division"),
    )


@login_required
def update_division(request, division_id):
    return __update_catalog_route__(
        request, Division, DivisionForm,
        "division", _("Division"),
        division_id
    )


@login_required
def list_class(request):
    return render(request, "catalog/list_catalog.html", {
        "table_url": reverse("class_table"),
        "rank_name": "name",
        "parent_rank": "division",
        "update_rank_url": reverse("update_class", kwargs={"class_id": 0}),
        "rank_title": _("Class"),
        "create_rank_url": reverse("create_class"),
        "rank_name_title": _("Name"),
        "parent_rank_title": _("Division"),
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
        "class", _("Class"),
    )


@login_required
def update_class(request, class_id):
    return __update_catalog_route__(
        request, ClassName, ClassForm,
        "class", _("Class"),
        class_id
    )


@login_required
def list_order(request):
    return render(request, "catalog/list_catalog.html", {
        "table_url": reverse("order_table"),
        "rank_name": "name",
        "parent_rank": "classname",
        "update_rank_url": reverse("update_order", kwargs={"order_id": 0}),
        "rank_title": _("Order"),
        "rank_name_title": _("Name"),
        "create_rank_url": reverse("create_order"),
        "parent_rank_title": _("Class"),
        "deletable": 0,
    })


@login_required
def order_table(request):
    sort_by_func = {
        0: "name",
        1: "classname__name",
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
        "order", _("Order"),
    )


@login_required
def update_order(request, order_id):
    return __update_catalog_route__(
        request, Order, OrderForm,
        "order", _("Order"),
        order_id
    )


@login_required
def list_family(request):
    return render(request, "catalog/list_catalog.html", {
        "table_url": reverse("family_table"),
        "rank_name": "name",
        "parent_rank": "order",
        "update_rank_url": reverse("update_family", kwargs={"family_id": 0}),
        "rank_title": _("Family"),
        "rank_name_title": _("Name"),
        "create_rank_url": reverse("create_family"),
        "parent_rank_title": _("Order"),
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
        "family", _("Family"),
    )


@login_required
def update_family(request, family_id):
    return __update_catalog_route__(
        request, Family, FamilyForm,
        "family", _("Family"),
        family_id
    )


@login_required
def list_genus(request):
    return render(request, "catalog/list_catalog.html", {
        "table_url": reverse("genus_table"),
        "rank_name": "name",
        "parent_rank": "family",
        "update_rank_url": reverse("update_genus", kwargs={"genus_id": 0}),
        "rank_title": _("Genus"),
        "rank_name_title": _("Name"),
        "create_rank_url": reverse("create_genus"),
        "parent_rank_title": _("Family"),
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
        "genus", _("Genus"),
    )


@login_required
def update_genus(request, genus_id):
    return __update_catalog_route__(
        request, Genus, GenusForm,
        "genus", _("Genus"),
        genus_id
    )


@login_required
def list_taxa(request):
    return render(request, "catalog/list_taxa.html")


@login_required
def taxa_table(request):
    sort_by_func = {
        0: "division",
        1: "classname",
        2: "order",
        3: "family",
        4: "scientific_name_full",
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
                Q(classname__icontains=search_value) |
                Q(order__icontains=search_value) |
                Q(family__icontains=search_value) |
                Q(status__icontains=search_value) |
                Q(determined__icontains=search_value)
        )
    )


@login_required
def create_taxa(request):
    if request.method == "POST":
        form = SpeciesForm(request.POST)
        if __create_catalog__(form, request.user, request=request) != -1:
            return redirect("list_taxa")
    else:
        form = SpeciesForm()
    return render(request, "catalog/create_taxa.html", {
        "form": form,
        "form_url": reverse("create_taxa")
    })


@login_required
def update_taxa(request, species_id):
    species = Species.objects.get(unique_taxon_id=species_id)
    warnings = False
    warning_text = ""
    gallery_warning = species.galleryimage_set.exists()
    voucher_warning = species.voucherimported_set.exists()
    synonymy_warning = species.synonyms.exists()
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
        "form_url": reverse("update_taxa", kwargs={"species_id": species_id}),
        "id": species_id,
        "species_name": species.scientific_name_full,
        "warnings": warnings,
        "warning_text": warning_text,
    })


def delete_taxa(request, species_id):
    species = Species.objects.get(unique_taxon_id=species_id)
    name = species.scientific_name_full
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
        FinderView.refresh_view()
        SynonymyView.refresh_view()
        RegionDistributionView.refresh_view()
    except Exception as e:
        logging.error("Error deleting species {}:{}".format(
            species_id, name
        ))
        logging.error(e, exc_info=True)
    return redirect("list_taxa")


@login_required
def select_taxa(request, species_id: int) -> HttpResponse:
    taxa_1 = Species.objects.get(unique_taxon_id=species_id)
    species = Species.objects.all()
    form = SpeciesForm(instance=taxa_1)
    return render(request, "catalog/merge_taxa.html", {
        "form": form, "species": species,
        "taxa_1": SpeciesSerializer(
            instance=taxa_1,
            many=False,
            context=request
        ).data,
        "form_url": reverse("update_taxa", kwargs={"species_id": species_id}),
    })


@login_required
def merge_taxa(request, taxa_1: int, taxa_2: int) -> HttpResponse:
    species_1 = Species.objects.get(unique_taxon_id=taxa_1)
    species_2 = Species.objects.get(unique_taxon_id=taxa_2)
    species = Species.objects.all()
    if request.method == "POST":
        form = SpeciesForm(request.POST, instance=species_2)
        updated = __update_catalog__(form, request.user, request=request)
        if updated:
            new_synonymy = Synonymy(species=species_1)
            new_synonymy.save(user=request.user)
            species_2.synonyms.add(new_synonymy)
            logging.info(f"Assigning voucher for {species_1}")
            for voucher in species_1.voucherimported_set.all():
                voucher.scientific_name = species_2
                voucher.save()
                logging.info(f"Re-generating etiquette for {voucher.biodata_code.code}")
                voucher.generate_etiquette()
            Binnacle.delete_entry(species_1, request.user)
            CatalogView.refresh_view()
            FinderView.refresh_view()
            SynonymyView.refresh_view()
            RegionDistributionView.refresh_view()
            return redirect("list_taxa")
    else:
        form = SpeciesForm(instance=species_2)
        for relation_name, _, many_relation in MANY_RELATIONS:
            new_relations = many_relation.objects.filter(
                Q(species=species_1) | Q(species=species_2)
            ).distinct()
            logging.debug(f"Relation {relation_name} set to {new_relations}")
            form.initial[relation_name] = [new_relation.id for new_relation in new_relations]
        if species_1.minimum_height is not None:
            if species_2.minimum_height is None:
                form.initial["minimum_height"] = species_1.minimum_height
            else:
                form.initial["minimum_height"] = min(species_1.minimum_height, species_2.minimum_height)
        if species_1.maximum_height is not None:
            if species_2.maximum_height is None:
                form.initial["maximum_height"] = species_1.maximum_height
            else:
                form.initial["maximum_height"] = max(species_1.maximum_height, species_2.maximum_height)
        form.initial["in_argentina"] = species_1.in_argentina or species_2.in_argentina
        form.initial["in_bolivia"] = species_1.in_bolivia or species_2.in_bolivia
        form.initial["in_peru"] = species_1.in_peru or species_2.in_peru
        if species_1.determined:
            form.initial["determined"] = True
        if species_2.id_mma is None and species_1.id_mma is None:
            form.initial["id_mma"] = species_1.id_mma
    return render(request, "catalog/merge_taxa.html", {
        "form": form,
        "taxa_1": SpeciesSerializer(
            instance=species_1,
            many=False,
            context=request
        ).data,
        "taxa_2": SpeciesSerializer(
            instance=species_2,
            many=False,
            context=request
        ).data,
        "species": species,
        "form_url": reverse("merge_taxa", kwargs={"taxa_1": taxa_1, "taxa_2": taxa_2}),
    })


@login_required
def list_synonymy(request):
    return render(request, "catalog/list_catalog.html", {
        "table_url": reverse("synonymy_table"),
        "rank_name": "scientific_name_full",
        "parent_rank": "species",
        "update_rank_url": reverse("update_synonymy", kwargs={"synonymy_id": 0}),
        "rank_title": _("Synonyms"),
        "rank_name_title": _("Complete Scientific Name"),
        "create_rank_url": reverse("create_synonymy"),
        "parent_rank_title": _("Species"),
        "deletable": 1,
    })


@login_required
def synonymy_table(request):
    sort_by_func = {
        0: "scientific_name_full",
        1: "species",
        2: "created_by__username",
        3: "created_at",
        4: "updated_at",
    }
    return __catalog_table__(
        request, Synonymy, SynonymsSerializer,
        sort_by_func, "synonyms"
    )


@login_required
def create_synonymy(request):
    return __create_catalog_route__(
        request, SynonymyForm,
        "synonymy", _("Synonymy"),
    )


@login_required
def update_synonymy(request, synonymy_id):
    return __update_catalog_route__(
        request, Synonymy, SynonymyForm,
        "synonymy", _("Synonymy"),
        synonymy_id
    )


@login_required
def delete_synonymy(request, synonymy_id):
    synonymy = Synonymy.objects.get(unique_taxon_id=synonymy_id)
    try:
        __delete_catalog__(synonymy, request.user)
        return redirect("list_synonymy")
    except Exception as e:
        logging.error(e, exc_info=True)
        return HttpResponseServerError()


@login_required
def list_binnacle(request):
    return render(request, "catalog/list_binnacle.html")


@login_required
def binnacle_table(request):
    binnacles = Binnacle.objects.all()
    search_query = Q()
    search_value = request.GET.get("search[value]", None)
    if search_value:
        search_query = (
                Q(type_update__icontains=search_value) |
                Q(model__icontains=search_value) |
                Q(description__icontains=search_value) |
                Q(note__icontains=search_value) |
                Q(created_by__username__icontains=search_value) |
                Q(created_at__icontains=search_value) |
                Q(updated_at__icontains=search_value)
        )
    sort_by_func = {
        0: 'type_update',
        1: 'model',
        2: 'description',
        3: 'note',
        4: 'created_by__username',
        5: 'created_at',
        6: 'updated_at',
    }
    return paginated_table(
        request, binnacles, BinnacleSerializer,
        sort_by_func, 'binnacle', search_query
    )


@login_required
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
    return render(request, "catalog/list_common_name.html", {
        "table_url": reverse("common_name_table"),
        "rank_name": "name",
        "parent_rank": "species",
        "update_rank_url": reverse("update_common_name", kwargs={"common_name_id": 0}),
        "rank_title": _("Common Name"),
        "rank_name_title": _("Name"),
        "create_rank_url": reverse("create_common_name"),
        "parent_rank_title": _("Species"),
        "deletable": 1,
    })


@login_required
def common_name_table(request):
    sort_by_func = {
        0: "name",
        1: "species__scientific_name",
        2: "created_by__username",
        3: "created_at",
        4: "updated_at",
    }
    return __catalog_table__(
        request, CommonName, CommonNameSerializer,
        sort_by_func, "common name"
    )


@login_required
def create_common_name(request):
    return __create_catalog_route__(
        request, CommonNameForm,
        "common_name", _("Common Name"),
    )


@login_required
def update_common_name(request, common_name_id):
    entry = CommonName.objects.get(id=common_name_id)
    if request.method == "POST":
        form = CommonNameForm(request.POST, instance=entry)
        if __update_catalog__(form, request.user):
            return redirect("list_common_name")
    else:
        form = CommonNameForm(instance=entry)
    return render(request, "catalog/update_catalog.html", {
        "rank_title": _("Common Name"),
        "id": common_name_id,
        "update_url": reverse(
            "update_common_name",
            kwargs={
                "common_name_id": common_name_id
            }
        ),
        "form": form,
        "list_url": reverse("list_common_name")
    })


@login_required
def delete_common_name(request, common_name_id):
    common_name = CommonName.objects.get(id=common_name_id)
    try:
        __delete_catalog__(common_name, request.user)
        return redirect("list_common_name")
    except Exception as e:
        logging.error(e, exc_info=True)
        return HttpResponseServerError


@login_required
def reload_scientific_name(request):
    os.makedirs("scientific_name_log", exist_ok=True)
    logger = TaskProcessLogger("Reload scientific Name", "scientific_name_log")
    logger.info("Reloading Scientific Name")
    for species in list(Species.objects.all()) + list(Synonymy.objects.all()):
        prev = (
            species.scientific_name_full,
            species.scientific_name_db,
            species.scientific_name
        )
        species.__update_scientific_name__()
        if species.scientific_name_full != prev[0]:
            logger.debug(f"({species.pk}) Scientific Name Full changes:")
            logger.debug(species.scientific_name_full)
            logger.debug(prev[0])
        if species.scientific_name_db != prev[1]:
            logger.debug(f"({species.pk}) Scientific Name DB:")
            logger.debug(species.scientific_name_db)
            logger.debug(prev[1])
        if species.scientific_name != prev[2]:
            logger.debug(f"({species.pk}) Scientific Name changes:")
            logger.debug(species.scientific_name)
            logger.debug(prev[2])
        species.save(force_update=True)
    logger.close()
    logger.save_file(PrivateMediaStorage(), "reload_scientific_name.log")
    import shutil
    shutil.rmtree("scientific_name_log")
    return redirect("index")
