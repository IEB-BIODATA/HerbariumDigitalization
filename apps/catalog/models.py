from __future__ import annotations

import logging
import dwca.terms as dwc
import dwca.classes as dwc_classes
from abc import abstractmethod, ABC
from copy import deepcopy

import pandas as pd
from celery.app.task import Task
from celery.result import AsyncResult
from django.conf import settings
from django.contrib.auth.models import User
from django.contrib.contenttypes.fields import GenericForeignKey
from django.contrib.contenttypes.models import ContentType
from django.contrib.gis.db.models import GeometryField
from django.contrib.postgres.search import TrigramSimilarity
from django.core.exceptions import ObjectDoesNotExist
from django.db import connection
from django.db import models
from django.db.models import Q
from django.utils.translation import gettext_lazy as _, pgettext_lazy, pgettext
from time import time_ns, time
from typing import List, Dict, Tuple

from intranet.utils import CatalogQuerySet

ATTRIBUTES = [
    "plant_habit", "env_habit",
    "status", "cycle",
    "region", "conservation_status",
    "common_names",
]

TAXONOMIC_RANK = [
    "kingdom", "division", "classname", "order",
    "family", "genus", "species",
]

FORMAT_CHOICES = [
    (0, "csv"), (1, "xlsx"), (2, "tsv")
]


CATALOG_DWC_FIELDS = [
    dwc.TaxonID(0), dwc.ParentNameUsageID(1), dwc.AcceptedNameUsageID(2),
    dwc.OriginalNameUsageID(3), dwc.ScientificNameID(4), dwc.DWCDataset(5),
    dwc.TaxonomicStatus(6), dwc.TaxonRank(7), dwc.TaxonRemarks(8), dwc.ScientificName(9),
    dwc.HigherClassification(10), dwc.Kingdom(11), dwc.Phylum(12), dwc.DWCClass(13), dwc.Order(14), dwc.Family(15), dwc.Genus(16),
    dwc.GenericName(17), dwc.InfragenericEpithet(18), dwc.SpecificEpithet(19),
    dwc.InfraspecificEpithet(20), dwc.ScientificNameAuthorship(21),
    dwc.NameAccordingTo(22), dwc.NamePublishedIn(23),
    dwc.NomenclaturalCode(24), dwc.NomenclaturalStatus(25),
    dwc.DWCModified(26), dwc.DWCInstitution(27), dwc.DWCInstitutionCode(28),
    dwc.DWCDatasetName(29)
]


class VernacularName(dwc_classes.DataFile):
    URI = "http://rs.gbif.org/terms/1.0/VernacularName"
    def __init__(self, _id: int, files: str, fields: List[dwc.Field]):
        super().__init__(
            _id, files, fields, dwc_classes.DataFileType.EXTENSION,
            "utf-8", "\n", "\t",
            "", 1
        )
        return


class Reference(dwc_classes.DataFile):
    URI = "http://rs.gbif.org/terms/1.0/Reference"
    def __init__(self, _id: int, files: str, fields: List[dwc.Field]):
        super().__init__(
            _id, files, fields, dwc_classes.DataFileType.EXTENSION,
            "utf-8", "\n", "\t",
            "", 1
        )
        return


class MinimumHeight(dwc.Field):
    URI = f"{settings.HERBARIUM_FRONTEND}/herbarium-namespace#minimumHeight"
    TYPE = float

    def __init__(self, index: int | str, default: TYPE = None, vocabulary: str = None) -> None:
        super().__init__(index, default, vocabulary)
        return

    @classmethod
    def name_cls(cls) -> str:
        return "minimumHeight"

    @property
    def name(self) -> str:
        return "minimumHeight"


class MaximumHeight(dwc.Field):
    URI = f"{settings.HERBARIUM_FRONTEND}/herbarium-namespace#maximumHeight"
    TYPE = float

    def __init__(self, index: int | str, default: TYPE = None, vocabulary: str = None) -> None:
        super().__init__(index, default, vocabulary)
        return

    @classmethod
    def name_cls(cls) -> str:
        return "maximumHeight"

    @property
    def name(self) -> str:
        return "maximumHeight"


class AttributeQuerySet(CatalogQuerySet, ABC):
    __attribute_name__ = "query"

    @staticmethod
    def species_filter():
        return "species"

    def filter_for_species(self, query: Q) -> AttributeQuerySet:
        return self.filter(query).distinct()

    def filter_query(self, **parameters: Dict[str, List[str]]) -> AttributeQuerySet:
        start = time_ns()
        query = Q()
        for query_key, parameter in parameters.items():
            if query_key == self.__attribute_name__:
                continue
            particular_query = Q()
            for par in parameter:
                if par.isdigit():
                    particular_query |= Q(**{f"species__{query_key}": par})
                else:
                    particular_query |= Q(**{f"species__{query_key}__key": par})
            query &= particular_query
        queryset = self.filter(query).distinct()
        logging.debug(f"{self.__attribute_name__}: {query} and got {queryset}")
        logging.debug(f"Query: {queryset.query}")
        logging.debug(
            f"Filtering {self.__attribute_name__} using attributes took {(time_ns() - start) / 1e6:.2f} milliseconds"
        )
        return queryset

    def filter_taxonomy(self, **parameters: Dict[str: List[str]]) -> AttributeQuerySet:
        start = time_ns()
        query = Q()
        for taxonomic_rank, parameter in parameters.items():
            clean_parameters = list()
            for par in parameter:
                if par.isdigit():
                    clean_parameters.append(RANK_MODELS[taxonomic_rank].objects.get(unique_taxon_id=par).pk)
                else:
                    clean_parameters.append(get_fuzzy_taxa(taxonomic_rank, par))
            logging.debug(f"{self.__attribute_name__}: Species from {taxonomic_rank}: {clean_parameters}")
            species = CatalogView.objects.filter(**{f"{taxonomic_rank}_id__in": clean_parameters})
            query &= Q(**{f"{self.species_filter()}__in": Species.objects.filter(pk__in=species)})
        queryset = self.filter_for_species(query)
        logging.debug(
            f"Filtering {self.__attribute_name__} using taxonomies took {(time_ns() - start) / 1e6:.2f} milliseconds"
        )
        logging.debug(f"Query: {queryset.query}")
        return queryset

    def filter_geometry(self, geometries: List[str]) -> AttributeQuerySet:
        start = time_ns()
        query = Q()
        for geometry in geometries:
            query |= Q(species__voucherimported__point__within=geometry)
        queryset = self.filter(query).distinct()
        logging.debug(f"{self.__attribute_name__}: {query} and got {queryset}")
        logging.debug(
            f"Filtering {self.__attribute_name__} using geometry took {(time_ns() - start) / 1e6:.2f} milliseconds"
        )
        return queryset

    def search(self, text: str) -> AttributeQuerySet:
        return self.filter(name__icontains=text)


class TaxonomicQuerySet(CatalogQuerySet, ABC):
    __rank_name__ = "taxonomy"

    def __init__(self, model=None, query=None, using=None, hints=None):
        super(TaxonomicQuerySet, self).__init__(model, query, using, hints)
        self.__rank_index__ = TAXONOMIC_RANK.index(self.__rank_name__)
        return

    def filter_query(self, **parameters: Dict[str, List[str]]) -> TaxonomicQuerySet:
        start = time_ns()
        query = Q()
        rank_index = TAXONOMIC_RANK.index(self.__rank_name__)
        for query_key, parameter in parameters.items():
            query_name = "__".join(TAXONOMIC_RANK[rank_index + 1:])
            if query_name != "":
                query_name = f"{query_name}__"
            particular_query = Q()
            for par in parameter:
                if par.isdigit():
                    particular_query |= Q(**{f"{query_name}{query_key}": par})
                else:
                    particular_query |= Q(**{f"{query_name}{query_key}__key": par})
            query &= particular_query
        queryset = self.filter(query).distinct()
        logging.debug(f"{self.__rank_name__}: {query} and got {queryset}")
        logging.debug(f"Query: {queryset.query}")
        logging.debug(
            f"Filtering {self.__rank_name__} using attributes took {(time_ns() - start) / 1e6:.2f} milliseconds"
        )
        return queryset

    def get_taxonomic_query(self, taxonomic_rank: str) -> str:
        rank_index = TAXONOMIC_RANK.index(taxonomic_rank)
        if self.__rank_index__ < rank_index:
            return "__".join(TAXONOMIC_RANK[self.__rank_index__ + 1: rank_index + 1]) + "__in"
        elif self.__rank_index__ > rank_index:
            return "__".join(reversed(TAXONOMIC_RANK[rank_index: self.__rank_index__])) + "__in"
        else:
            raise RuntimeError

    def filter_taxonomy(self, **parameters: Dict[str: List[str]]) -> TaxonomicQuerySet:
        start = time_ns()
        query = Q()
        for taxonomic_rank, parameter in parameters.items():
            clean_parameters = list()
            for par in parameter:
                if par.isdigit():
                    clean_parameters.append(RANK_MODELS[taxonomic_rank].objects.get(unique_taxon_id=par).pk)
                else:
                    clean_parameters.append(get_fuzzy_taxa(taxonomic_rank, par))
            try:
                query &= Q(**{self.get_taxonomic_query(taxonomic_rank): clean_parameters})
            except RuntimeError:
                continue
        queryset = self.filter(query).distinct()
        logging.debug(f"{self.__rank_name__}: {query} and got {queryset}")
        logging.debug(f"Query: {queryset.query}")
        logging.debug(
            f"Filtering {self.__rank_name__} using taxonomies took {(time_ns() - start) / 1e6:.2f} milliseconds"
        )
        return queryset

    def filter_geometry(self, geometries: List[str]) -> TaxonomicQuerySet:
        start = time_ns()
        rank_index = TAXONOMIC_RANK.index(self.__rank_name__)
        query_name = "__".join(TAXONOMIC_RANK[rank_index + 1:])
        if query_name != "":
            query_name = f"{query_name}__"
        query = Q()
        for geometry in geometries:
            query |= Q(**{f"{query_name}voucherimported__point__within": geometry})
        queryset = self.filter(query).distinct()
        logging.debug(f"{self.__rank_name__}: {query} and got {queryset}")
        logging.debug(
            f"Filtering {self.__rank_name__} using geometries took {(time_ns() - start) / 1e6:.2f} milliseconds"
        )
        return queryset

    def search(self, text: str) -> TaxonomicQuerySet:
        return self.filter(self.model.get_query_name(text))


