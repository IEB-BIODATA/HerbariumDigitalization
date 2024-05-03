from __future__ import annotations

from time import time_ns

import logging
from abc import abstractmethod, ABC
from copy import deepcopy
from django.contrib.auth.models import User
from django.contrib.gis.db.models import GeometryField
from django.db import connection
from django.db import models
from django.db.models import Q
from django.utils.translation import gettext_lazy as _, pgettext_lazy
from typing import List, Dict, Tuple

from intranet.utils import CatalogQuerySet

ATTRIBUTES = [
    "plant_habit", "env_habit",
    "status", "cycle",
    "region", "conservation_state",
    "common_names",
]

TAXONOMIC_RANK = [
    "kingdom", "division", "class_name", "order",
    "family", "genus", "species",
]


class AttributeQuerySet(CatalogQuerySet, ABC):
    __attribute_name__ = "query"

    @staticmethod
    def species_filter():
        return "species"

    def filter_for_species(self, query: Q) -> AttributeQuerySet:
        return self.filter(query).distinct()

    def filter_query_in(self, **parameters: Dict[str, List[str]]) -> AttributeQuerySet:
        start = time_ns()
        query = Q()
        for query_key, parameter in parameters.items():
            if query_key == self.__attribute_name__:
                continue
            query &= Q(**{f"species__{query_key}__in": parameter})
        queryset = self.filter(query).distinct()
        logging.debug(f"{self.__attribute_name__}: {query} and got {queryset}")
        logging.debug(
            f"Filtering {self.__attribute_name__} using attributes took {(time_ns() - start) / 1e6:.2f} milliseconds"
        )
        return queryset

    def filter_query(self, **parameters: Dict[str, List[str]]) -> AttributeQuerySet:
        start = time_ns()
        query = Q()
        for query_key, parameter in parameters.items():
            query_name = f"species__{query_key}" if query_key != self.__attribute_name__ else "pk"
            query &= Q(**{query_name: parameter})
        queryset = self.filter(query).distinct()
        logging.debug(f"{self.__attribute_name__}: {query} and got {queryset}")
        logging.debug(
            f"Filtering {self.__attribute_name__} using attributes took {(time_ns() - start) / 1e6:.2f} milliseconds"
        )
        return queryset

    def filter_taxonomy_in(self, **parameters: Dict[str: List[str]]) -> AttributeQuerySet:
        return self.filter_taxonomy(_in=True, **parameters)

    def filter_taxonomy(self, _in: bool = False, **parameters: Dict[str: List[str]]) -> AttributeQuerySet:
        start = time_ns()
        query = Q()
        with_in = "__in" if _in else ""
        for taxonomic_rank, parameter in parameters.items():
            logging.debug(f"{self.__attribute_name__}: Species from {taxonomic_rank}: {parameter}")
            species = CatalogView.objects.filter(**{f"{taxonomic_rank}_id{with_in}": parameter})
            query &= Q(**{f"{self.species_filter()}__in": Species.objects.filter(pk__in=species)})
        queryset = self.filter_for_species(query)
        logging.debug(
            f"Filtering {self.__attribute_name__} using taxonomies took {(time_ns() - start) / 1e6:.2f} milliseconds"
        )
        return queryset
    
    def filter_geometry_in(self, geometries: List[str]) -> AttributeQuerySet:
        start = time_ns()
        query = Q()
        for geometry in geometries:
            query |= Q(species__voucherimported__point__within=geometry)
        queryset = self.filter(query)
        logging.debug(f"{self.__attribute_name__}: {query} and got {queryset}")
        logging.debug(
            f"Filtering {self.__attribute_name__} using geometry took {(time_ns() - start) / 1e6:.2f} milliseconds"
        )
        return queryset 
    
    def filter_geometry(self, geometry) -> AttributeQuerySet:
        start = time_ns()
        query = Q(species__voucherimported__point__within=geometry)
        queryset = self.filter(query)
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
        self.___rank_index__ = TAXONOMIC_RANK.index(self.__rank_name__)
        return

    def filter_query_in(self, **parameters: Dict[str, List[str]]) -> TaxonomicQuerySet:
        start = time_ns()
        query = Q()
        rank_index = TAXONOMIC_RANK.index(self.__rank_name__)
        for query_key, parameter in parameters.items():
            query_name = "__".join(TAXONOMIC_RANK[rank_index + 1:])
            if query_name != "":
                query_name = f"{query_name}__"
            query &= Q(**{f"{query_name}{query_key}__in": parameter})
        queryset = self.filter(query).distinct()
        logging.debug(f"{self.__rank_name__}: {query} and got {queryset}")
        logging.debug(
            f"Filtering {self.__rank_name__} using attributes took {(time_ns() - start) / 1e6:.2f} milliseconds"
        )
        return queryset

    def filter_query(self, **parameters: Dict[str, List[str]]) -> TaxonomicQuerySet:
        start = time_ns()
        query = Q()
        rank_index = TAXONOMIC_RANK.index(self.__rank_name__)
        for query_key, parameter in parameters.items():
            query_name = "__".join(TAXONOMIC_RANK[rank_index + 1:])
            if query_name != "":
                query_name = f"{query_name}__"
            query &= Q(**{f"{query_name}{query_key}": parameter})
        queryset = self.filter(query).distinct()
        logging.debug(f"{self.__rank_name__}: {query} and got {queryset}")
        logging.debug(
            f"Filtering {self.__rank_name__} using attributes took {(time_ns() - start) / 1e6:.2f} milliseconds"
        )
        return queryset

    def get_taxonomic_query(self, taxonomic_rank: str, with_in: bool = False) -> str:
        rank_index = TAXONOMIC_RANK.index(taxonomic_rank)
        str_in = "__in" if with_in else ""
        if self.___rank_index__ < rank_index:
            return "__".join(TAXONOMIC_RANK[self.___rank_index__ + 1: rank_index + 1]) + str_in
        elif self.___rank_index__ == rank_index:
            if with_in:
                raise RuntimeError
            return "pk"
        else:  # self.__rank_index__ > rank_index
            return "__".join(reversed(TAXONOMIC_RANK[rank_index: self.___rank_index__])) + str_in

    def filter_taxonomy_in(self, **parameters: Dict[str: List[str]]) -> TaxonomicQuerySet:
        start = time_ns()
        query = Q()
        for taxonomic_rank, parameter in parameters.items():
            try:
                query &= Q(**{self.get_taxonomic_query(taxonomic_rank, with_in=True): parameter})
            except RuntimeError:
                continue
        queryset = self.filter(query).distinct()
        logging.debug(f"{self.__rank_name__}: {query} and got {queryset}")
        logging.debug(
            f"Filtering {self.__rank_name__} using taxonomies took {(time_ns() - start) / 1e6:.2f} milliseconds"
        )
        return queryset

    def filter_taxonomy(self, **parameters: Dict[str: List[str]]) -> TaxonomicQuerySet:
        start = time_ns()
        query = Q()
        for taxonomic_rank, parameter in parameters.items():
            query &= Q(**{self.get_taxonomic_query(taxonomic_rank): parameter})
        queryset = self.filter(query).distinct()
        logging.debug(f"{self.__rank_name__}: {query} and got {queryset}")
        logging.debug(
            f"Filtering {self.__rank_name__} using taxonomies took {(time_ns() - start) / 1e6:.2f} milliseconds"
        )
        return queryset

    def filter_geometry_in(self, geometries: List[str]) -> TaxonomicQuerySet:
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

    def filter_geometry(self, geometry: str) -> TaxonomicQuerySet:
        start = time_ns()
        rank_index = TAXONOMIC_RANK.index(self.__rank_name__)
        query_name = "__".join(TAXONOMIC_RANK[rank_index + 1:])
        if query_name != "":
            query_name = f"{query_name}__"
        query = Q(**{f"{query_name}voucherimported__point__within": geometry})
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


