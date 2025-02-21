import eml
import eml.resources
from xml_common.utils import Language as EMLLanguage
from django.conf import settings
from django.contrib.gis.db.models import GeometryField
from django.utils.translation import gettext_lazy as _, get_language
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

    @property
    def eml_object(self):
        return eml.resources.coverage.GeographicCoverage(
            scope=eml.types.Scope.DOCUMENT,
            description=self.description,
            west_bounding=self.west_bounding,
            east_bounding=self.east_bounding,
            north_bounding=self.north_bounding,
            south_bounding=self.south_bounding,
        )

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

    @property
    def eml_object(self):
        common_name = list()
        if self.common_name:
            common_name.append(self.common_name)
        return eml.resources.coverage.TaxonomicCoverage.TaxonomicClassification(
            rank_name=self.rank_name,
            rank_value=self.rank_value,
            common_name=common_name,
            taxon_id=[(taxon_id.taxon_id, taxon_id.provider) for taxon_id in self.taxon_ids.all()],
            classification=[
                classification.eml_object for classification in self.taxonomicclassification_set.all()
            ]
        )

    class Meta:
        verbose_name = _("Taxonomic Classification")
        verbose_name_plural = _("Taxonomic Classifications")


class TaxonomicCoverage(models.Model):
    general = models.TextField(verbose_name=_("General Coverage"))
    taxonomic_classification = models.ManyToManyField(TaxonomicClassification, verbose_name=_("Taxonomic Classification"))

    @property
    def eml_object(self):
        return eml.resources.coverage.TaxonomicCoverage(
            general_coverage=self.general,
            classification=[
                classification.eml_object for classification in self.taxonomic_classification.all()
            ],
        )

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

    @property
    def eml_object(self):
        individual_name = None
        organization = None
        position_name = None
        address = list()
        phone = list()
        mail = list()
        url = list()
        if self.name is not None or self.last_name is not None:
            individual_name = eml.types.IndividualName(
                last_name=self.last_name,
                first_name=self.name
            )
        if self.organization is not None:
            organization = eml.types.OrganizationName(self.organization)
        if self.position is not None:
            position_name = eml.types.PositionName(self.position)
        if self.address is not None or self.city is not None or self.country is not None or self.postal_code is not None:
            address.append(eml.types.EMLAddress(
                delivery_point=self.address,
                city=self.city,
                postal_code=self.postal_code,
                country=self.country
            ))
        if self.phone is not None:
            phone.append(eml.types.EMLPhone(self.phone))
        if self.web_page is not None:
            url.append(self.web_page)
        return eml.types.ResponsibleParty(
            individual_name=individual_name,
            organization_name=organization,
            position_name=position_name,
            address=address, phone=phone,
            mail=mail, url=url
        )

    def __str__(self):
        return f"{self.name} {self.last_name} ({self.organization})"

    class Meta:
        verbose_name = _("Responsible Party")
        verbose_name_plural = _("Responsible Parties")


class Keyword(models.Model):
    keyword = models.CharField(max_length=255, verbose_name=_("Keyword"))
    type = models.IntegerField(
        choices=[(key_type.value, key_type.name) for key_type in eml.resources.KeywordType],
        default=eml.resources.KeywordType.NULL.value,
        verbose_name=_("Type")
    )

    def __str__(self):
        key_type = f" [{self.type}]" if self.type is not None else ""
        return f"{self.keyword}{key_type}"


    class Meta:
        verbose_name = _("Keyword")
        verbose_name_plural = _("Keywords")


class KeywordSet(models.Model):
    keywords = models.ManyToManyField(Keyword, verbose_name=_("Keywords"))
    thesaurus = models.CharField(null=True, blank=True, verbose_name=_("Thesaurus"))

    @property
    def eml_object(self):
        return eml.resources.EMLKeywordSet(
            keywords=[keyword.keyword for keyword in self.keywords.all()],
            thesaurus=self.thesaurus,
            keywords_type=[eml.resources.KeywordType(keyword.type) for keyword in self.keywords.all()]
        )

    class Meta:
        verbose_name = _("Keyword Set")
        verbose_name_plural = _("Keyword Sets")


class ProcedureStep(models.Model):
    step = models.IntegerField(verbose_name=_("Step"))
    sub_step = models.ManyToManyField("self", blank=True, verbose_name=_("Sub Step"))
    description = models.TextField(verbose_name=_("Description"))

    @property
    def eml_object(self):
        return eml.types.ProcedureStep(
            description=eml.types.EMLTextType(  # TODO: Correct way of parse this
                paragraphs=[paragraph.lstrip("<para>").rstrip("</para") for paragraph in self.description.split("</para><para>")],
            ),
            sub_step=[sub_step.eml_object for sub_step in self.sub_step.all()],
        )

    class Meta:
        verbose_name = _("Procedure Step")
        verbose_name_plural = _("Procedure Steps")


class Method(models.Model):
    steps = models.ManyToManyField(ProcedureStep, verbose_name=_("Steps"))

    @property
    def eml_object(self):
        steps = self.steps.all()
        method_steps = [None] * len(steps)
        for step in steps:
            method_steps[step.step - 1] = step.eml_object
        return eml.types.Methods(
            method_steps=method_steps
        )

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

    @property
    def eml_object(self):
        geographic_cov = None
        taxonomic_cov = None
        methods = None
        if self.geographic_coverage is not None:
            geographic_cov = self.geographic_coverage.eml_object
        if self.taxonomic_coverage is not None:
            taxonomic_cov = self.taxonomic_coverage.eml_object
        if self.method is not None:
            methods = self.method.eml_object
        return eml.resources.EMLDataset(
            titles=[self.title],
            abstract=eml.types.EMLTextType( # TODO: Correct way of parse this
                paragraphs=[paragraph.lstrip("<para>").rstrip("</para") for paragraph in self.abstract.split("</para><para>")],
            ),
            language=EMLLanguage.get_language(self.language),
            creators=[creator.eml_object for creator in self.creator.all()],
            contact=[contact.eml_object for contact in self.contact.all()],
            metadata_providers=[metadata_provider.eml_object for metadata_provider in self.metadata_provider.all()],
            associated_parties=[
                (as_party.responsible_party.eml_object, Role.get_enum(as_party.get_role_display())) for as_party in self.associatedparty_set.all()
            ],
            intellectual_rights=eml.types.EMLTextType( # TODO: Correct way of parse this
                paragraphs=[paragraph.lstrip("<para>").rstrip("</para") for paragraph in self.intellectual_rights.split("</para><para>")],
            ),
            licensed=[a_licence.eml_object for a_licence in self.licensed.all()],
            keyword_set=[keyword_set.eml_object for keyword_set in self.keyword_set.all()],
            coverage=eml.resources.EMLCoverage(
                geographic=geographic_cov,
                taxonomic=taxonomic_cov,
            ),
            methods=methods
        )

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

    @property
    def eml_object(self):
        eml_object = eml.EML(
            self.package_id,
            system=settings.HERBARIUM_FRONTEND,
            resource_type=eml.resources.EMLResource.DATASET,
            version=eml.EMLVersion.VERSION_2_2_0,
            language=EMLLanguage.get_language(get_language())
        )
        eml_object.__resource__ = self.dataset.eml_object
        return eml_object

    class Meta:
        verbose_name = _("EML")
        verbose_name_plural = _("EML")