class AttributeModel(models.Model):
    name = models.CharField(verbose_name=_("Name"), max_length=300, blank=True, null=True)
    created_at = models.DateTimeField(verbose_name=_("Created at"), auto_now_add=True, blank=True, null=True,
                                      editable=False)
    updated_at = models.DateTimeField(verbose_name=_("Updated at"), auto_now=True)
    created_by = models.ForeignKey(User, verbose_name=_("Created by"), on_delete=models.PROTECT, default=1,
                                   editable=False)

    class Meta:
        abstract = True


class StatusQuerySet(AttributeQuerySet):
    __attribute_name__ = "status"


class Status(AttributeModel):
    objects = StatusQuerySet.as_manager()

    def __unicode__(self):
        return u"%s" % self.name

    def __str__(self):
        return "%s" % self.name

    def __repr__(self):
        return "Status::%s" % self.name

    class Meta:
        verbose_name = _("Origin")
        verbose_name_plural = _("Origins")
        ordering = ['name']


class CycleQuerySet(AttributeQuerySet):
    __attribute_name__ = "cycle"


class Cycle(AttributeModel):
    objects = CycleQuerySet.as_manager()

    def __unicode__(self):
        return u"%s" % self.name

    def __str__(self):
        return "%s" % self.name

    def __repr__(self):
        return "Cycle::%s" % self.name

    class Meta:
        verbose_name = _("Cycle")
        verbose_name_plural = _("Cycles")
        ordering = ['name']


class PlantHabitQuerySet(AttributeQuerySet):
    __attribute_name__ = "plant_habit"


class PlantHabit(AttributeModel):
    objects = PlantHabitQuerySet.as_manager()

    def __unicode__(self):
        return u"%s" % self.name

    def __str__(self):
        return "%s" % self.name

    def __repr__(self):
        return "Plant Habit::%s" % self.name

    class Meta:
        verbose_name = _("Plant Habit")
        verbose_name_plural = _("Plant Habits")
        ordering = ['name']


class EnvironmentalHabitQuerySet(AttributeQuerySet):
    __attribute_name__ = "env_habit"


class EnvironmentalHabit(AttributeModel):
    objects = EnvironmentalHabitQuerySet.as_manager()

    def __unicode__(self):
        return u"%s" % self.__str__()

    def __str__(self):
        return "%s" % self.name

    def __repr__(self):
        return "Environmental Habit::%s" % self.__str__()

    class Meta:
        verbose_name = _("Environmental Habit")
        verbose_name_plural = _("Environmental Habits")
        ordering = ['name']


class Habit(AttributeModel):
    plant_habit = models.ForeignKey(PlantHabit, on_delete=models.CASCADE)
    env_habit = models.ForeignKey(EnvironmentalHabit, on_delete=models.CASCADE)

    def __unicode__(self):
        return u"%s" % self.__str__()

    def __str__(self):
        return "%s" % self.name

    def __repr__(self):
        return "Habit::%s" % self.__str__()

    def natural_key(self) -> Tuple[models.ForeignKey, models.ForeignKey]:
        return self.plant_habit.primary_key, self.env_habit.primary_key

    class Meta:
        verbose_name_plural = _("Habits")
        ordering = ['plant_habit', 'env_habit']
        constraints = [
            models.UniqueConstraint(fields=['plant_habit', 'env_habit'], name='unique habit')
        ]


class TaxonRankQuerySet(AttributeQuerySet):
    __attribute_name__ = "taxon_rank"


class TaxonRank(AttributeModel):
    objects = TaxonRankQuerySet.as_manager()

    def __unicode__(self):
        return u"%s" % self.__str__()

    def __str__(self):
        return "%s" % self.name

    def __repr__(self):
        return "Taxon Rank::%s" % self.__str__()

    class Meta:
        verbose_name = _("Taxon Rank")
        verbose_name_plural = _("Taxon Rank")
        ordering = ['name']


class RegionQuerySet(AttributeQuerySet):
    __attribute_name__ = "region"

    def filter_taxonomy(self, **parameters: Dict[str: List[str]]) -> AttributeQuerySet:
        start = time_ns()
        query = Q()
        for taxonomic_rank, parameter in parameters.items():
            clean_parameters = list()
            for par in parameter:
                if par.isdigit():
                    clean_parameters.append(RANK_MODELS[taxonomic_rank].objects.get(unique_taxon_id=par).pk)
                else:
                    clean_parameters.append(get_fuzzy_taxa(taxonomic_rank, par))
            logging.debug(f"{self.__attribute_name__}: Species from {taxonomic_rank}: {clean_parameters}")
            species = CatalogView.objects.filter(**{f"{taxonomic_rank}_id__in": clean_parameters})
            regions = RegionDistributionView.objects.filter(
                Q(species_id__in=[sp.id for sp in species])
            ).distinct('region_key')
            query &= Q(**{f"key__in": [reg.region_key for reg in regions]})
        queryset = self.filter_for_species(query)
        logging.debug(
            f"Filtering {self.__attribute_name__} using taxonomies took {(time_ns() - start) / 1e6:.2f} milliseconds"
        )
        logging.debug(f"Query: {queryset.query}")
        return queryset

    def filter_geometry(self, geometries: List[str]) -> TaxonomicQuerySet:
        start = time_ns()
        query = Q()
        for geometry in geometries:
            query |= Q(geometry__intersects=geometry)
        queryset = self.filter(query).distinct()
        logging.debug(f"{self.__attribute_name__}: {query} and got {queryset}")
        logging.debug(
            f"Filtering {self.__attribute_name__} using geometries took {(time_ns() - start) / 1e6:.2f} milliseconds"
        )
        return queryset


class Region(AttributeModel):
    key = models.CharField(verbose_name=_("Key"), max_length=3, blank=True, null=True)
    order = models.IntegerField(verbose_name=pgettext_lazy("ordering", "Order"), blank=True, null=True,
                                db_column="order")
    geometry = GeometryField(verbose_name=_("Geometry"), dim=2, blank=True, null=True)

    objects = RegionQuerySet.as_manager()

    def __unicode__(self):
        return u"%s" % self.name

    def __str__(self):
        return "%s " % self.name

    def __repr__(self):
        return "Region::%s" % self.name

    class Meta:
        verbose_name = _('Region')
        verbose_name_plural = _("Regions")
        ordering = ['order']


class ConservationStatusQuerySet(AttributeQuerySet):
    __attribute_name__ = "conservation_status"

    def filter_taxonomy(self, **parameters: Dict[str: List[str]]) -> AttributeQuerySet:
        start = time_ns()
        query = Q()
        for taxonomic_rank, parameter in parameters.items():
            clean_parameters = list()
            for par in parameter:
                if par.isdigit():
                    clean_parameters.append(RANK_MODELS[taxonomic_rank].objects.get(unique_taxon_id=par).pk)
                else:
                    clean_parameters.append(get_fuzzy_taxa(taxonomic_rank, par))
            logging.debug(f"{self.__attribute_name__}: Species from {taxonomic_rank}: {clean_parameters}")
            species_view = CatalogView.objects.filter(**{f"{taxonomic_rank}_id__in": clean_parameters})
            species = Species.objects.filter(id__in=[sp.id for sp in species_view]).prefetch_related(
                "conservation_status"
            )
            query &= Q(**{f"species__in": [sp.id for sp in species]})
        queryset = self.filter_for_species(query)
        logging.debug(
            f"Filtering {self.__attribute_name__} using taxonomies took {(time_ns() - start) / 1e6:.2f} milliseconds"
        )
        logging.debug(f"Query: {queryset.query}")
        return queryset