class RegionQuerySet(AttributeQuerySet):
    __attribute_name__ = "region"

    def filter_geometry_in(self, geometries: List[str]) -> TaxonomicQuerySet:
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

    def filter_geometry(self, geometry) -> TaxonomicQuerySet:
        start = time_ns()
        query = Q(geometry__intersects=geometry)
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


class ConservationStateQuerySet(AttributeQuerySet):
    __attribute_name__ = "conservation_state"


class ConservationState(AttributeModel):
    key = models.CharField(verbose_name=_("Key"), max_length=3, blank=True, null=True)
    order = models.IntegerField(verbose_name=pgettext_lazy("ordering", "Order"), blank=True, null=True, db_column="order")

    objects = ConservationStateQuerySet.as_manager()

    def __unicode__(self):
        return u"%s" % self.name

    def __str__(self):
        return f"{self.name} ({self.key})"

    def __repr__(self):
        return "Conservation State::%s" % self.name

    class Meta:
        verbose_name = _("Conservation State")
        verbose_name_plural = _("Conservation States")
        ordering = ['order']


class TaxonomicModel(models.Model):
    created_at = models.DateTimeField(verbose_name=_("Created at"), auto_now_add=True, blank=True, null=True, editable=False)
    updated_at = models.DateTimeField(verbose_name=_("Updated at"), auto_now=True)
    created_by = models.ForeignKey(User, verbose_name=_("Created by"), on_delete=models.PROTECT, default=1, editable=False)

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

    class Meta:
        verbose_name_plural = _("Division")
        verbose_name_plural = _("Divisions")
        ordering = ['name']


