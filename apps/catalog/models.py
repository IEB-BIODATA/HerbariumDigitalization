from abc import abstractmethod

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
        return self.name

    def __str__(self):
        return "%s " % self.name

    class Meta:
        verbose_name_plural = "Status"
        ordering = ['name']


class Cycle(models.Model):
    name = models.CharField(max_length=100, blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True, blank=True, null=True, editable=False)
    updated_at = models.DateTimeField(auto_now=True)
    created_by = models.ForeignKey(User, on_delete=models.PROTECT, default=1, editable=False)

    def __unicode__(self):
        return self.name

    def __str__(self):
        return "%s " % self.name

    class Meta:
        verbose_name_plural = "Ciclos"
        ordering = ['name']


class TaxonomicModel(models.Model):

    class Meta:
        abstract = True

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


class Kingdom(TaxonomicModel):
    name = models.CharField(max_length=300, blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True, blank=True, null=True, editable=False)
    updated_at = models.DateTimeField(auto_now=True)
    created_by = models.ForeignKey(User, on_delete=models.PROTECT, default=1, editable=False)

    def __unicode__(self):
        return self.name

    def __str__(self):
        return "%s " % self.name

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
    created_at = models.DateTimeField(auto_now_add=True, blank=True, null=True, editable=False)
    updated_at = models.DateTimeField(auto_now=True)
    created_by = models.ForeignKey(User, on_delete=models.PROTECT, default=1, editable=False)

    def __unicode__(self):
        return self.name

    def __str__(self):
        return "%s " % self.name

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
    created_at = models.DateTimeField(auto_now_add=True, blank=True, null=True, editable=False)
    updated_at = models.DateTimeField(auto_now=True)
    created_by = models.ForeignKey(User, on_delete=models.PROTECT, default=1, editable=False)

    def __unicode__(self):
        return self.name

    def __str__(self):
        return "%s " % self.name

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


class Order(TaxonomicModel):
    name = models.CharField(max_length=300, blank=True, null=True)
    class_name = models.ForeignKey(ClassName, on_delete=models.CASCADE, blank=True, null=True, help_text="Clase")
    created_at = models.DateTimeField(auto_now_add=True, blank=True, null=True, editable=False)
    updated_at = models.DateTimeField(auto_now=True)
    created_by = models.ForeignKey(User, on_delete=models.PROTECT, default=1, editable=False)

    def __unicode__(self):
        return self.name

    def __str__(self):
        return "%s " % self.name

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
    created_at = models.DateTimeField(auto_now_add=True, blank=True, null=True, editable=False)
    updated_at = models.DateTimeField(auto_now=True)
    created_by = models.ForeignKey(User, on_delete=models.PROTECT, default=1, editable=False)

    @staticmethod
    def get_query_name(search: str) -> Q:
        return TaxonomicModel.get_query_name(search)

    @staticmethod
    def get_parent_query(search: str) -> Q:
        return Q(order__name__icontains=search)

    @staticmethod
    def get_created_by_query(search: str) -> Q:
        return TaxonomicModel.get_created_by_query(search)

    def __unicode__(self):
        return self.name

    def __str__(self):
        return "%s " % self.name

    class Meta:
        verbose_name_plural = "Familys"
        ordering = ['name']


class Genus(TaxonomicModel):
    name = models.CharField(max_length=300, blank=True, null=True)
    family = models.ForeignKey(Family, on_delete=models.CASCADE, blank=True, null=True, help_text="Familia")
    created_at = models.DateTimeField(auto_now_add=True, blank=True, null=True, editable=False)
    updated_at = models.DateTimeField(auto_now=True)
    created_by = models.ForeignKey(User, on_delete=models.PROTECT, default=1, editable=False)

    def __unicode__(self):
        return self.name

    def __str__(self):
        return "%s " % self.name

    @staticmethod
    def get_query_name(search: str) -> Q:
        return TaxonomicModel.get_query_name(search)

    @staticmethod
    def get_parent_query(search: str) -> Q:
        return Q(family__name__icontains=search)

    @staticmethod
    def get_created_by_query(search: str) -> Q:
        return TaxonomicModel.get_created_by_query(search)

    class Meta:
        verbose_name_plural = "Genus"
        ordering = ['name']