class ConservationStatus(AttributeModel):
    key = models.CharField(verbose_name=_("Key"), max_length=3, blank=True, null=True)
    order = models.IntegerField(verbose_name=pgettext_lazy("ordering", "Order"), blank=True, null=True, db_column="order")

    objects = ConservationStatusQuerySet.as_manager()

    def __unicode__(self):
        return u"%s" % self.name

    def __str__(self):
        return f"{self.name} ({self.key})"

    def __repr__(self):
        return "Conservation Status::%s" % self.name

    class Meta:
        verbose_name = _("State of Conservation")
        verbose_name_plural = _("Conservation Status")
        ordering = ['order']


class Author(models.Model):
    first_name = models.CharField(verbose_name=_("First name"), max_length=255)
    last_name = models.CharField(verbose_name=_("Last name"), max_length=255, blank=True, null=True)

    def __str__(self):
        if self.last_name is not None:
            return f"{self.last_name}, {self.first_name[0]}."
        else:
            return f"{self.first_name}"



class References(models.Model):
    author = models.ManyToManyField(Author, verbose_name=_("Author"))
    title = models.TextField(verbose_name=_("Title"), blank=True, null=True)
    journal = models.CharField(verbose_name=_("Journal"), max_length=300, blank=True, null=True)
    volume = models.IntegerField(verbose_name=_("Volume"), blank=True, null=True)
    issue = models.IntegerField(verbose_name=_("Issue"), blank=True, null=True)
    first_page = models.IntegerField(verbose_name=_("First Page"), blank=True, null=True)
    last_page = models.IntegerField(verbose_name=_("Last Page"), blank=True, null=True)
    year = models.IntegerField(verbose_name=_("Year"), blank=True, null=True)

    def __str__(self) -> str:
        return self.cite()

    def cite(self) -> str:
        authors = self.author.all()
        if len(authors) >= 3:
            authors_str = f"{authors[0]}, et al."
        else:
            authors_str = ", ".join([str(a) for a in authors])
        if self.issue is not None:
            if self.volume is not None:
                issue_str = f" {self.volume} ({self.issue}),"
            else:
                issue_str = f" {self.issue},"
        else:
            if self.volume is not None:
                issue_str = f" {self.volume},"
            else:
                issue_str = f""
        if self.first_page is not None:
            if self.last_page is not None:
                page_str = f" {self.first_page}-{self.last_page}"
            else:
                page_str = f" {self.first_page}"
        else:
            page_str = ""
        if self.year is not None:
            year_str = f" ({self.year})"
        else:
            year_str = ""
        return f"{authors_str} {self.title}. {self.journal}{issue_str}{page_str}{year_str}."


class TaxonomicModel(models.Model):
    unique_taxon_id = models.BigIntegerField()
    taxon_id = models.CharField()
    created_at = models.DateTimeField(verbose_name=_("Created at"), auto_now_add=True, blank=True, null=True, editable=False)
    updated_at = models.DateTimeField(verbose_name=_("Updated at"), auto_now=True)
    created_by = models.ForeignKey(User, verbose_name=_("Created by"), on_delete=models.PROTECT, default=1, editable=False)
    references = models.ManyToManyField(References, verbose_name=_("References"), blank=True)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if self.pk is not None:
            self.__original__ = deepcopy(self)
        else:
            self.__original__ = None

    def __hash__(self):
        return super().__hash__()

    def __eq__(self, other: object):
        return isinstance(other, TaxonomicModel)

    def __ne__(self, other: object):
        return not self.__eq__(other)

    @staticmethod
    @abstractmethod
    def get_query_name(search: str) -> Q:
        return Q(name__icontains=search)

    @staticmethod
    @abstractmethod
    def get_parent_query(search: str) -> Q:
        pass

    @staticmethod
    @abstractmethod
    def get_created_by_query(search: str) -> Q:
        return Q(created_by__username__icontains=search)

    @property
    @abstractmethod
    def parent(self) -> TaxonomicModel | None:
        return None

    def get_higher_classification(self) -> List[str]:
        if self.parent is None:
            return list()
        else:
            return self.parent.get_higher_classification() + [self.parent.name]

    @classmethod
    def get_dwc_data(cls, logger: logging.Logger = logging.getLogger(__name__), task: Task = None):
        from ..metadata.models import EML
        eml = EML.objects.get(pk=1)
        objects = cls.objects.all()
        rank_name = objects.__rank_name__
        if rank_name == "classname":
            rank_name = "class"
        rows = list()
        logger.debug(f"Extracting data: {rank_name}")
        current_total = 0
        total = objects.count()
        if task is not None:
            async_result = AsyncResult(task.request.id)
            current_total = async_result.info["total"]
            total += current_total
            task.update_state(state="PROGRESS", meta={"step": current_total, "total": total, "logs": logger[0].get_logs()})
        for i, obj in enumerate(objects):
            if task is not None:
                task.update_state(state="PROGRESS", meta={"step": i + current_total, "total": total, "logs": logger[0].get_logs()})
            higher_classification = obj.get_higher_classification()
            complete_classification = higher_classification.copy()
            complete_classification.append(obj.name)
            while len(complete_classification) < 6:
                complete_classification.append(None)
            parent_id = None
            if obj.parent is not None:
                parent_id = obj.parent.taxon_id
            rows.append(
                [
                    obj.taxon_id, parent_id, obj.taxon_id,
                    obj.taxon_id, obj.taxon_id, eml.package_id,
                    "accepted", rank_name, "", obj.name,
                    obj.get_higher_classification()
                ] + complete_classification + [
                    None, None, None,
                    None, None,
                    None, None,
                    "ICBN", None,
                    obj.updated_at, "https://udec.cl", "UDEC",
                    eml.dataset.title,
                ]
            )
        return pd.DataFrame(rows, columns=[
            field.name for field in CATALOG_DWC_FIELDS
        ])

    def save(self, force_insert=False, force_update=False, using=None, update_fields=None, **kwargs):
        if force_update:
            return super().save(
                force_insert=force_insert,
                force_update=force_update,
                using=using,
                update_fields=update_fields,
            )
        if self.pk is None:
            try:
                if self.taxon_id is None or self.taxon_id == "":
                    with connection.cursor() as cursor:
                        cursor.execute("SELECT get_taxon_id()")
                        result = cursor.fetchone()
                        if result:
                            self.unique_taxon_id = result[0]
                            logging.debug(self.unique_taxon_id)
                        else:
                            raise RuntimeError("Cannot got unique taxa id")
                    self.taxon_id = settings.TAXA_ID_PREF + str(self.unique_taxon_id)
                super().save(
                    force_insert=force_insert,
                    force_update=force_update,
                    using=using,
                    update_fields=update_fields
                )
                Binnacle.new_entry(self, kwargs["user"], notes=kwargs.get("notes", None))
            except Exception as e:
                raise e
        elif self.__original__ != self:
            prev_entry = repr(self.__original__)
            self.__original__ = deepcopy(self)
            Binnacle.update_entry(prev_entry, self, kwargs["user"], notes=kwargs.get("notes", None))
            return super().save(
                force_insert=force_insert,
                force_update=force_update,
                using=using,
                update_fields=update_fields
            )
        else:
            logging.warning("Same value not saving")
            return

    class Meta:
        abstract = True


class KingdomQuerySet(TaxonomicQuerySet):
    __rank_name__ = "kingdom"


class Kingdom(TaxonomicModel):
    name = models.CharField(verbose_name=_("Name"), max_length=300, blank=True, null=True)

    objects = KingdomQuerySet.as_manager()

    def __hash__(self):
        return super().__hash__()

    def __eq__(self, other):
        return super().__eq__(other) and \
            self.name == other.name

    def __unicode__(self):
        return u"%s" % self.name

    def __str__(self):
        return "%s" % self.name

    def __repr__(self):
        return "%s" % self.name

    @staticmethod
    def get_query_name(search: str) -> Q:
        return TaxonomicModel.get_query_name(search)

    @staticmethod
    def get_parent_query(search: str) -> Q:
        raise NotImplementedError("Kingdom does not have a parent taxonomy")

    @staticmethod
    def get_created_by_query(search: str) -> Q:
        return TaxonomicModel.get_created_by_query(search)

    @property
    def parent(self) -> TaxonomicModel | None:
        return None

    class Meta:
        verbose_name = _("Kingdom")
        verbose_name_plural = _("Kingdoms")
        ordering = ['name']