class ClassQuerySet(TaxonomicQuerySet):
    __rank_name__ = "class_name"


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

    class Meta:
        db_table = "catalog_class_name"
        verbose_name = _("Class")
        verbose_name_plural = _("Classes")
        ordering = ['name']
        default_related_name = "class_name"


class OrderQuerySet(TaxonomicQuerySet):
    __rank_name__ = "order"


class Order(TaxonomicModel):
    name = models.CharField(verbose_name=_("Name"), max_length=300, blank=True, null=True)
    class_name = models.ForeignKey(ClassName, verbose_name=_("Class Name"), on_delete=models.CASCADE, blank=True, null=True, help_text="Clase")

    objects = OrderQuerySet.as_manager()

    def __hash__(self):
        return super().__hash__()

    def __eq__(self, other):
        return super().__eq__(other) and \
            self.class_name == other.class_name and \
            self.name == other.name

    def __unicode__(self):
        return u"%s" % self.name

    def __str__(self):
        return "%s" % self.name

    def __repr__(self):
        return "%s|Class::%s" % (self.name, self.class_name)

    @staticmethod
    def get_query_name(search: str) -> Q:
        return TaxonomicModel.get_query_name(search)

    @staticmethod
    def get_parent_query(search: str) -> Q:
        return Q(class_name__name__icontains=search)

    @staticmethod
    def get_created_by_query(search: str) -> Q:
        return TaxonomicModel.get_created_by_query(search)

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
        null=True, help_text="order", db_column="order"
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
    scientific_name_db = models.CharField(verbose_name=_("Scientific Name Database"), max_length=300, blank=True, null=True)
    scientific_name_full = models.CharField(verbose_name=_("Complete Scientific Name"), max_length=800, blank=True, null=True)
    genus = models.CharField(verbose_name=_("Genus"), max_length=300, blank=True, null=True)
    specific_epithet = models.CharField(verbose_name=_("Specific Epithet"), max_length=300, blank=True, null=True, help_text="EpitetoEspecifico")
    scientific_name_authorship = models.CharField(verbose_name=_("Scientific Name Authorship"), max_length=500, blank=True, null=True, help_text="AutoresSp")
    subspecies = models.CharField(verbose_name=_("Subspecies"), max_length=300, blank=True, null=True)
    ssp_authorship = models.CharField(verbose_name=_("Subspecies Authorship"), max_length=500, blank=True, null=True)
    variety = models.CharField(verbose_name=_("Variety"), max_length=300, blank=True, null=True)
    variety_authorship = models.CharField(verbose_name=_("Variety Authorship"), max_length=500, blank=True, null=True)
    form = models.CharField(verbose_name=pgettext_lazy("taxonomic", "Form"), max_length=300, blank=True, null=True)
    form_authorship = models.CharField(verbose_name=_("Form Authorship"), max_length=500, blank=True, null=True)

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

    class Meta:
        abstract = True


