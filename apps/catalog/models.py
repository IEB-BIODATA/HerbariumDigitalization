from django.db import models
from django.contrib.auth.models import User
from django.db import connection


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


class Ciclo(models.Model):
    name = models.CharField(max_length=300, blank=True, null=True)
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


class Kingdom(models.Model):
    name = models.CharField(max_length=300, blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True, blank=True, null=True, editable=False)
    updated_at = models.DateTimeField(auto_now=True)
    created_by = models.ForeignKey(User, on_delete=models.PROTECT, default=1, editable=False)

    def __unicode__(self):
        return self.name

    def __str__(self):
        return "%s " % self.name

    class Meta:
        verbose_name_plural = "Kingdoms"
        ordering = ['name']


class Division(models.Model):
    name = models.CharField(max_length=300, blank=True, null=True)
    kingdom = models.ForeignKey(Kingdom, on_delete=models.CASCADE, blank=True, null=True, help_text="Reino")
    created_at = models.DateTimeField(auto_now_add=True, blank=True, null=True, editable=False)
    updated_at = models.DateTimeField(auto_now=True)
    created_by = models.ForeignKey(User, on_delete=models.PROTECT, default=1, editable=False)

    def __unicode__(self):
        return self.name

    def __str__(self):
        return "%s " % self.name

    class Meta:
        verbose_name_plural = "Divisions"
        ordering = ['name']


class Class_name(models.Model):
    name = models.CharField(max_length=300, blank=True, null=True)
    division = models.ForeignKey(Division, on_delete=models.CASCADE, blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True, blank=True, null=True, editable=False)
    updated_at = models.DateTimeField(auto_now=True)
    created_by = models.ForeignKey(User, on_delete=models.PROTECT, default=1, editable=False)

    def __unicode__(self):
        return self.name

    def __str__(self):
        return "%s " % self.name

    class Meta:
        verbose_name_plural = "Classes"
        ordering = ['name']


class Order(models.Model):
    name = models.CharField(max_length=300, blank=True, null=True)
    class_name = models.ForeignKey(Class_name, on_delete=models.CASCADE, blank=True, null=True, help_text="Clase")
    created_at = models.DateTimeField(auto_now_add=True, blank=True, null=True, editable=False)
    updated_at = models.DateTimeField(auto_now=True)
    created_by = models.ForeignKey(User, on_delete=models.PROTECT, default=1, editable=False)

    def __unicode__(self):
        return self.name

    def __str__(self):
        return "%s " % self.name

    class Meta:
        verbose_name_plural = "Orders"
        ordering = ['name']


class Family(models.Model):
    name = models.CharField(max_length=300, blank=True, null=True)
    orden = models.ForeignKey(Order, on_delete=models.CASCADE, blank=True, null=True, help_text="Orden")
    created_at = models.DateTimeField(auto_now_add=True, blank=True, null=True, editable=False)
    updated_at = models.DateTimeField(auto_now=True)
    created_by = models.ForeignKey(User, on_delete=models.PROTECT, default=1, editable=False)

    def __unicode__(self):
        return self.name

    def __str__(self):
        return "%s " % self.name

    class Meta:
        verbose_name_plural = "Familys"
        ordering = ['name']


class Genus(models.Model):
    name = models.CharField(max_length=300, blank=True, null=True)
    family = models.ForeignKey(Family, on_delete=models.CASCADE, blank=True, null=True, help_text="Familia")
    created_at = models.DateTimeField(auto_now_add=True, blank=True, null=True, editable=False)
    updated_at = models.DateTimeField(auto_now=True)
    created_by = models.ForeignKey(User, on_delete=models.PROTECT, default=1, editable=False)

    def __unicode__(self):
        return self.name

    def __str__(self):
        return "%s " % self.name

    class Meta:
        verbose_name_plural = "Genus"
        ordering = ['name']


class Habit(models.Model):
    name = models.CharField(max_length=300, blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True, blank=True, null=True, editable=False)
    updated_at = models.DateTimeField(auto_now=True)
    created_by = models.ForeignKey(User, on_delete=models.PROTECT, default=1, editable=False)

    def __unicode__(self):
        return self.name

    def __str__(self):
        return "%s " % self.name

    class Meta:
        verbose_name_plural = "Habits"
        ordering = ['name']


class Synonymy(models.Model):
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

    class Meta:
        verbose_name_plural = "Synonyms"
        ordering = ['scientificName']


class CommonName(models.Model):
    name = models.CharField(max_length=300, blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True, blank=True, null=True, editable=False)
    updated_at = models.DateTimeField(auto_now=True)
    created_by = models.ForeignKey(User, on_delete=models.PROTECT, default=1, editable=False)

    def __unicode__(self):
        return self.name

    def __str__(self):
        return "%s " % self.name

    class Meta:
        verbose_name_plural = "Common Names"
        ordering = ['name']


class Region(models.Model):
    name = models.CharField(max_length=300, blank=True, null=True)
    key = models.CharField(max_length=3, blank=True, null=True)
    order = models.IntegerField(blank=True, null=True)
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
    order = models.IntegerField(blank=True, null=True)
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


class Species(models.Model):
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
    habito = models.ForeignKey(Habit, on_delete=models.CASCADE, blank=True, null=True)
    ciclo = models.ForeignKey(Ciclo, on_delete=models.CASCADE, blank=True, null=True)
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
    region_distribution = models.ManyToManyField(Region, blank=True)
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

    def orden(self):
        return self.genus.family.orden

    def class_name(self):
        return self.genus.family.orden.class_name

    def division(self):
        return self.genus.family.orden.class_name.division

    def kingdom(self):
        return self.genus.family.orden.class_name.division.kingdom

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


class CatalogView(models.Model):
    id = models.IntegerField(primary_key=True, blank=False, null=False, help_text="")
    id_taxa = models.IntegerField(blank=False, null=False, help_text="")
    kingdom = models.CharField(max_length=300, blank=True, null=True)
    division = models.CharField(max_length=300, blank=True, null=True)
    class_name = models.CharField(max_length=300, blank=True, null=True)
    orden = models.CharField(max_length=300, blank=True, null=True)
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
    habito = models.CharField(max_length=300, blank=True, null=True)
    ciclo = models.CharField(max_length=300, blank=True, null=True)
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
            cursor.execute("REFRESH MATERIALIZED VIEW CONCURRENTLY region_distribution_view")

    class Meta:
        managed = False
        db_table = 'region_distribution_view'