class DivisionQuerySet(TaxonomicQuerySet):
    __rank_name__ = "division"


class Division(TaxonomicModel):
    name = models.CharField(verbose_name=_("Name"), max_length=300, blank=True, null=True)
    kingdom = models.ForeignKey(Kingdom, verbose_name=_("Kingdom"), on_delete=models.CASCADE, blank=True, null=True, help_text="Reino")

    objects = DivisionQuerySet.as_manager()

    def __hash__(self):
        return super().__hash__()

    def __eq__(self, other):
        return super().__eq__(other) and \
            self.kingdom == other.kingdom and \
            self.name == other.name

    def __unicode__(self):
        return u"%s" % self.name

    def __str__(self):
        return "%s" % self.name

    def __repr__(self):
        return "%s|Kingdom::%s" % (self.name, self.kingdom)

    @staticmethod
    def get_query_name(search: str) -> Q:
        return TaxonomicModel.get_query_name(search)

    @staticmethod
    def get_parent_query(search: str) -> Q:
        return Q(kingdom__name__icontains=search)

    @staticmethod
    def get_created_by_query(search: str) -> Q:
        return TaxonomicModel.get_created_by_query(search)

    @property
    def parent(self) -> TaxonomicModel | None:
        return self.kingdom

    class Meta:
        verbose_name_plural = _("Division")
        verbose_name_plural = _("Divisions")
        ordering = ['name']


class ClassQuerySet(TaxonomicQuerySet):
    __rank_name__ = "classname"


class ClassName(TaxonomicModel):
    name = models.CharField(verbose_name=_("Name"), max_length=300, blank=True, null=True)
    division = models.ForeignKey(Division, verbose_name=_("Division"), on_delete=models.CASCADE, blank=True, null=True)

    objects = ClassQuerySet.as_manager()

    def __hash__(self):
        return super().__hash__()

    def __eq__(self, other):
        return super().__eq__(other) and \
            self.division == other.division and \
            self.name == other.name

    def __unicode__(self):
        return u"%s" % self.name

    def __str__(self):
        return "%s" % self.name

    def __repr__(self):
        return "%s|Division::%s" % (self.name, self.division)

    @staticmethod
    def get_query_name(search: str) -> Q:
        return TaxonomicModel.get_query_name(search)

    @staticmethod
    def get_parent_query(search: str) -> Q:
        return Q(division__name__icontains=search)

    @staticmethod
    def get_created_by_query(search: str) -> Q:
        return TaxonomicModel.get_created_by_query(search)

    @property
    def parent(self) -> TaxonomicModel | None:
        return self.division

    class Meta:
        verbose_name = _("Class")
        verbose_name_plural = _("Classes")
        ordering = ['name']


class OrderQuerySet(TaxonomicQuerySet):
    __rank_name__ = "order"


class Order(TaxonomicModel):
    name = models.CharField(verbose_name=_("Name"), max_length=300, blank=True, null=True)
    classname = models.ForeignKey(ClassName, verbose_name=_("Class Name"), on_delete=models.CASCADE, blank=True, null=True, help_text="Clase")

    objects = OrderQuerySet.as_manager()

    def __hash__(self):
        return super().__hash__()

    def __eq__(self, other):
        return super().__eq__(other) and \
            self.classname == other.classname and \
            self.name == other.name

    def __unicode__(self):
        return u"%s" % self.name

    def __str__(self):
        return "%s" % self.name

    def __repr__(self):
        return "%s|Class::%s" % (self.name, self.classname)

    @staticmethod
    def get_query_name(search: str) -> Q:
        return TaxonomicModel.get_query_name(search)

    @staticmethod
    def get_parent_query(search: str) -> Q:
        return Q(classname__name__icontains=search)

    @staticmethod
    def get_created_by_query(search: str) -> Q:
        return TaxonomicModel.get_created_by_query(search)

    @property
    def parent(self) -> TaxonomicModel | None:
        return self.classname

    class Meta:
        verbose_name = _("Order")
        verbose_name_plural = _("Orders")
        ordering = ['name']


class FamilyQuerySet(TaxonomicQuerySet):
    __rank_name__ = "family"


class Family(TaxonomicModel):
    name = models.CharField(verbose_name=_("Name"), max_length=300, blank=True, null=True)
    order = models.ForeignKey(
        Order, verbose_name=_("Order"), on_delete=models.CASCADE, blank=True,
        null=True, help_text="order"
    )

    objects = FamilyQuerySet.as_manager()

    def __hash__(self):
        return super().__hash__()

    def __eq__(self, other):
        return super().__eq__(other) and \
            self.order == other.order and \
            self.name == other.name

    def __unicode__(self):
        return u"%s" % self.name

    def __str__(self):
        return "%s" % self.name

    def __repr__(self):
        return "%s|Order::%s" % (self.name, self.order)

    @staticmethod
    def get_query_name(search: str) -> Q:
        return TaxonomicModel.get_query_name(search)

    @staticmethod
    def get_parent_query(search: str) -> Q:
        return Q(order__name__icontains=search)

    @staticmethod
    def get_created_by_query(search: str) -> Q:
        return TaxonomicModel.get_created_by_query(search)

    @property
    def parent(self) -> TaxonomicModel | None:
        return self.order

    def save(self, force_insert=False, force_update=False, using=None, update_fields=None, **kwargs):
        if self.__original__ is not None and self.__original__.name != self.name:
            logging.debug("Name from {} to {}. Change etiquettes".format(
                self.__original__.name, self.name
            ))
            for genus in self.genus_set.all():
                for species in genus.species_set.all():
                    vouchers = species.voucherimported_set.all()
                    logging.debug("Vouchers on {} ({}): {}".format(
                        species.scientific_name_full, species.id, vouchers.count()
                    ))
                    for voucher in vouchers:
                        voucher.generate_etiquette()
        return super().save(
            force_insert=force_insert,
            force_update=force_update,
            using=using,
            update_fields=update_fields,
            **kwargs
        )

    class Meta:
        verbose_name = _("Family")
        verbose_name_plural = _("Families")
        ordering = ['name']


class GenusQuerySet(TaxonomicQuerySet):
    __rank_name__ = "genus"


class Genus(TaxonomicModel):
    name = models.CharField(verbose_name=_("Name"), max_length=300, blank=True, null=True)
    family = models.ForeignKey(Family, verbose_name=_("Family"), on_delete=models.CASCADE, blank=True, null=True, help_text="Familia")

    objects = GenusQuerySet.as_manager()

    def __hash__(self):
        return super().__hash__()

    def __eq__(self, other):
        return super().__eq__(other) and \
            self.family == other.family and \
            self.name == other.name

    def __unicode__(self):
        return u"%s" % self.name

    def __str__(self):
        return "%s" % self.name

    def __repr__(self):
        return "%s|Family::%s" % (self.name, self.family)

    @staticmethod
    def get_query_name(search: str) -> Q:
        return TaxonomicModel.get_query_name(search)

    @staticmethod
    def get_parent_query(search: str) -> Q:
        return Q(family__name__icontains=search)

    @staticmethod
    def get_created_by_query(search: str) -> Q:
        return TaxonomicModel.get_created_by_query(search)

    @property
    def parent(self) -> TaxonomicModel | None:
        return self.family

    def save(self, force_insert=False, force_update=False, using=None, update_fields=None, **kwargs):
        if self.__original__ is not None and self.__original__ != self:
            logging.debug("Genus from {} to {}. Changing species...".format(
                repr(self.__original__), repr(self)
            ))
            for species in self.species_set.all():
                if self.__original__.name != self.name:
                    species.save(
                        force_insert=force_insert,
                        force_update=force_update,
                        using=using,
                        update_fields=update_fields,
                        **kwargs
                    )
                else:
                    vouchers = species.voucherimported_set.all()
                    logging.debug("Vouchers on {} ({}): {}".format(
                        species.scientific_name_full, species.id, vouchers.count()
                    ))
                    for voucher in vouchers:
                        voucher.generate_etiquette()
        return super().save(
            force_insert=force_insert,
            force_update=force_update,
            using=using,
            update_fields=update_fields,
            **kwargs
        )

    class Meta:
        verbose_name = _("Genus")
        verbose_name_plural = _("Genera")
        ordering = ['name']