class SynonymyQuerySet(AttributeQuerySet):
    __attribute_name__ = "synonymy"

    def search(self, text: str) -> AttributeQuerySet:
        return self.filter(scientific_name_full__icontains=text)


class Synonymy(ScientificName):
    objects = SynonymyQuerySet.as_manager()

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if "species" in kwargs:
            species: Species = kwargs["species"]
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


class CommonNameQuerySet(AttributeQuerySet):
    __attribute_name__ = "common_names"


class CommonName(TaxonomicModel):
    name = models.CharField(verbose_name=_("Name"), max_length=300, blank=True, null=True)

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

    @staticmethod
    def get_query_name(search: str) -> Q:
        return TaxonomicModel.get_query_name(search)

    @staticmethod
    def get_parent_query(search: str) -> Q:
        return Q(species__scientific_name__icontains=search)

    @staticmethod
    def get_created_by_query(search: str) -> Q:
        return TaxonomicModel.get_created_by_query(search)

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
        "publication": "publicación",
        "volume": "volume",
        "pages": "páginas",
        "year": "año de publicación",
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
    publication = models.CharField(verbose_name=_("Publication"), max_length=300, blank=True, null=True)
    volume = models.CharField(verbose_name=_("Volume"), max_length=300, blank=True, null=True)
    pages = models.CharField(verbose_name=_("Pages"), max_length=300, blank=True, null=True)
    year = models.IntegerField(verbose_name=_("Year"), blank=True, null=True)
    synonyms = models.ManyToManyField(Synonymy, verbose_name=_("Synonyms"), blank=True)
    region = models.ManyToManyField(Region, verbose_name=_("Regions"), blank=True, db_column="region")
    id_mma = models.IntegerField(verbose_name=_("MMA ID"), blank=True, null=True,
                                 help_text=_("ID of the species platform of the MMA"))
    conservation_state = models.ManyToManyField(ConservationState, verbose_name=_("Conservation State"), blank=True)
    determined = models.BooleanField(verbose_name=_("Determined?"), default=False)
    id_taxa_origin = models.IntegerField(verbose_name=_("ID Taxa of Origin"), blank=True, null=True, help_text="")

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
    def class_name(self):
        return self.order.class_name

    @property
    def division(self):
        return self.class_name.division

    @property
    def kingdom(self):
        return self.division.kingdom

    @staticmethod
    def get_parent_query(search: str) -> Q:
        return Q(genus__name__icontains=search)

    @staticmethod
    def get_created_by_query(search: str) -> Q:
        return TaxonomicModel.get_created_by_query(search)

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
                    try:
                        self.__prev__.save(user=kwargs["user"])
                        self.synonyms.add(self.__prev__)
                    except Exception as e:
                        logging.error("Error saving synonymy\n{}".format(e), exc_info=True)
                if len(self.__difference__(self.__original__)) > 0:
                    kwargs["notes"] = "Actualización de {}".format(
                        "; ".join(self.__difference__(self.__original__))
                    )
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


