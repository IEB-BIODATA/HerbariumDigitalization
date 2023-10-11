from __future__ import annotations
import logging
from abc import abstractmethod
from copy import deepcopy
from typing import List

from django.db import models
from django.contrib.auth.models import User
from django.db import connection
from django.db.models import Q


class Status(models.Model):
    name = models.CharField(max_length=300, blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True, blank=True, null=True, editable=False)
    updated_at = models.DateTimeField(auto_now=True)
    created_by = models.ForeignKey(User, on_delete=models.PROTECT, default=1, editable=False)

    def __unicode__(self):
        return u"%s" % self.name

    def __str__(self):
        return "%s" % self.name

    def __repr__(self):
        return "Status::%s" % self.name

    class Meta:
        verbose_name_plural = "Status"
        ordering = ['name']


class Cycle(models.Model):
    name = models.CharField(max_length=100, blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True, blank=True, null=True, editable=False)
    updated_at = models.DateTimeField(auto_now=True)
    created_by = models.ForeignKey(User, on_delete=models.PROTECT, default=1, editable=False)

    def __unicode__(self):
        return u"%s" % self.name

    def __str__(self):
        return "%s" % self.name

    def __repr__(self):
        return "Cycle::%s" % self.name

    class Meta:
        verbose_name_plural = "Ciclos"
        ordering = ['name']


class TaxonomicModel(models.Model):
    created_at = models.DateTimeField(auto_now_add=True, blank=True, null=True, editable=False)
    updated_at = models.DateTimeField(auto_now=True)
    created_by = models.ForeignKey(User, on_delete=models.PROTECT, default=1, editable=False)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if self.id is not None:
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
        if self.id is None:
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


class Kingdom(TaxonomicModel):
    name = models.CharField(max_length=300, blank=True, null=True)

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
        verbose_name_plural = "Kingdoms"
        ordering = ['name']


class Division(TaxonomicModel):
    name = models.CharField(max_length=300, blank=True, null=True)
    kingdom = models.ForeignKey(Kingdom, on_delete=models.CASCADE, blank=True, null=True, help_text="Reino")

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
        verbose_name_plural = "Divisions"
        ordering = ['name']


class ClassName(TaxonomicModel):
    name = models.CharField(max_length=300, blank=True, null=True)
    division = models.ForeignKey(Division, on_delete=models.CASCADE, blank=True, null=True)

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
        verbose_name_plural = "Classes"
        ordering = ['name']
        default_related_name = "class_name"


class Order(TaxonomicModel):
    name = models.CharField(max_length=300, blank=True, null=True)
    class_name = models.ForeignKey(ClassName, on_delete=models.CASCADE, blank=True, null=True, help_text="Clase")

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
        verbose_name_plural = "Orders"
        ordering = ['name']


class Family(TaxonomicModel):
    name = models.CharField(max_length=300, blank=True, null=True)
    order = models.ForeignKey(
        Order, on_delete=models.CASCADE, blank=True,
        null=True, help_text="order", db_column="order"
    )

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
        verbose_name_plural = "Familys"
        ordering = ['name']


class Genus(TaxonomicModel):
    name = models.CharField(max_length=300, blank=True, null=True)
    family = models.ForeignKey(Family, on_delete=models.CASCADE, blank=True, null=True, help_text="Familia")

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
        verbose_name_plural = "Genus"
        ordering = ['name']


class PlantHabit(models.Model):
    name = models.CharField(max_length=100, blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True, blank=True, null=True, editable=False)
    updated_at = models.DateTimeField(auto_now=True)
    created_by = models.ForeignKey(User, on_delete=models.PROTECT, default=1, editable=False)

    def __unicode__(self):
        return u"%s" % self.name

    def __str__(self):
        return "%s" % self.name

    def __repr__(self):
        return "Plant Habit::%s" % self.name

    class Meta:
        verbose_name_plural = "Plant Habits"
        ordering = ['name']


class EnvironmentalHabit(models.Model):
    female_name = models.CharField(max_length=100, blank=True, null=True)
    male_name = models.CharField(max_length=100, blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True, blank=True, null=True, editable=False)
    updated_at = models.DateTimeField(auto_now=True)
    created_by = models.ForeignKey(User, on_delete=models.PROTECT, default=1, editable=False)

    def __unicode__(self):
        return u"%s" % self.__str__()

    def __str__(self):
        return "%s / %s" % (self.female_name, self.male_name)

    def __repr__(self):
        return "Environmental Habit::%s" % self.__str__()

    class Meta:
        verbose_name_plural = "Environmental Habits"
        ordering = ['female_name']