class ScientificName(TaxonomicModel):
    scientific_name = models.CharField(verbose_name=_("Scientific Name"), max_length=300, blank=True, null=True)
    scientific_name_db = models.CharField(
        verbose_name=_("Scientific Name Database"), max_length=300,
        blank=True, null=True
    )
    scientific_name_full = models.CharField(
        verbose_name=_("Complete Scientific Name"), max_length=800,
        blank=True, null=True
    )
    genus = models.CharField(verbose_name=_("Genus"), max_length=300, blank=True, null=True)
    specific_epithet = models.CharField(
        verbose_name=_("Specific Epithet"), max_length=300,
        blank=True, null=True, help_text="EpitetoEspecifico"
    )
    scientific_name_authorship = models.CharField(
        verbose_name=_("Scientific Name Authorship"), max_length=500,
        blank=True, null=True, help_text="AutoresSp"
    )
    subspecies = models.CharField(verbose_name=_("Subspecies"), max_length=300, blank=True, null=True)
    ssp_authorship = models.CharField(verbose_name=_("Subspecies Authorship"), max_length=500, blank=True, null=True)
    variety = models.CharField(verbose_name=_("Variety"), max_length=300, blank=True, null=True)
    variety_authorship = models.CharField(verbose_name=_("Variety Authorship"), max_length=500, blank=True, null=True)
    form = models.CharField(verbose_name=pgettext_lazy("taxonomic", "Form"), max_length=300, blank=True, null=True)
    form_authorship = models.CharField(verbose_name=_("Form Authorship"), max_length=500, blank=True, null=True)
    taxon_rank = models.ForeignKey(
        TaxonRank, verbose_name=_("Taxon Rank"),
        null=True, editable=False, on_delete=models.PROTECT
    )

    def __hash__(self):
        return super().__hash__()

    def __eq__(self, other):
        return super().__eq__(other) and \
            self.scientific_name == other.scientific_name and \
            self.scientific_name_db == other.scientific_name_db and \
            self.scientific_name_full == other.scientific_name_full

    def __unicode__(self):
        return u"%s" % self.scientific_name

    def __str__(self):
        return "%s" % self.scientific_name_full

    def __repr__(self):
        return "%s/%s" % (self.scientific_name, self.scientific_name_full)

    @staticmethod
    def get_query_name(search: str) -> Q:
        return Q(scientific_name_full__icontains=search)

    @staticmethod
    def get_parent_query(search: str) -> Q:
        return Q(species__scientific_name__icontains=search)

    @staticmethod
    def get_created_by_query(search: str) -> Q:
        return TaxonomicModel.get_created_by_query(search)

    @property
    @abstractmethod
    def parent(self) -> TaxonomicModel | None:
        pass

    @property
    def name(self) -> str:
        return self.scientific_name

    @property
    def dwc_scientific_name(self) -> str:
        sp_name = f"{self.genus} {self.specific_epithet}"
        if self.form is not None:
            return f"{sp_name} fma. {self.form}"
        if self.variety is not None:
            return f"{sp_name} var. {self.variety}"
        if self.subspecies is not None:
            return f"{sp_name} fma. {self.subspecies}"
        return sp_name

    @property
    def infraspecific_epithet(self) -> str | None:
        if self.form is not None:
            return self.form
        elif self.variety is not None:
            return self.variety
        elif self.subspecies is not None:
            return self.subspecies
        else:
            return None

    @property
    def authorship(self) -> str | None:
        if self.form_authorship is not None:
            return self.form_authorship
        elif self.variety_authorship is not None:
            return self.variety_authorship
        elif self.ssp_authorship is not None:
            return self.ssp_authorship
        else:
            return self.scientific_name_authorship

    def __update_scientific_name__(self):
        genus = str(self.genus).capitalize()
        self.scientific_name = "{genus} {epithet}{sub_ssp}{var}{fma}".format(
            genus=genus, epithet=self.specific_epithet,
            sub_ssp=" subsp. {}".format(self.subspecies) if self.subspecies is not None else "",
            var=" var. {}".format(self.variety) if self.variety is not None else "",
            fma=" fma. {}".format(self.form) if self.form is not None else "",
        )
        self.scientific_name_full = "{genus} {epithet}{authorship}{sub_ssp}{var}{fma}".format(
            genus=genus, epithet=self.specific_epithet,
            authorship=" {}".format(
                self.scientific_name_authorship
            ) if self.scientific_name_authorship is not None else "",
            sub_ssp=" subsp. {}{}".format(
                self.subspecies,
                " {}".format(
                    self.ssp_authorship
                ) if self.ssp_authorship is not None else ""
            ) if self.subspecies is not None else "",
            var=" var. {}{}".format(
                self.variety,
                " {}".format(
                    self.variety_authorship
                ) if self.variety_authorship is not None else ""
            ) if self.variety is not None else "",
            fma=" fma. {}{}".format(
                self.form,
                " {}".format(
                    self.form_authorship
                ) if self.form_authorship is not None else ""
            ) if self.form is not None else "",
        )
        self.scientific_name_db = self.scientific_name.upper()
        return

    def save(self, *args, **kwargs):
        if self.form is not None:
            taxon_rank = TaxonRank.objects.get(name__iexact=pgettext("taxonomic", "form"))
        elif self.variety is not None:
            taxon_rank = TaxonRank.objects.get(name__iexact=pgettext("taxonomic", "variety"))
        elif self.subspecies is not None:
            taxon_rank = TaxonRank.objects.get(name__iexact=pgettext("taxonomic", "subspecies"))
        else:
            taxon_rank = TaxonRank.objects.get(name__iexact=pgettext("taxonomic", "species"))
        self.taxon_rank = taxon_rank
        return super().save(*args, **kwargs)

    class Meta:
        abstract = True


class CommonNameQuerySet(AttributeQuerySet):
    __attribute_name__ = "common_names"


class CommonName(AttributeModel):
    name = models.CharField(verbose_name=_("Name"), max_length=300, blank=True, null=True)
    language = models.CharField(verbose_name=_("Language"), choices=settings.LANGUAGES, max_length=5, default="es",
                                blank=False, null=True)

    objects = CommonNameQuerySet.as_manager()

    def __hash__(self):
        return super().__hash__()

    def __eq__(self, other: object):
        return super().__eq__(other) and self.name == other.name

    def __unicode__(self):
        return u"%s" % self.name

    def __str__(self):
        return "%s" % self.name

    def __repr__(self):
        return "%s" % self.name

    class Meta:
        verbose_name = _("Common Name")
        verbose_name_plural = _("Common Names")
        ordering = ['name']


class SpeciesQuerySet(TaxonomicQuerySet):
    __rank_name__ = "species"