class CatalogView(TaxonomicModel):
    """
    CREATE MATERIALIZED VIEW catalog_view AS
    SELECT species.id,
           species.id_taxa,
           kingdom.id      AS kingdom_id,
           kingdom.name    AS kingdom,
           division.id     AS division_id,
           division.name   AS division,
           class.id        AS class_name_id,
           class.name      AS class_name,
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
           species.publication,
           species.volume,
           species.pages,
           species.year,
           species.determined,
           species.id_taxa_origin,
           species.created_at,
           species.updated_at,
           "user".username AS created_by
    FROM catalog_species species
         JOIN auth_user "user" ON species.created_by_id = "user".id
         JOIN catalog_genus genus ON species.genus_id = genus.id
         JOIN catalog_family family ON genus.family_id = family.id
         JOIN catalog_order "order" ON family."order" = "order".id
         JOIN catalog_class_name class ON "order".class_name_id = class.id
         JOIN catalog_division division ON class.division_id = division.id
         JOIN catalog_kingdom kingdom ON division.kingdom_id = kingdom.id
         LEFT JOIN catalog_status status ON species.status_id = status.id;

    CREATE UNIQUE INDEX catalog_view_id_idx
        ON catalog_view (id);
    """
    id = models.IntegerField(primary_key=True, blank=False, null=False, help_text="")
    id_taxa = models.IntegerField(blank=False, null=False, help_text="")
    kingdom_id = models.IntegerField(blank=False, null=False, help_text="")
    kingdom = models.CharField(max_length=300, blank=True, null=True)
    division_id = models.IntegerField(blank=False, null=False, help_text="")
    division = models.CharField(max_length=300, blank=True, null=True)
    class_name_id = models.IntegerField(blank=False, null=False, help_text="")
    class_name = models.CharField(max_length=300, blank=True, null=True)
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
    publication = models.CharField(max_length=300, blank=True, null=True)
    volume = models.CharField(max_length=300, blank=True, null=True)
    pages = models.CharField(max_length=300, blank=True, null=True)
    year = models.IntegerField(blank=True, null=True)
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
           species.id               AS specie_id,
           species.id_taxa,
           species.scientific_name AS specie_scientific_name,
           species_synonymy.id      AS synonymy_id,
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
        LEFT JOIN catalog_species_synonyms species_synonymy ON species_synonymy.synonymy_id = synonymy.id
        LEFT JOIN catalog_species species ON species_synonymy.species_id = species.id
        LEFT JOIN auth_user "user" ON synonymy.created_by_id = "user".id;

    CREATE UNIQUE INDEX synonymy_view_id_idx
        ON synonymy_view (synonymy_id);
    """
    id = models.IntegerField(primary_key=True, blank=False, null=False, help_text="")
    specie_id = models.IntegerField(blank=False, null=False, help_text="")
    id_taxa = models.IntegerField(blank=False, null=False, help_text="")
    specie_scientific_name = models.CharField(max_length=500, blank=True, null=True, help_text="sp")
    synonymy_id = models.IntegerField(blank=False, null=False, help_text="")
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
        return Q(specie_scientific_name__icontains=search)

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
    SELECT id,
           'species'       AS type,
           scientific_name AS name,
           scientific_name AS name_es,
           scientific_name AS name_en,
           determined
    FROM catalog_species
    UNION ALL
    SELECT id,
           'synonymy'      AS type,
           scientific_name AS name,
           scientific_name AS name_es,
           scientific_name AS name_en,
           FALSE           AS determined
    FROM catalog_synonymy
    UNION ALL
    SELECT id,
           'family'        AS type,
           name            AS name,
           name            AS name_es,
           name            AS name_en,
           FALSE           AS determined
    FROM catalog_family
    UNION ALL
    SELECT id,
           'genus'         AS type,
           name            AS name,
           name            AS name_es,
           name            AS name_en,
           FALSE           AS determined
    FROM catalog_genus
    UNION ALL
    SELECT id,
           'common_name'   AS type,
           name,
           name_es,
           name_en,
           FALSE           AS determined
    FROM catalog_commonname
    ORDER BY type, name;

    CREATE UNIQUE INDEX finder_view_id
        ON finder_view (id, type);

    CREATE INDEX finder_view_trgm_es_id
        ON finder_view USING gin(name_es gin_trgm_ops);

    CREATE INDEX finder_view_trgm_en_id
        ON finder_view USING gin(name_en gin_trgm_ops);
    """
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