class PlantHabit(models.Model):
    name = models.CharField(max_length=100, blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True, blank=True, null=True, editable=False)
    updated_at = models.DateTimeField(auto_now=True)
    created_by = models.ForeignKey(User, on_delete=models.PROTECT, default=1, editable=False)

    def __unicode__(self):
        return self.name

    def __str__(self):
        return "%s " % self.name

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
        return self.__str__()

    def __str__(self):
        return "%s / %s" % (self.female_name, self.male_name)

    class Meta:
        verbose_name_plural = "Environmental Habits"
        ordering = ['female_name']


class Synonymy(TaxonomicModel):
    scientificName = models.CharField(max_length=300, blank=True, null=True)
    scientificNameDB = models.CharField(max_length=300, blank=True, null=True)
    scientificNameFull = models.CharField(max_length=800, blank=True, null=True)
    genus = models.CharField(max_length=300, blank=True, null=True)
    specificEpithet = models.CharField(max_length=300, blank=True, null=True, help_text="EpitetoEspecifico")
    scientificNameAuthorship = models.CharField(max_length=500, blank=True, null=True, help_text="AutoresSp")
    subespecie = models.CharField(max_length=300, blank=True, null=True)
    autoresSsp = models.CharField(max_length=500, blank=True, null=True)
    variedad = models.CharField(max_length=300, blank=True, null=True)
    autoresVariedad = models.CharField(max_length=500, blank=True, null=True)
    forma = models.CharField(max_length=300, blank=True, null=True)
    autoresForma = models.CharField(max_length=500, blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True, blank=True, null=True, editable=False)
    updated_at = models.DateTimeField(auto_now=True)
    created_by = models.ForeignKey(User, on_delete=models.PROTECT, default=1, editable=False)

    def __unicode__(self):
        return self.scientificName

    def __str__(self):
        return "%s " % self.scientificNameFull

    @staticmethod
    def get_query_name(search: str) -> Q:
        return Q(scientificNameFull__icontains=search)

    @staticmethod
    def get_parent_query(search: str) -> Q:
        return Q(species__scientificName__icontains=search)

    @staticmethod
    def get_created_by_query(search: str) -> Q:
        return TaxonomicModel.get_created_by_query(search)

    class Meta:
        verbose_name_plural = "Synonyms"
        ordering = ['scientificName']


class CommonName(TaxonomicModel):
    name = models.CharField(max_length=300, blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True, blank=True, null=True, editable=False)
    updated_at = models.DateTimeField(auto_now=True)
    created_by = models.ForeignKey(User, on_delete=models.PROTECT, default=1, editable=False)

    def __unicode__(self):
        return self.name

    def __str__(self):
        return "%s " % self.name

    @staticmethod
    def get_query_name(search: str) -> Q:
        return TaxonomicModel.get_query_name(search)

    @staticmethod
    def get_parent_query(search: str) -> Q:
        return Q(species__scientificName__icontains=search)

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
        return self.name

    def __str__(self):
        return "%s " % self.name

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
        return self.name

    def __str__(self):
        return "%s " % self.name

    class Meta:
        verbose_name_plural = "Conservation States"
        ordering = ['order']