class Species(ScientificName):
    __attributes__ = {
        "id_taxa": "id del taxa",
        "in_argentina": "en Argentina",
        "in_bolivia": "en Bolivia",
        "in_peru": "en Perú",
        "status": "origen",
        "minimum_height": "altura mínima",
        "maximum_height": "altura máxima",
        "notes": "notes",
        "type_id": "id de tipo",
        "id_mma": "id del MMA",
        "determined": "terminal",
        "id_taxa_origin": "id del taxón de origen",
    }

    id_taxa = models.IntegerField(verbose_name=_("ID Taxa"), blank=True, null=True, help_text="")
    genus = models.ForeignKey(Genus, verbose_name=_("Genus"), on_delete=models.CASCADE, blank=True, null=True,
                              help_text=_("Genus"))
    common_names = models.ManyToManyField(CommonName, verbose_name=_("Common names"), blank=True)
    in_argentina = models.BooleanField(verbose_name=_("In Argentina"), default=False)
    in_bolivia = models.BooleanField(verbose_name=_("In Bolivia"), default=False)
    in_peru = models.BooleanField(verbose_name=_("In Peru"), default=False)
    plant_habit = models.ManyToManyField(PlantHabit, verbose_name=_("Habit"), blank=True, db_column="plant_habit")
    env_habit = models.ManyToManyField(EnvironmentalHabit, verbose_name=_("Life Form"), blank=True,
                                       db_column="environmental_habit")
    cycle = models.ManyToManyField(Cycle, verbose_name=_("Cycle"), blank=True, db_column="cycle")
    status = models.ForeignKey(Status, verbose_name=_("Origin"),  on_delete=models.CASCADE, blank=True, null=True)
    minimum_height = models.IntegerField(verbose_name=_("Minimum Height"), blank=True, null=True)
    maximum_height = models.IntegerField(verbose_name=_("Maximum Height"), blank=True, null=True)
    notes = models.CharField(verbose_name=_("Notes"), max_length=1000, blank=True, null=True)
    type_id = models.CharField(verbose_name=_("Type ID"), max_length=300, blank=True, null=True)
    region = models.ManyToManyField(Region, verbose_name=_("Regions"), blank=True, db_column="region")
    id_mma = models.IntegerField(verbose_name=_("MMA ID"), blank=True, null=True,
                                 help_text=_("ID of the species platform of the MMA"))
    conservation_status = models.ManyToManyField(ConservationStatus, verbose_name=_("State of Conservation"), blank=True)
    determined = models.BooleanField(verbose_name=_("Determined?"), default=False)
    id_taxa_origin = models.IntegerField(verbose_name=_("ID Taxa of Origin"), blank=True, null=True, help_text="")
    parent_content_type = models.ForeignKey(ContentType, on_delete=models.CASCADE)
    parent_taxon_id = models.PositiveIntegerField()
    parent_name = GenericForeignKey("parent_content_type", "parent_taxon_id")

    objects = SpeciesQuerySet.as_manager()

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if self.pk is not None:
            self.__prev__ = Synonymy(species=self)
        else:
            self.__prev__ = None

    def __hash__(self):
        return super().__hash__()

    def __eq__(self, other):
        return super().__eq__(other) and len(self.__difference__(other)) == 0

    def __difference__(self, other: Species) -> List[str]:
        difference = list()
        for attribute in self.__attributes__:
            if getattr(self, attribute) != getattr(other, attribute):
                difference.append("'{}' de '{}' a '{}'".format(
                    self.__attributes__[attribute],
                    getattr(self, attribute),
                    getattr(other, attribute)
                ))
        return difference

    @property
    def family(self):
        return self.genus.family

    @property
    def order(self):
        return self.family.order

    @property
    def classname(self):
        return self.order.classname

    @property
    def division(self):
        return self.classname.division

    @property
    def kingdom(self):
        return self.division.kingdom

    @staticmethod
    def get_parent_query(search: str) -> Q:
        return Q(genus__name__icontains=search)

    @staticmethod
    def get_created_by_query(search: str) -> Q:
        return TaxonomicModel.get_created_by_query(search)

    @property
    def parent(self) -> TaxonomicModel | None:
        try:
            return self.parent_content_type.model_class().objects.get(unique_taxon_id=self.parent_taxon_id)
        except ObjectDoesNotExist:
            return None

    def get_higher_classification(self) -> List[str]:
        higher_classification = list()
        parent = self.parent
        while parent is not None:
            higher_classification.insert(0, parent.name)
            parent = parent.parent
        return higher_classification

    @classmethod
    def get_dwc_data(cls, logger: logging.Logger = logging.getLogger(__name__), task: Task = None):
        from ..metadata.models import EML
        eml = EML.objects.get(pk=1)
        objects = cls.objects.all()
        rows = list()
        logger.debug(f"Extracting data: species")
        current_total = 0
        total = objects.count()
        if task is not None:
            async_result = AsyncResult(task.request.id)
            current_total = async_result.info["total"]
            total += current_total
            task.update_state(state="PROGRESS", meta={"step": current_total, "total": total, "logs": logger[0].get_logs()})
        errors = list()
        for i, obj in enumerate(objects):
            if task is not None:
                task.update_state(state="PROGRESS", meta={"step": i + current_total, "total": total, "logs": logger[0].get_logs()})
            if obj.parent is None:
                errors.append(obj.name)
            else:
                rows.append(
                    [
                        obj.taxon_id, obj.parent.taxon_id, obj.taxon_id,
                        obj.taxon_id, obj.taxon_id, eml.package_id,
                        "accepted", obj.taxon_rank.name_en, obj.notes, obj.dwc_scientific_name,
                        obj.get_higher_classification()
                    ] + obj.get_higher_classification()[0:6] + [
                        obj.genus.name, None, obj.specific_epithet,
                        obj.infraspecific_epithet, obj.authorship,
                        None, None,
                        "ICBN", None,
                        obj.updated_at, "https://udec.cl", "UDEC",
                        eml.dataset.title,
                    ]
                )
        if len(errors) > 0:
            raise AttributeError("Parent not found on:\n" + "\n".join(errors))
        return pd.DataFrame(rows, columns=[
            field.name for field in CATALOG_DWC_FIELDS
        ])

    def save(self, force_insert=False, force_update=False, using=None, update_fields=None, **kwargs):
        if force_update:
            return super().save(
                force_insert=force_insert,
                force_update=force_update,
                using=using,
                update_fields=update_fields,
                **kwargs
            )
        self.__update_scientific_name__()
        if self.__prev__ is not None:
            logging.debug(f"{self.__prev__} ({self.__prev__.pk})")
            if self.__original__ != self:
                if self.__original__.scientific_name != self.scientific_name or \
                        self.__original__.scientific_name_full != self.scientific_name_full:
                    if self.__original__.scientific_name_full != self.scientific_name_full:
                        logging.debug(f"Name changed on taxa {self.pk}")
                        logging.debug("Listing specimen:")
                        logging.debug("\n".join([
                            specimen.biodata_code.code
                            for specimen in self.voucherimported_set.all()
                        ]))
                        for specimen in self.voucherimported_set.all():
                            specimen.generate_etiquette()
                        with connection.cursor() as cursor:
                            cursor.execute("SELECT get_taxon_id()")
                            result = cursor.fetchone()
                            if result:
                                self.unique_taxon_id = result[0]
                            else:
                                raise RuntimeError("Cannot got unique taxa id")
                        self.taxon_id = settings.TAXA_ID_PREF + str(self.unique_taxon_id)
                    try:
                        self.__prev__.species = self
                        self.__prev__.save(user=kwargs["user"])
                    except Exception as e:
                        logging.error("Error saving synonymy\n{}".format(e), exc_info=True)
                if len(self.__difference__(self.__original__)) > 0:
                    kwargs["notes"] = "Actualización de {}".format(
                        "; ".join(self.__difference__(self.__original__))
                    )
        if self.parent is None:
            self.parent_content_type = ContentType.objects.get_for_model(Genus)
            self.parent_taxon_id = self.genus.unique_taxon_id
        return super().save(
            force_insert=force_insert,
            force_update=force_update,
            using=using,
            update_fields=update_fields,
            **kwargs
        )

    class Meta:
        verbose_name = _("Species")
        verbose_name_plural = pgettext_lazy("plural", "Species")
        ordering = ['scientific_name']


class SynonymyQuerySet(AttributeQuerySet):
    __attribute_name__ = "synonymy"

    def search(self, text: str) -> AttributeQuerySet:
        return self.filter(scientific_name_full__icontains=text)


class Synonymy(ScientificName):
    species = models.ForeignKey(Species, verbose_name=_("Species"), related_name="synonyms", on_delete=models.PROTECT, blank=True, null=True)

    objects = SynonymyQuerySet.as_manager()

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if "species" in kwargs:
            species: Species = kwargs["species"]
            self.unique_taxon_id = species.unique_taxon_id
            self.taxon_id = species.taxon_id
            self.genus = str(species.genus).capitalize()
            self.scientific_name = species.scientific_name
            self.scientific_name_db = species.scientific_name_db
            self.scientific_name_full = species.scientific_name_full
            self.specific_epithet = species.specific_epithet
            self.scientific_name_authorship = species.scientific_name_authorship
            self.subspecies = species.subspecies
            self.ssp_authorship = species.ssp_authorship
            self.variety = species.variety
            self.variety_authorship = species.variety_authorship
            self.form = species.form
            self.form_authorship = species.form_authorship

    @staticmethod
    def get_parent_query(search: str) -> Q:
        return Q(species__scientific_name__icontains=search)

    @staticmethod
    def get_created_by_query(search: str) -> Q:
        return TaxonomicModel.get_created_by_query(search)

    @property
    def parent(self) -> TaxonomicModel | None:
        return self.species.parent

    def get_higher_classification(self) -> List[str]:
        return self.species.get_higher_classification()

    @classmethod
    def get_dwc_data(cls, logger: logging.Logger = logging.getLogger(__name__), task: Task = None):
        from ..metadata.models import EML
        eml = EML.objects.get(pk=1)
        objects = cls.objects.all()
        rows = list()
        logger.debug(f"Extracting data: synonyms")
        current_total = 0
        total = objects.count()
        if task is not None:
            async_result = AsyncResult(task.request.id)
            current_total = async_result.info["total"]
            total += current_total
            task.update_state(state="PROGRESS",
                              meta={"step": current_total, "total": total, "logs": logger[0].get_logs()})
        for i, obj in enumerate(objects):
            if task is not None:
                task.update_state(state="PROGRESS",
                                  meta={"step": i + current_total, "total": total, "logs": logger[0].get_logs()})
            if obj.species is None:
                logger.warning(f"Species not found on synonym {obj.name}")
            else:
                rows.append(
                    [
                        obj.taxon_id, obj.parent.taxon_id, obj.species.taxon_id,
                        obj.species.taxon_id, obj.taxon_id, eml.package_id,
                        "synonym", obj.taxon_rank.name_en, "", obj.dwc_scientific_name,
                        obj.get_higher_classification()
                    ] + obj.get_higher_classification()[0:6] + [
                        obj.genus, None, obj.specific_epithet,
                        obj.infraspecific_epithet, obj.authorship,
                        None, None,
                        "ICBN", None,
                        obj.updated_at, "https://udec.cl", "UDEC",
                        eml.dataset.title,
                    ]
                )
        return pd.DataFrame(rows, columns=[
            field.name for field in CATALOG_DWC_FIELDS
        ])

    def save(self, force_insert=False, force_update=False, using=None, update_fields=None, **kwargs):
        if force_update:
            return super().save(
                force_insert=force_insert,
                force_update=force_update,
                using=using,
                update_fields=update_fields,
                **kwargs
            )
        self.genus = str(self.genus).capitalize()
        self.__update_scientific_name__()
        return super().save(
            force_insert=force_insert,
            force_update=force_update,
            using=using,
            update_fields=update_fields,
            **kwargs
        )

    class Meta:
        verbose_name = _("Synonym")
        verbose_name_plural = _("Synonyms")
        ordering = ['scientific_name']


