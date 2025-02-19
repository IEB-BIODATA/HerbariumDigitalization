from django.conf import settings
from django.contrib.gis.db.models import GeometryField
from django.utils.translation import gettext_lazy as _
from django.db import models
from eml.types import Role

from apps.digitalization.models import Licence


class GeographicCoverage(models.Model):
    west_bounding = models.FloatField(verbose_name=_("West Bounding"))
    east_bounding = models.FloatField(verbose_name=_("East Bounding"))
    north_bounding = models.FloatField(verbose_name=_("North Bounding"))
    south_bounding = models.FloatField(verbose_name=_("South Bounding"))
    description = models.TextField(verbose_name=_("Description"))
    bound = GeometryField(dim=2, blank=True, null=True, verbose_name=_("Bound"))

    class Meta:
        verbose_name = _("Geographic Coverage")
        verbose_name_plural = _("Geographic Coverages")


class TaxonID(models.Model):
    taxon_id = models.CharField(max_length=255, verbose_name=_("Taxon ID"))
    provider = models.CharField(max_length=255, null=True, blank=True, verbose_name=_("Provider"))

    def __str__(self):
        provider = f" [{self.provider}]" if self.provider else ""
        return f"{self.taxon_id}{provider}"

    class Meta:
        verbose_name = _("Taxon ID")
        verbose_name_plural = _("Taxon IDs")


class TaxonomicClassification(models.Model):
    rank_name = models.CharField(max_length=255, verbose_name=_("Rank"))
    rank_value = models.CharField(max_length=255, verbose_name=_("Rank Value"))
    common_name = models.CharField(max_length=255, blank=True, null=True, verbose_name=_("Common Name"))
    taxon_ids = models.ManyToManyField(TaxonID, verbose_name=_("Taxon IDs"))
    parent = models.ForeignKey("self", on_delete=models.CASCADE, blank=True, null=True, verbose_name=_("Parent"))

    def __str__(self):
        return self.rank_name + ": " + self.rank_value

    class Meta:
        verbose_name = _("Taxonomic Classification")
        verbose_name_plural = _("Taxonomic Classifications")


class TaxonomicCoverage(models.Model):
    general = models.TextField(verbose_name=_("General Coverage"))
    taxonomic_classification = models.ManyToManyField(TaxonomicClassification, verbose_name=_("Taxonomic Classification"))

    class Meta:
        verbose_name = _("Taxonomic Coverage")
        verbose_name_plural = _("Taxonomic Coverages")


class ResponsibleParty(models.Model):
    name = models.CharField(max_length=255, null=True, blank=True, verbose_name=_("First Name"))
    last_name = models.CharField(max_length=255, null=True, blank=True, verbose_name=_("Last Name"))
    position = models.CharField(max_length=255, null=True, blank=True, verbose_name=_("Position"))
    organization = models.CharField(max_length=255, null=True, blank=True, verbose_name=_("Organization"))
    address = models.TextField(null=True, blank=True, verbose_name=_("Address"))
    city = models.CharField(max_length=255, null=True, blank=True, verbose_name=_("City"))
    country = models.CharField(max_length=255, null=True, blank=True, verbose_name=_("Country"))
    postal_code = models.CharField(max_length=255, null=True, blank=True, verbose_name=_("Postal Code"))
    phone = models.CharField(max_length=255, null=True, blank=True, verbose_name=_("Phone"))
    mail = models.EmailField(null=True, blank=True, verbose_name=_("Email"))
    web_page = models.URLField(null=True, blank=True, verbose_name=_("Web Page"))

    def __str__(self):
        return f"{self.name} {self.last_name} ({self.organization})"

    class Meta:
        verbose_name = _("Responsible Party")
        verbose_name_plural = _("Responsible Parties")


class Keyword(models.Model):
    keyword = models.CharField(max_length=255, verbose_name=_("Keyword"))
    type = models.CharField(max_length=255, null=True, blank=True, verbose_name=_("Type"))

    def __str__(self):
        key_type = f" [{self.type}]" if self.type is not None else ""
        return f"{self.keyword}{key_type}"


    class Meta:
        verbose_name = _("Keyword")
        verbose_name_plural = _("Keywords")


class KeywordSet(models.Model):
    keywords = models.ManyToManyField(Keyword, verbose_name=_("Keywords"))
    thesaurus = models.CharField(null=True, blank=True, verbose_name=_("Thesaurus"))

    class Meta:
        verbose_name = _("Keyword Set")
        verbose_name_plural = _("Keyword Sets")


class ProcedureStep(models.Model):
    step = models.IntegerField(verbose_name=_("Step"))
    sub_step = models.ManyToManyField("self", blank=True, verbose_name=_("Sub Step"))
    description = models.TextField(verbose_name=_("Description"))

    class Meta:
        verbose_name = _("Procedure Step")
        verbose_name_plural = _("Procedure Steps")


class Method(models.Model):
    steps = models.ManyToManyField(ProcedureStep, verbose_name=_("Steps"))

    class Meta:
        verbose_name = _("Method")
        verbose_name_plural = _("Methods")


class EMLDataset(models.Model):
    title = models.CharField(max_length=255, verbose_name=_("Title"))
    abstract = models.TextField(null=True, blank=True, verbose_name=_("Abstract"))
    language = models.CharField(choices=settings.LANGUAGES, verbose_name=_("Language"))
    creator = models.ManyToManyField(ResponsibleParty, related_name="creator", verbose_name=_("Creator"))
    contact = models.ManyToManyField(ResponsibleParty, related_name="contact", verbose_name=_("Contact"))
    metadata_provider = models.ManyToManyField(ResponsibleParty, blank=True, related_name="metadata_provider", verbose_name=_("Metadata Provider"))
    intellectual_rights = models.TextField(null=True, blank=True, verbose_name=_("Intellectual Rights"))
    licensed = models.ManyToManyField(Licence, blank=True, verbose_name=_("Licenced"))
    keyword_set = models.ManyToManyField(KeywordSet, blank=True, verbose_name=_("Keyword Set"))
    geographic_coverage = models.ForeignKey(GeographicCoverage, null=True, blank=True, on_delete=models.CASCADE, verbose_name=_("Geographic Coverage"))
    taxonomic_coverage = models.ForeignKey(TaxonomicCoverage, null=True, blank=True, on_delete=models.CASCADE, verbose_name=_("Taxonomic Coverage"))
    method = models.ForeignKey(Method, null=True, blank=True, on_delete=models.CASCADE, related_name="method", verbose_name=_("Method"))

    class Meta:
        verbose_name = _("EML Dataset")
        verbose_name_plural = _("EML Datasets")


class AssociatedParty(models.Model):
    dataset = models.ForeignKey(EMLDataset, on_delete=models.CASCADE, verbose_name=_("Dataset"))
    responsible_party = models.ForeignKey(ResponsibleParty, on_delete=models.CASCADE, verbose_name=_("Responsible Party"))
    role = models.SmallIntegerField(choices=[(role.value, role.to_camel_case()) for role in Role], verbose_name=_("Role"))

    class Meta:
        verbose_name = _("Associated Party")
        verbose_name_plural = _("Associated Parties")


class EML(models.Model):
    package_id = models.CharField(verbose_name=_("Package ID"))
    dataset = models.ForeignKey(EMLDataset, on_delete=models.CASCADE, verbose_name=_("EML Dataset"))

    class Meta:
        verbose_name = _("EML")
        verbose_name_plural = _("EML")