class Species(TaxonomicModel):
    id_taxa = models.IntegerField(blank=True, null=True, help_text="")
    genus = models.ForeignKey(Genus, on_delete=models.CASCADE, blank=True, null=True, help_text="Género")
    scientificName = models.CharField(max_length=500, blank=True, null=True, help_text="sp")
    scientificNameDB = models.CharField(max_length=500, blank=True, null=True, help_text="spdb")
    scientificNameFull = models.CharField(max_length=800, blank=True, null=True, help_text="spCompleto")
    specificEpithet = models.CharField(max_length=300, blank=True, null=True, help_text="EpitetoEspecifico")
    scientificNameAuthorship = models.CharField(max_length=500, blank=True, null=True, help_text="AutoresSp")
    subespecie = models.CharField(max_length=300, blank=True, null=True)
    autoresSsp = models.CharField(max_length=500, blank=True, null=True)
    variedad = models.CharField(max_length=300, blank=True, null=True)
    autoresVariedad = models.CharField(max_length=500, blank=True, null=True)
    forma = models.CharField(max_length=300, blank=True, null=True)
    autoresForma = models.CharField(max_length=500, blank=True, null=True)
    common_names = models.ManyToManyField(CommonName, blank=True)
    enArgentina = models.BooleanField(default=False)
    enBolivia = models.BooleanField(default=False)
    enPeru = models.BooleanField(default=False)
    plant_habit = models.ManyToManyField(
        PlantHabit, blank=True,
        db_column="plant_habit"
    )
    env_habit = models.ManyToManyField(
        EnvironmentalHabit, blank=True,
        db_column="environmental_habit"
    )
    cycle = models.ManyToManyField(
        Cycle, blank=True,
        db_column="cycle"
    )
    status = models.ForeignKey(Status, on_delete=models.CASCADE, blank=True, null=True)
    alturaMinima = models.IntegerField(blank=True, null=True)
    alturaMaxima = models.IntegerField(blank=True, null=True)
    notas = models.CharField(max_length=1000, blank=True, null=True)
    id_tipo = models.CharField(max_length=300, blank=True, null=True)
    publicacion = models.CharField(max_length=300, blank=True, null=True)
    volumen = models.CharField(max_length=300, blank=True, null=True)
    paginas = models.CharField(max_length=300, blank=True, null=True)
    anio = models.IntegerField(blank=True, null=True)
    synonymys = models.ManyToManyField(Synonymy, blank=True)
    region = models.ManyToManyField(Region, blank=True, db_column="region")
    id_mma = models.IntegerField(blank=True, null=True, help_text="")
    conservation_state = models.ManyToManyField(ConservationState, blank=True)
    created_at = models.DateTimeField(auto_now_add=True, blank=True, null=True, editable=False)
    updated_at = models.DateTimeField(auto_now=True)
    created_by = models.ForeignKey(User, on_delete=models.PROTECT, default=1, editable=False)
    determined = models.BooleanField(default=False)
    id_taxa_origin = models.IntegerField(blank=True, null=True, help_text="")

    class Meta:
        verbose_name_plural = "Species"
        ordering = ['scientificName']

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
        return Q(scientificNameFull__icontains=search)

    @staticmethod
    def get_parent_query(search: str) -> Q:
        return Q(genus__name__icontains=search)

    @staticmethod
    def get_created_by_query(search: str) -> Q:
        return TaxonomicModel.get_created_by_query(search)

    def __unicode__(self):
        return self.scientificName

    def __str__(self):
        return "%s " % self.scientificName


class Binnacle(models.Model):
    type_update = models.CharField(max_length=100, blank=True, null=True, help_text="tipo")
    model = models.CharField(max_length=100, blank=True, null=True, help_text="modelo")
    description = models.CharField(max_length=1000, blank=True, null=True, help_text="descripción")
    note = models.CharField(max_length=1000, blank=True, null=True, help_text="descripción")
    created_at = models.DateTimeField(auto_now_add=True, blank=True, null=True, editable=False)
    updated_at = models.DateTimeField(auto_now=True)
    created_by = models.ForeignKey(User, on_delete=models.PROTECT, default=1, editable=False)

    class Meta:
        verbose_name_plural = "Binnacles"
        ordering = ['updated_at']