class Binnacle(models.Model):
    TAXONOMIC_MODEL_NAME = {
        "Division": "División",
        "ClassName": "Clase",
        "Order": "Orden",
        "Family": "Familia",
        "Genus": "Género",
        "Synonymy": "Sinónimo",
        "CommonName": "Nombre Común",
        "Species": "Especie",
    }

    type_update = models.CharField(max_length=100, blank=True, null=True, help_text="tipo")
    model = models.CharField(max_length=100, blank=True, null=True, help_text="modelo")
    description = models.CharField(max_length=2000, blank=True, null=True, help_text="descripción")
    note = models.CharField(blank=True, null=True, help_text="descripción")
    created_at = models.DateTimeField(auto_now_add=True, blank=True, null=True, editable=False)
    updated_at = models.DateTimeField(auto_now=True)
    created_by = models.ForeignKey(User, on_delete=models.PROTECT, default=1, editable=False)

    def __unicode__(self):
        return u"%s" % self.description

    def __str__(self):
        return "%s" % self.description

    def __repr__(self):
        return "Binnacle::%s" % self.description

    class Meta:
        verbose_name_plural = "Binnacles"
        ordering = ['-updated_at']

    @staticmethod
    def __get_taxonomic_name__(model: TaxonomicModel) -> str:
        return Binnacle.TAXONOMIC_MODEL_NAME[
            model.__class__.__name__
        ]

    @staticmethod
    def new_entry(model: TaxonomicModel, created_by: User, notes: str = None) -> None:
        rank_name = Binnacle.__get_taxonomic_name__(model)
        description = "Se crea {} {} ({})".format(
            rank_name,
            repr(model),
            model.pk
        )
        logging.info("{}: {}".format(created_by.username, description))
        binnacle = Binnacle(
            type_update="Nuevo",
            model=rank_name,
            description=description,
            created_by=created_by,
            note=notes
        )
        return binnacle.save()

    @staticmethod
    def update_entry(prev_model: str, model: TaxonomicModel, created_by: User, notes: str = None) -> None:
        rank_name = Binnacle.__get_taxonomic_name__(model)
        description = "Se actualiza {} {} ({}) en {}".format(
            rank_name,
            prev_model,
            model.pk,
            repr(model)
        )
        logging.info("{}: {}".format(created_by.username, description))
        binnacle = Binnacle(
            type_update="Actualización",
            model=rank_name,
            description=description,
            created_by=created_by,
            note=notes
        )
        return binnacle.save()

    @staticmethod
    def delete_entry(model: TaxonomicModel, created_by: User, notes: str = None) -> None:
        rank_name = Binnacle.__get_taxonomic_name__(model)
        description = "Se elimina {} {} ({})".format(
            rank_name,
            repr(model),
            model.pk
        )
        try:
            model.delete()
            logging.info("{}: {}".format(created_by, description))
            binnacle = Binnacle(
                type_update="Eliminación",
                model=rank_name,
                description=description,
                created_by=created_by,
                note=notes
            )
            binnacle.save()
        except Exception as e:
            logging.error("Error on '{}'".format(description))
            raise e


class DownloadSearchRegistration(models.Model):
    mail = models.EmailField(null=False, blank=False)
    name = models.CharField(max_length=100, null=False, blank=False)
    requested_at = models.DateTimeField(auto_now=True, null=False, blank=False)
    institution = models.CharField(max_length=200, null=False, blank=False)
    format = models.IntegerField(choices=FORMAT_CHOICES, default=0)
    request_status = models.BooleanField(default=False)


class CatalogView(TaxonomicModel):
    """
    CREATE MATERIALIZED VIEW catalog_view AS
    SELECT species.id,
           species.id_taxa,
           species.unique_taxon_id,
           species.taxon_id,
           kingdom.id      AS kingdom_id,
           kingdom.name    AS kingdom,
           division.id     AS division_id,
           division.name   AS division,
           classname.id    AS classname_id,
           classname.name  AS classname,
           "order".id      AS order_id,
           "order".name    AS "order",
           family.id       AS family_id,
           family.name     AS family,
           genus.id        AS genus_id,
           genus.name      AS genus,
           species.scientific_name,
           species.scientific_name_full,
           species.specific_epithet,
           species.scientific_name_authorship,
           species.subspecies,
           species.ssp_authorship,
           species.variety,
           species.variety_authorship,
           species.form,
           species.form_authorship,
           species.in_argentina,
           species.in_bolivia,
           species.in_peru,
           status.name     AS status,
           status.name_es  AS status_es,
           status.name_en  AS status_en,
           species.minimum_height,
           species.maximum_height,
           species.notes,
           species.type_id,
           species.determined,
           species.id_taxa_origin,
           species.created_at,
           species.updated_at,
           "user".username AS created_by
    FROM catalog_species species
         JOIN auth_user "user" ON species.created_by_id = "user".id
         JOIN catalog_genus genus ON species.genus_id = genus.id
         JOIN catalog_family family ON genus.family_id = family.id
         JOIN catalog_order "order" ON family.order_id = "order".id
         JOIN catalog_classname classname ON "order".classname_id = classname.id
         JOIN catalog_division division ON classname.division_id = division.id
         JOIN catalog_kingdom kingdom ON division.kingdom_id = kingdom.id
         LEFT JOIN catalog_status status ON species.status_id = status.id;

    CREATE UNIQUE INDEX catalog_view_id_idx
        ON catalog_view (id);
    """
    id = models.IntegerField(primary_key=True, blank=False, null=False, help_text="")
    id_taxa = models.IntegerField(blank=False, null=False, help_text="")
    unique_taxon_id = models.BigIntegerField()
    taxon_id = models.CharField()
    kingdom_id = models.IntegerField(blank=False, null=False, help_text="")
    kingdom = models.CharField(max_length=300, blank=True, null=True)
    division_id = models.IntegerField(blank=False, null=False, help_text="")
    division = models.CharField(max_length=300, blank=True, null=True)
    classname_id = models.IntegerField(blank=False, null=False, help_text="")
    classname = models.CharField(max_length=300, blank=True, null=True)
    order_id = models.IntegerField(blank=False, null=False, help_text="")
    order = models.CharField(max_length=300, blank=True, null=True, db_column="order")
    family_id = models.IntegerField(blank=False, null=False, help_text="")
    family = models.CharField(max_length=300, blank=True, null=True)
    genus_id = models.IntegerField(blank=False, null=False, help_text="")
    genus = models.CharField(max_length=300, blank=True, null=True)
    scientific_name = models.CharField(max_length=500, blank=True, null=True, help_text="sp")
    scientific_name_full = models.CharField(max_length=800, blank=True, null=True, help_text="spCompleto")
    specific_epithet = models.CharField(max_length=300, blank=True, null=True, help_text="EpitetoEspecifico")
    scientific_name_authorship = models.CharField(max_length=500, blank=True, null=True, help_text="AutoresSp")
    subspecies = models.CharField(max_length=300, blank=True, null=True)
    ssp_authorship = models.CharField(max_length=500, blank=True, null=True)
    variety = models.CharField(max_length=300, blank=True, null=True)
    variety_authorship = models.CharField(max_length=500, blank=True, null=True)
    form = models.CharField(max_length=300, blank=True, null=True)
    form_authorship = models.CharField(max_length=500, blank=True, null=True)
    in_argentina = models.BooleanField(default=False)
    in_bolivia = models.BooleanField(default=False)
    in_peru = models.BooleanField(default=False)
    status = models.CharField(max_length=300, blank=True, null=True)
    minimum_height = models.IntegerField(blank=True, null=True)
    maximum_height = models.IntegerField(blank=True, null=True)
    notes = models.CharField(max_length=1000, blank=True, null=True)
    type_id = models.CharField(max_length=300, blank=True, null=True)
    determined = models.BooleanField(default=False)
    id_taxa_origin = models.IntegerField(blank=True, null=True, help_text="")
    created_at = models.DateTimeField(blank=True, null=True, editable=False)
    updated_at = models.DateTimeField()
    created_by = models.CharField(max_length=300, blank=True, null=True)

    @classmethod
    def refresh_view(cls):
        with connection.cursor() as cursor:
            cursor.execute("REFRESH MATERIALIZED VIEW CONCURRENTLY catalog_view")

    @staticmethod
    def get_query_name(search: str) -> Q:
        return Q(scientific_name_full__icontains=search)

    @staticmethod
    def get_parent_query(search: str) -> Q:
        return Q(genus__icontains=search)

    @staticmethod
    def get_created_by_query(search: str) -> Q:
        return Q(created_by__icontains=search)

    class Meta:
        managed = False
        db_table = 'catalog_view'