class ScientificName(TaxonomicModel):
    scientific_name = models.CharField(max_length=300, blank=True, null=True)
    scientific_name_db = models.CharField(max_length=300, blank=True, null=True)
    scientific_name_full = models.CharField(max_length=800, blank=True, null=True)
    genus = models.CharField(max_length=300, blank=True, null=True)
    specific_epithet = models.CharField(max_length=300, blank=True, null=True, help_text="EpitetoEspecifico")
    scientific_name_authorship = models.CharField(max_length=500, blank=True, null=True, help_text="AutoresSp")
    subspecies = models.CharField(max_length=300, blank=True, null=True)
    ssp_authorship = models.CharField(max_length=500, blank=True, null=True)
    variety = models.CharField(max_length=300, blank=True, null=True)
    variety_authorship = models.CharField(max_length=500, blank=True, null=True)
    form = models.CharField(max_length=300, blank=True, null=True)
    form_authorship = models.CharField(max_length=500, blank=True, null=True)

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


class Synonymy(ScientificName):
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
            self.variety_authorship = species.variety_authorship
            self.form = species.form
            self.form_authorship = species.form_authorship

    @staticmethod
    def get_query_name(search: str) -> Q:
        return Q(scientific_name_full__icontains=search)

    @staticmethod
    def get_parent_query(search: str) -> Q:
        return Q(species__scientific_name__icontains=search)

    @staticmethod
    def get_created_by_query(search: str) -> Q:
        return TaxonomicModel.get_created_by_query(search)

    def save(self, force_insert=False, force_update=False, using=None, update_fields=None, **kwargs):
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
        verbose_name_plural = "Synonyms"
        ordering = ['scientific_name']


class CommonName(TaxonomicModel):
    name = models.CharField(max_length=300, blank=True, null=True)

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
        verbose_name_plural = "Common Names"
        ordering = ['name']


class Region(models.Model):
    name = models.CharField(max_length=300, blank=True, null=True)
    key = models.CharField(max_length=3, blank=True, null=True)
    order = models.IntegerField(blank=True, null=True, db_column="order")
    created_at = models.DateTimeField(auto_now_add=True, blank=True, null=True, editable=False)
    updated_at = models.DateTimeField(auto_now=True)
    created_by = models.ForeignKey(User, on_delete=models.PROTECT, default=1, editable=False)

    def __unicode__(self):
        return u"%s" % self.name

    def __str__(self):
        return "%s " % self.name

    def __repr__(self):
        return "Region::%s" % self.name

    class Meta:
        verbose_name_plural = "Regions"
        ordering = ['order']


class ConservationState(models.Model):
    name = models.CharField(max_length=300, blank=True, null=True)
    key = models.CharField(max_length=3, blank=True, null=True)
    order = models.IntegerField(blank=True, null=True, db_column="order")
    created_at = models.DateTimeField(auto_now_add=True, blank=True, null=True, editable=False)
    updated_at = models.DateTimeField(auto_now=True)
    created_by = models.ForeignKey(User, on_delete=models.PROTECT, default=1, editable=False)

    def __unicode__(self):
        return u"%s" % self.name

    def __str__(self):
        return "%s" % self.name

    def __repr__(self):
        return "Conservation State::%s" % self.name

    class Meta:
        verbose_name_plural = "Conservation States"
        ordering = ['order']