class CatalogView(TaxonomicModel):
    id = models.IntegerField(primary_key=True, blank=False, null=False, help_text="")
    id_taxa = models.IntegerField(blank=False, null=False, help_text="")
    kingdom = models.CharField(max_length=300, blank=True, null=True)
    division = models.CharField(max_length=300, blank=True, null=True)
    class_name = models.CharField(max_length=300, blank=True, null=True)
    order = models.CharField(max_length=300, blank=True, null=True, db_column="order")
    family = models.CharField(max_length=300, blank=True, null=True)
    genus = models.CharField(max_length=300, blank=True, null=True)
    scientificName = models.CharField(max_length=500, blank=True, null=True, help_text="sp")
    scientificNameFull = models.CharField(max_length=800, blank=True, null=True, help_text="spCompleto")
    specificEpithet = models.CharField(max_length=300, blank=True, null=True, help_text="EpitetoEspecifico")
    scientificNameAuthorship = models.CharField(max_length=500, blank=True, null=True, help_text="AutoresSp")
    subespecie = models.CharField(max_length=300, blank=True, null=True)
    autoresSsp = models.CharField(max_length=500, blank=True, null=True)
    variedad = models.CharField(max_length=300, blank=True, null=True)
    autoresVariedad = models.CharField(max_length=500, blank=True, null=True)
    forma = models.CharField(max_length=300, blank=True, null=True)
    autoresForma = models.CharField(max_length=500, blank=True, null=True)
    enArgentina = models.BooleanField(default=False)
    enBolivia = models.BooleanField(default=False)
    enPeru = models.BooleanField(default=False)
    status = models.CharField(max_length=300, blank=True, null=True)
    alturaMinima = models.IntegerField(blank=True, null=True)
    alturaMaxima = models.IntegerField(blank=True, null=True)
    notas = models.CharField(max_length=1000, blank=True, null=True)
    id_tipo = models.CharField(max_length=300, blank=True, null=True)
    publicacion = models.CharField(max_length=300, blank=True, null=True)
    volumen = models.CharField(max_length=300, blank=True, null=True)
    paginas = models.CharField(max_length=300, blank=True, null=True)
    anio = models.IntegerField(blank=True, null=True)
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
        return Q(scientificNameFull__icontains=search)

    @staticmethod
    def get_parent_query(search: str) -> Q:
        return Q(genus__icontains=search)

    @staticmethod
    def get_created_by_query(search: str) -> Q:
        return Q(created_by__icontains=search)

    class Meta:
        managed = False
        db_table = 'catalog_view'


class SynonymyView(models.Model):
    id = models.IntegerField(primary_key=True, blank=False, null=False, help_text="")
    specie_id = models.IntegerField(blank=False, null=False, help_text="")
    id_taxa = models.IntegerField(blank=False, null=False, help_text="")
    specie_scientificname = models.CharField(max_length=500, blank=True, null=True, help_text="sp")
    synonymy_id = models.IntegerField(blank=False, null=False, help_text="")
    scientificName = models.CharField(max_length=300, blank=True, null=True)
    scientificNameFull = models.CharField(max_length=800, blank=True, null=True)
    genus = models.CharField(max_length=300, blank=True, null=True)
    specificEpithet = models.CharField(max_length=300, blank=True, null=True)
    scientificNameAuthorship = models.CharField(max_length=500, blank=True, null=True)
    subespecie = models.CharField(max_length=300, blank=True, null=True)
    autoresSsp = models.CharField(max_length=500, blank=True, null=True)
    variedad = models.CharField(max_length=300, blank=True, null=True)
    autoresVariedad = models.CharField(max_length=500, blank=True, null=True)
    forma = models.CharField(max_length=300, blank=True, null=True)
    autoresForma = models.CharField(max_length=300, blank=True, null=True)
    created_at = models.DateTimeField(blank=True, null=True, editable=False)
    updated_at = models.DateTimeField()
    created_by = models.CharField(max_length=300, blank=True, null=True)

    @classmethod
    def refresh_view(cl):
        with connection.cursor() as cursor:
            cursor.execute("REFRESH MATERIALIZED VIEW CONCURRENTLY synonymy_view")

    class Meta:
        managed = False
        db_table = 'synonymy_view'


class RegionDistributionView(models.Model):
    id = models.IntegerField(primary_key=True, blank=False, null=False, help_text="")
    specie_id = models.IntegerField(blank=False, null=False, help_text="")
    id_taxa = models.IntegerField(blank=False, null=False, help_text="")
    specie_scientificname = models.CharField(max_length=500, blank=True, null=True, help_text="sp")
    region_name = models.CharField(max_length=300, blank=True, null=True)
    region_key = models.CharField(max_length=3, blank=True, null=True)

    @classmethod
    def refresh_view(cl):
        with connection.cursor() as cursor:
            cursor.execute("REFRESH MATERIALIZED VIEW CONCURRENTLY region_view")

    class Meta:
        managed = False
        db_table = 'region_view'