class SynonymyView(TaxonomicModel):
    """
    CREATE MATERIALIZED VIEW synonymy_view AS
    SELECT synonymy.id,
           species_id,
           species.id_taxa,
           species.scientific_name AS species_scientific_name,
           synonymy.scientific_name,
           synonymy.scientific_name_full,
           synonymy.genus,
           synonymy.specific_epithet,
           synonymy.scientific_name_authorship,
           synonymy.subspecies,
           synonymy.ssp_authorship,
           synonymy.variety,
           synonymy.variety_authorship,
           synonymy.form,
           synonymy.form_authorship,
           synonymy.created_at,
           synonymy.updated_at,
           "user".username          AS created_by
    FROM catalog_synonymy synonymy
        LEFT JOIN catalog_species species ON synonymy.species_id = species.id
        LEFT JOIN auth_user "user" ON synonymy.created_by_id = "user".id;

    CREATE UNIQUE INDEX synonymy_view_id_idx
        ON synonymy_view (id);
    """
    id = models.IntegerField(primary_key=True, blank=False, null=False, help_text="")
    species_id = models.IntegerField(blank=False, null=False, help_text="")
    id_taxa = models.IntegerField(blank=False, null=False, help_text="")
    unique_taxon_id = models.BigIntegerField()
    taxon_id = models.CharField()
    species_scientific_name = models.CharField(max_length=500, blank=True, null=True, help_text="sp")
    scientific_name = models.CharField(max_length=300, blank=True, null=True)
    scientific_name_full = models.CharField(max_length=800, blank=True, null=True)
    genus = models.CharField(max_length=300, blank=True, null=True)
    specific_epithet = models.CharField(max_length=300, blank=True, null=True)
    scientific_name_authorship = models.CharField(max_length=500, blank=True, null=True)
    subspecies = models.CharField(max_length=300, blank=True, null=True)
    ssp_authorship = models.CharField(max_length=500, blank=True, null=True)
    variety = models.CharField(max_length=300, blank=True, null=True)
    variety_authorship = models.CharField(max_length=500, blank=True, null=True)
    form = models.CharField(max_length=300, blank=True, null=True)
    form_authorship = models.CharField(max_length=300, blank=True, null=True)
    created_at = models.DateTimeField(blank=True, null=True, editable=False)
    updated_at = models.DateTimeField()
    created_by = models.CharField(max_length=300, blank=True, null=True)

    @staticmethod
    def get_query_name(search: str) -> Q:
        return Q(scientific_name_full__icontains=search)

    @staticmethod
    def get_parent_query(search: str) -> Q:
        return Q(species_scientific_name__icontains=search)

    @staticmethod
    def get_created_by_query(search: str) -> Q:
        return Q(created_by__icontains=search)

    @classmethod
    def refresh_view(cls):
        with connection.cursor() as cursor:
            cursor.execute("REFRESH MATERIALIZED VIEW CONCURRENTLY synonymy_view")

    class Meta:
        managed = False
        db_table = 'synonymy_view'


class RegionDistributionView(models.Model):
    """
    CREATE MATERIALIZED VIEW region_view AS
    SELECT species_region.id,
           species.id              AS species_id,
           species.id_taxa,
           species.scientific_name AS specie_scientific_name,
           region.name             AS region_name,
           region.name_es          AS region_name_es,
           region.name_en          AS region_name_en,
           region.key              AS region_key
    FROM catalog_species_region species_region
         JOIN catalog_species species ON species_region.species_id = species.id
         JOIN catalog_region region ON species_region.region_id = region.id
    ORDER BY species_region.id;

    CREATE UNIQUE INDEX region_distribution_view_id_idx
        ON region_view (id);
    """
    id = models.IntegerField(primary_key=True, blank=False, null=False, help_text="")
    species_id = models.IntegerField(blank=False, null=False, help_text="")
    id_taxa = models.IntegerField(blank=False, null=False, help_text="")
    specie_scientific_name = models.CharField(max_length=500, blank=True, null=True, help_text="sp")
    region_name = models.CharField(max_length=300, blank=True, null=True)
    region_key = models.CharField(max_length=3, blank=True, null=True)

    @classmethod
    def refresh_view(cls):
        with connection.cursor() as cursor:
            cursor.execute("REFRESH MATERIALIZED VIEW CONCURRENTLY region_view")

    class Meta:
        managed = False
        db_table = 'region_view'


class FinderView(models.Model):
    """
    CREATE MATERIALIZED VIEW finder_view AS
    SELECT taxon_id,
           unique_taxon_id AS id,
           'species'       AS type,
           scientific_name AS name,
           determined
    FROM catalog_species
    UNION ALL
    SELECT taxon_id,
           unique_taxon_id AS id,
           'synonymy'      AS type,
           scientific_name AS name,
           FALSE           AS determined
    FROM catalog_synonymy
    UNION ALL
    SELECT taxon_id,
           unique_taxon_id AS id,
           'kingdom'       AS type,
           name            AS name,
           FALSE           AS determined
    FROM catalog_kingdom
    UNION ALL
    SELECT taxon_id,
           unique_taxon_id AS id,
           'division'      AS type,
           name            AS name,
           FALSE           AS determined
    FROM catalog_division
    UNION ALL
    SELECT taxon_id,
           unique_taxon_id AS id,
           'class'         AS type,
           name            AS name,
           FALSE           AS determined
    FROM catalog_classname
    UNION ALL
    SELECT taxon_id,
           unique_taxon_id AS id,
           'order'         AS type,
           name            AS name,
           FALSE           AS determined
    FROM catalog_order
    UNION ALL
    SELECT taxon_id,
           unique_taxon_id AS id,
           'family'        AS type,
           name            AS name,
           FALSE           AS determined
    FROM catalog_family
    UNION ALL
    SELECT taxon_id,
           unique_taxon_id AS id,
           'genus'         AS type,
           name            AS name,
           FALSE           AS determined
    FROM catalog_genus
    UNION ALL
    SELECT id              AS taxon_id,
           id,
           'common_name'   AS type,
           name,
           FALSE           AS determined
    FROM catalog_commonname
    ORDER BY type, name;

    CREATE UNIQUE INDEX finder_view_id
        ON finder_view (id, type);

    CREATE INDEX finder_view_trgm_id
        ON finder_view USING gin(name gin_trgm_ops);
    """
    taxon_id = models.CharField()
    id = models.IntegerField(primary_key=True, blank=False, null=False, help_text="id")
    name = models.CharField(max_length=500, blank=True, null=True, help_text="name")
    type = models.CharField(max_length=50, blank=True, null=True)
    determined = models.BooleanField(default=False)

    @classmethod
    def refresh_view(cls):
        with connection.cursor() as cursor:
            cursor.execute("REFRESH MATERIALIZED VIEW CONCURRENTLY finder_view")

    class Meta:
        managed = False
        db_table = 'finder_view'


RANK_MODELS = {
    "kingdom": Kingdom,
    "division": Division,
    "classname": ClassName,
    "order": Order,
    "family": Family,
    "genus": Genus,
    "species": Species,
}


def get_fuzzy_taxa(rank: str, search: str) -> int:
    start = time()
    model = RANK_MODELS[rank]
    str_name = 'scientific_name' if rank == 'search' else 'name'
    results = model.objects.annotate(
        similarity=TrigramSimilarity(str_name, search)
    ).filter(
        similarity__gte=0.6
    ).order_by('-similarity')
    show_results = [
        (getattr(result, str_name), result.similarity) for result in results
    ]
    logging.debug(f"Fuzzy match of {search} "
                  f"in {rank} took {time() - start} s, "
                  f"and got {show_results}")
    if results.count() >= 1:
        return results.first().pk
    else:
        return -1