class Species(ScientificName):
    objects = None
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

    id_taxa = models.IntegerField(blank=True, null=True, help_text="")
    genus = models.ForeignKey(Genus, on_delete=models.CASCADE, blank=True, null=True, help_text="Género")
    common_names = models.ManyToManyField(CommonName, blank=True)
    in_argentina = models.BooleanField(default=False)
    in_bolivia = models.BooleanField(default=False)
    in_peru = models.BooleanField(default=False)
    plant_habit = models.ManyToManyField(PlantHabit, blank=True, db_column="plant_habit")
    env_habit = models.ManyToManyField(EnvironmentalHabit, blank=True, db_column="environmental_habit")
    cycle = models.ManyToManyField(Cycle, blank=True, db_column="cycle")
    status = models.ForeignKey(Status, on_delete=models.CASCADE, blank=True, null=True)
    minimum_height = models.IntegerField(blank=True, null=True)
    maximum_height = models.IntegerField(blank=True, null=True)
    notes = models.CharField(max_length=1000, blank=True, null=True)
    type_id = models.CharField(max_length=300, blank=True, null=True)
    publication = models.CharField(max_length=300, blank=True, null=True)
    volume = models.CharField(max_length=300, blank=True, null=True)
    pages = models.CharField(max_length=300, blank=True, null=True)
    year = models.IntegerField(blank=True, null=True)
    synonyms = models.ManyToManyField(Synonymy, blank=True)
    region = models.ManyToManyField(Region, blank=True, db_column="region")
    id_mma = models.IntegerField(blank=True, null=True, help_text="")
    conservation_state = models.ManyToManyField(ConservationState, blank=True)
    determined = models.BooleanField(default=False)
    id_taxa_origin = models.IntegerField(blank=True, null=True, help_text="")

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if self.id is not None:
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

    def family(self):
        return self.genus.family

    def order(self):
        return self.genus.family.order

    def class_name(self):
        return self.genus.family.order.class_name

    def division(self):
        return self.genus.family.order.class_name.division

    def kingdom(self):
        return self.genus.family.order.class_name.division.kingdom

    @staticmethod
    def get_query_name(search: str) -> Q:
        return Q(scientific_name_full__icontains=search)

    @staticmethod
    def get_parent_query(search: str) -> Q:
        return Q(genus__name__icontains=search)

    @staticmethod
    def get_created_by_query(search: str) -> Q:
        return TaxonomicModel.get_created_by_query(search)

    def save(self, force_insert=False, force_update=False, using=None, update_fields=None, **kwargs):
        self.__update_scientific_name__()
        if self.__prev__ is not None:
            if self.__original__ != self:
                if self.__original__.scientific_name != self.scientific_name or \
                        self.__original__.scientific_name_full != self.scientific_name_full:
                    if self.__original__.scientific_name_full != self.scientific_name_full:
                        logging.debug("Name changed")
                        logging.debug("Listing specimen")
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
        verbose_name_plural = "Species"
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
    description = models.CharField(max_length=1000, blank=True, null=True, help_text="descripción")
    note = models.CharField(max_length=1000, blank=True, null=True, help_text="descripción")
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
            model.id
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
            model.id,
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
            model.id
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
           kingdom.name    AS kingdom,
           division.name   AS division,
           class.name      AS class_name,
           "order".name    AS "order",
           family.name     AS family,
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

    ALTER MATERIALIZED VIEW catalog_view OWNER TO <POSTGRES_USER>;

    CREATE UNIQUE INDEX catalog_view_id_idx
        ON catalog_view (id);
    """
    id = models.IntegerField(primary_key=True, blank=False, null=False, help_text="")
    id_taxa = models.IntegerField(blank=False, null=False, help_text="")
    kingdom = models.CharField(max_length=300, blank=True, null=True)
    division = models.CharField(max_length=300, blank=True, null=True)
    class_name = models.CharField(max_length=300, blank=True, null=True)
    order = models.CharField(max_length=300, blank=True, null=True, db_column="order")
    family = models.CharField(max_length=300, blank=True, null=True)
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
    def refresh_view(cl):
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

    ALTER MATERIALIZED VIEW synonymy_view OWNER TO <POSTGRES_USER>;

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
    def refresh_view(cl):
        with connection.cursor() as cursor:
            cursor.execute("REFRESH MATERIALIZED VIEW CONCURRENTLY synonymy_view")

    class Meta:
        managed = False
        db_table = 'synonymy_view'


class RegionDistributionView(models.Model):
    """
    CREATE MATERIALIZED VIEW region_view AS
    SELECT species_region.id,
           species.id               AS specie_id,
           species.id_taxa,
           species."scientific_name" AS specie_scientific_name,
           region.name              AS region_name,
           region.key               AS region_key
    FROM catalog_species_region species_region
         JOIN catalog_species species ON species_region.species_id = species.id
         JOIN catalog_region region ON species_region.region_id = region.id
    ORDER BY species_region.id;

    ALTER MATERIALIZED VIEW region_view OWNER TO <POSTGRES_USER>;

    CREATE UNIQUE INDEX region_distribution_view_id_idx
        ON region_view (id);
    """
    id = models.IntegerField(primary_key=True, blank=False, null=False, help_text="")
    specie_id = models.IntegerField(blank=False, null=False, help_text="")
    id_taxa = models.IntegerField(blank=False, null=False, help_text="")
    specie_scientific_name = models.CharField(max_length=500, blank=True, null=True, help_text="sp")
    region_name = models.CharField(max_length=300, blank=True, null=True)
    region_key = models.CharField(max_length=3, blank=True, null=True)

    @classmethod
    def refresh_view(cl):
        with connection.cursor() as cursor:
            cursor.execute("REFRESH MATERIALIZED VIEW CONCURRENTLY region_view")

    class Meta:
        managed = False
        db_table = 'region_view'
