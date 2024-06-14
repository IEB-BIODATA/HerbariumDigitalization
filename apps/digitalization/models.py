# -*- coding: utf-8 -*-
from __future__ import annotations

import celery
import logging
import math
import numpy as np
import pandas as pd
import pytz
from django.conf import settings
from django.contrib.auth.models import User
from django.contrib.gis.db import models
from django.contrib.gis.db.models import GeometryField
from django.contrib.gis.geos import GEOSGeometry
from django.core.files.base import ContentFile, File
from django.db import connection
from django.db.models import Q
from django.db.models.signals import post_delete, pre_save
from django.dispatch import receiver
from django.forms import CharField
from django.utils.translation import gettext_lazy as _
from typing import BinaryIO, Union, Any, Tuple, Callable, Dict, List

from apps.catalog.models import Species, TAXONOMIC_RANK
from intranet.utils import CatalogQuerySet
from .storage_backends import PublicMediaStorage, PrivateMediaStorage
from .validators import validate_file_size

VOUCHER_STATE = (
    (0, _('No State')),
    (1, _('Found')),
    (2, _('Not Found')),
    (3, _('Borrowed')),
    (4, _('Lost')),
    (5, _('Found And Borrowed')),
    (6, _('In Curatorship')),
    (7, _('Digitalized')),
    (8, _('Pending')),
)

DESIGNATION_TYPES = (
    (0, _('Protected Area')),
    (1, _('Private Conservation')),
    (2, _('Other Designations')),
)

IUCN_CATEGORIES = (
    ('Ia', _('strict nature reserve')),
    ('Ib', _('wilderness area')),
    ('II', _('national park')),
    ('III', _('natural monument or feature')),
    ('IV', _('habitat or species management area')),
    ('V', _('protected landscape or seascape')),
    ('VI', _('protected area with sustainable use of natural resources')),
)

DCW_SQL = {
    "catalogNumber": "catalog_number",
    "recordNumber": "record_number",
    "recordedBy": "recorded_by",
    "organismRemarks": "organism_remarks",
    "otherCatalogNumbers": "other_catalog_numbers",
    "verbatimElevation": "verbatim_elevation",
    "decimalLatitude": "decimal_latitude",
    "decimalLongitude": "decimal_longitude",
    "georeferencedDate": "georeferenced_date",
    "identifiedBy": "identified_by",
    "dateIdentified": "date_identified",
    "scientificName": "scientific_name",
    "scientificNameSimilarity": "scientific_name_similarity",
    "synonymySimilarity": "synonymy_similarity",
    "similarity": "similarity",
}


class Herbarium(models.Model):
    name = models.CharField(verbose_name=_("Name"), max_length=300, blank=False, null=False)
    collection_code = models.CharField(verbose_name=_("Collection Code"), max_length=6, blank=False, null=False,
                                       help_text=_("No more than %d letters") % 6)
    institution_code = models.CharField(verbose_name=_("Institution Code"), max_length=10, blank=True, null=True,
                                        help_text=_("No more than %d letters") % 10)

    class Meta:
        verbose_name = _("Herbarium")
        verbose_name_plural = _("Herbariums")

    def __unicode__(self):
        return self.name

    def __str__(self):
        return "%s " % self.name

    def natural_key(self) -> Tuple[Any, CharField]:
        return self.pk, self.name


class ColorProfileFile(models.Model):
    file = models.FileField(
        verbose_name=_("File"),
        upload_to='uploads/color_profile/',
        validators=[validate_file_size],
        blank=False, null=False
    )
    created_at = models.DateTimeField(verbose_name=_("Created at"), blank=True, null=True, editable=False)
    created_by = models.ForeignKey(User, verbose_name=_("Created by"), on_delete=models.PROTECT, blank=True, null=True)

    def __unicode__(self):
        return self.file.name

    def __str__(self):
        return "%s " % self.file.name

    class Meta:
        verbose_name = _("Color Profile File")
        verbose_name_plural = _("Color Profile Files")


class GeneratedPage(models.Model):
    name = models.CharField(verbose_name=_("Name"), max_length=300)
    herbarium = models.ForeignKey(Herbarium, verbose_name=_("Herbarium"), on_delete=models.CASCADE)
    finished = models.BooleanField(verbose_name=_("Finished?"), default=False)
    color_profile = models.ForeignKey(ColorProfileFile, verbose_name=_("Color Profile File"), on_delete=models.SET_NULL, blank=True, null=True)
    created_at = models.DateTimeField(verbose_name=_("Created at"), auto_now_add=True, blank=True, null=True, editable=False)
    created_by = models.ForeignKey(User, verbose_name=_("Created by"), on_delete=models.PROTECT)

    class Meta:
        verbose_name = _("Generated Page")
        verbose_name_plural = _("Generated Pages")

    @property
    def total(self):
        return BiodataCode.objects.filter(page__id=self.pk).count()

    @property
    def stateless_count(self):
        return BiodataCode.objects.filter(page__id=self.pk, voucher_state=0).count()

    @property
    def found_count(self):
        return BiodataCode.objects.filter(page__id=self.pk, voucher_state=1).count()

    @property
    def not_found_count(self):
        return BiodataCode.objects.filter(page__id=self.pk, voucher_state=2).count()

    @property
    def digitalized(self):
        return BiodataCode.objects.filter(
            Q(page__id=self.pk) & (Q(voucher_state=7) | Q(voucher_state=8))
        ).count()

    @property
    def qr_count(self):
        return BiodataCode.objects.filter(
            Q(page__id=self.pk) & Q(qr_generated=True)
        ).count()

    def save(
        self, quantity_pages: int = None, force_insert=False, force_update=False, using=None, update_fields=None
    ):
        if quantity_pages is None:
            quantity_pages = math.ceil(self.qr_count / 35)
        try:
            self.name = "{} páginas - {} códigos - Fecha:{}".format(
                quantity_pages, self.qr_count,
                self.created_at.astimezone(
                    pytz.timezone(settings.TIME_ZONE)
                ).strftime('%d-%m-%Y %H:%M')
            )
        except AttributeError:
            logging.debug(f"Cannot define name for session ({self.pk})")
        return super().save(
            force_insert=force_insert,
            force_update=force_update,
            using=using,
            update_fields=update_fields
        )

    def __unicode__(self):
        return self.name

    def __str__(self):
        return "%s " % self.name

    def natural_key(self) -> Tuple[Any, CharField]:
        return self.pk, self.name


class BiodataCode(models.Model):
    herbarium = models.ForeignKey(Herbarium, verbose_name=_("Herbarium"), on_delete=models.CASCADE)
    code = models.CharField(verbose_name=_("Code"), max_length=30, blank=False, null=False, unique=True)
    catalog_number = models.IntegerField(verbose_name=_("Catalog Number"), blank=True, null=True)
    created_at = models.DateTimeField(verbose_name=_("Created at"), blank=True, null=True, editable=False)
    created_by = models.ForeignKey(User, verbose_name=_("Created by"), on_delete=models.PROTECT)
    qr_generated = models.BooleanField(verbose_name=_("Generated QR?"), default=False)
    page = models.ForeignKey(GeneratedPage, verbose_name=_("Page"), on_delete=models.CASCADE, blank=True, null=True)
    voucher_state = models.IntegerField(verbose_name=_("Voucher State"), choices=VOUCHER_STATE, default=0)

    class Meta:
        verbose_name = _("BIODATA Code")
        verbose_name_plural = _("BIODATA Codes")

    def __unicode__(self):
        return self.code

    def __str__(self):
        return "%s " % self.code

    def natural_key(self) -> Tuple[Any, CharField]:
        return self.pk, self.code


class HerbariumMember(models.Model):
    user = models.OneToOneField(User, verbose_name=_("User"), unique=True, on_delete=models.CASCADE)
    herbarium = models.ManyToManyField(Herbarium, verbose_name=_("Herbarium"), blank=False)

    class Meta:
        verbose_name = _('Herbarium')
        verbose_name_plural = _('Herbariums')


class PriorityVouchersFile(models.Model):
    herbarium = models.ForeignKey(Herbarium, verbose_name=_("Herbarium"), on_delete=models.CASCADE, blank=True, null=True)
    file = models.FileField(
        verbose_name=_("File"),
        upload_to='uploads/priority_vouchers/',
        validators=[validate_file_size],
        blank=False, null=False
    )
    created_at = models.DateTimeField(verbose_name=_("Created at"), blank=True, null=True, editable=False)
    created_by = models.ForeignKey(User,verbose_name=_("Created by"),  on_delete=models.PROTECT, blank=True, null=True)

    class Meta:
        verbose_name = _("Priority Vouchers File")
        verbose_name_plural = _("Priority Vouchers Files")

    def __unicode__(self):
        return self.file.name

    def __str__(self):
        return "%s " % self.file.name


class VoucherImportedQuerySet(CatalogQuerySet):

    def filter_query(self, **parameters: Dict[str, List[str]]) -> CatalogQuerySet:
        query = Q()
        for query_key, parameter in parameters.items():
            query &= Q(**{f"scientific_name__{query_key}__in": parameter})
        queryset = self.filter(query).distinct()
        logging.debug(f"Voucher Imported: {query} and got {queryset}")
        return queryset

    def filter_taxonomy(self, **parameters: Dict[str: List[str]]) -> CatalogQuerySet:
        query = Q()
        for taxonomic_rank, parameter in parameters.items():
            rank_index = TAXONOMIC_RANK.index(taxonomic_rank)
            query_name = "__".join(list(reversed(TAXONOMIC_RANK))[0:-rank_index]).replace(
                "species", "scientific_name"
            )
            query &= Q(**{f"{query_name}__in": parameter})
        queryset = self.filter(query).distinct()
        logging.debug(f"Voucher Imported: {query} and got {queryset}")
        return queryset

    def filter_geometry(self, geometries: List[str]) -> CatalogQuerySet:
        queryset = self
        for geometry in geometries:
            queryset = self.filter(point__within=geometry).distinct()
        logging.debug(f"Voucher Imported: geometry and got {queryset}")
        return queryset

    def search(self, text: str) -> CatalogQuerySet:
        return self.filter(scientific_name__scientific_name__icontains=text)


class VoucherImported(models.Model):
    vouchers_file = models.ForeignKey(PriorityVouchersFile, verbose_name=_("Priority Vouchers File"),
                                      on_delete=models.CASCADE, blank=True, null=True)
    biodata_code = models.ForeignKey(BiodataCode, verbose_name=_("BIODATA Code"), on_delete=models.CASCADE,
                                     blank=True, null=True)
    herbarium = models.ForeignKey(Herbarium, verbose_name=_("Herbarium"), on_delete=models.CASCADE,
                                  blank=True, null=True)
    other_catalog_numbers = models.CharField(verbose_name=_("Other Catalog Numbers"), max_length=13,
                                             blank=True, null=True)
    catalog_number = models.IntegerField(verbose_name=_("Catalog Number"), blank=True, null=True)
    recorded_by = models.CharField(verbose_name=_("Recorded by"), max_length=300, blank=True, null=True)
    record_number = models.CharField(verbose_name=_("Record Number"), max_length=13, blank=True, null=True)
    organism_remarks = models.CharField(verbose_name=_("Observations"), max_length=300, blank=True, null=True)
    scientific_name = models.ForeignKey(Species, verbose_name=_("Species"), on_delete=models.CASCADE, blank=True,
                                        null=True)
    locality = models.CharField(verbose_name=_("Locality"), max_length=300, blank=True, null=True)
    verbatim_elevation = models.IntegerField(verbose_name=_("Altitude"), blank=True, null=True)
    georeferenced_date = models.DateTimeField(verbose_name=_("Georeferenced Date"), blank=True, null=True)
    decimal_latitude = models.FloatField(verbose_name=_("Latitude"), blank=True, null=True)
    decimal_longitude = models.FloatField(verbose_name=_("Longitude"), blank=True, null=True)
    identified_by = models.CharField(verbose_name=_("Identified by"), max_length=100, blank=True, null=True)
    identified_date = models.CharField(verbose_name=_("Identified Date"), max_length=100, blank=True, null=True)
    identified_date = models.CharField(verbose_name=_("Identified Date"), max_length=100, blank=True, null=True)
    image = models.ImageField(verbose_name=_("Image"), storage=PrivateMediaStorage(), blank=True, null=True)
    image_resized_10 = models.ImageField(verbose_name=_("%d Times Smaller Image Scale") % 10,
                                         storage=PrivateMediaStorage(), blank=True, null=True)
    image_resized_60 = models.ImageField(verbose_name=_("%d Times Smaller Image Scale") % 60,
                                         storage=PrivateMediaStorage(), blank=True, null=True)
    image_public = models.ImageField(verbose_name=_("Public Image"), storage=PublicMediaStorage(), blank=True, null=True)
    image_public_resized_10 = models.ImageField(verbose_name=_("%d Times Smaller Public Image Scale") % 10,
                                                storage=PublicMediaStorage(), blank=True, null=True)
    image_public_resized_60 = models.ImageField(verbose_name=_("%d Times Smaller Public Image Scale") % 60,
                                                storage=PublicMediaStorage(), blank=True, null=True)
    image_raw = models.ImageField(verbose_name=_("Raw Image"), storage=PrivateMediaStorage(), blank=True, null=True)
    point = models.PointField(verbose_name=_("Point"), null=True, blank=True, )
    decimal_latitude_public = models.FloatField(verbose_name=_("Public Latitude"), blank=True, null=True)
    decimal_longitude_public = models.FloatField(verbose_name=_("Public Longitude"), blank=True, null=True)
    point_public = models.PointField(verbose_name=_("Public Point"), null=True, blank=True, )
    priority = models.IntegerField(verbose_name=_("Priority"), blank=True, null=True, default=3)

    objects = VoucherImportedQuerySet.as_manager()

    class Meta:
        verbose_name = _("Voucher")
        verbose_name_plural = _("Vouchers")

    def generate_etiquette(self):
        if self.biodata_code.voucher_state == 7:
            logging.debug("Regenerating public image ({})".format(self.pk))
            self.biodata_code.voucher_state = 8
            self.biodata_code.save()
            self.save()
            celery.current_app.send_task('etiquette_picture', (self.pk,))
            return
        else:
            logging.debug("Voucher not digitalized, skipping ({})".format(self.pk))
            return

    def image_voucher_thumb_url(self):
        if self.image_resized_10:
            return self.image_resized_10.url
        else:
            return '#'

    def image_voucher_url(self):
        if self.image_resized_60:
            return self.image_resized_60.url
        else:
            return '#'

    def image_voucher_jpg_raw_url(self):
        if self.image:
            return self.image.url
        else:
            return '#'

    def image_voucher_cr3_raw_url(self):
        if self.image_raw:
            return self.image_raw.url
        else:
            return '#'

    def image_voucher_jpg_raw_url_public(self):
        if self.image_public:
            return self.image_public.url
        else:
            return '#'

    def upload_raw_image(self, image: Union[File, BinaryIO]):
        self.__upload_image__(image, ".CR3", "image_raw")
        self.biodata_code.voucher_state = 8
        self.biodata_code.save()
        self.save()
        return

    def upload_image(self, image: Union[File, BinaryIO], public: bool = False):
        add_public = "_public" if public else ""
        self.__upload_image__(image, f"{add_public}.jpg", f"image{add_public}")
        self.save()
        return

    def upload_scaled_image(self, image: Union[File, BinaryIO], scale: int, public: bool = False):
        add_public = "_public" if public else ""
        self.__upload_image__(image, f"{add_public}_resized_{scale}.jpg", f"image{add_public}_resized_{scale}")
        self.save()
        return

    def __upload_image__(self, image: Union[File, BinaryIO], file_info: str, image_variable: str):
        image_content = ContentFile(image.read())
        image_name = "{}_{}_{:07}{}".format(
            self.herbarium.institution_code,
            self.herbarium.collection_code,
            self.catalog_number,
            file_info
        )
        logging.info("Voucher {}: Saving {} with name {}".format(
            self.pk, image_variable, image_name
        ))
        getattr(self, image_variable).save(image_name, image_content, save=True)
        return

    @staticmethod
    def public_point(point):
        integer = int(point)
        min_grade = point - integer
        minimum = min_grade * 60
        min_round = round(minimum) - 1
        public_point = integer + min_round / 60
        return public_point

    @staticmethod
    def from_pandas_row(
            row: pd.Series,
            priority_file: PriorityVouchersFile,
            species: Species = None,
            biodata_code: BiodataCode = None,
            logger: logging.Logger = None
    ) -> VoucherImported:
        if species is None:
            species = Species.objects.firter(scientific_name_db=row["scientific_name"].upper().strip()).first()
        if biodata_code is None:
            biodata_code = BiodataCode.objects.filter(
                code="{}:{}:{:07d}".format(
                    priority_file.herbarium.institution_code,
                    priority_file.herbarium.collection_code,
                    row['catalog_number']
                )).first()
        if logger is None:
            logger = logging.getLogger(__name__)

        def __validate_attribute__(_row_: pd.Series, _column_: str, _validator_: Callable[[Any], Any]) -> Any:
            if _column_ in _row_.keys():
                try:
                    return _validator_(_row_[_column_])
                except Exception as e:
                    logger.warning(f"Error ({e}) retrieving '{_column_}' from data", exc_info=True)
                    return None
            else:
                logger.warning(f"'{_column_}' not in data")
                return None

        georeferenced_date = pd.to_datetime(
            row['georeferenced_date'],
            format='%Y%m%d', utc=True
        )

        point = None
        point_public = None
        decimal_latitude_public = None
        decimal_longitude_public = None

        if row['decimal_latitude'] and row['decimal_longitude']:
            point = GEOSGeometry(
                f"POINT({row['decimal_longitude']} {row['decimal_latitude']})",
                srid=4326
            )
            if not np.isnan(row['decimal_latitude']) and not np.isnan(row['decimal_longitude']):
                decimal_latitude_public = VoucherImported.public_point(row['decimal_latitude'])
                decimal_longitude_public = VoucherImported.public_point(row['decimal_longitude'])
                point_public = GEOSGeometry(
                    f"POINT({decimal_longitude_public} {decimal_latitude_public})",
                    srid=4326
                )

        return VoucherImported(
            vouchers_file=priority_file,
            biodata_code=biodata_code,
            herbarium=priority_file.herbarium,
            other_catalog_numbers=row['other_catalog_numbers'],
            catalog_number=row['catalog_number'],
            recorded_by=row['recorded_by'],
            record_number=row['record_number'],
            organism_remarks=__validate_attribute__(row, "organism_remarks", lambda x: x),
            scientific_name=species,
            locality=row['locality'],
            verbatim_elevation=__validate_attribute__(row, "verbatim_elevation", lambda x: int(x)),
            georeferenced_date=None if pd.isnull(georeferenced_date) else georeferenced_date,
            decimal_latitude=__validate_attribute__(
                row, "decimal_latitude",
                lambda x: None if np.isnan(x) else float(x)
            ),
            decimal_longitude=__validate_attribute__(
                row, "decimal_longitude",
                lambda x: None if np.isnan(x) else float(x)
            ),
            identified_by=__validate_attribute__(row, "identified_by", lambda x: x),
            identified_date=__validate_attribute__(row, "identified_date", lambda x: x),
            point=point,
            decimal_latitude_public=decimal_latitude_public,
            decimal_longitude_public=decimal_longitude_public,
            point_public=point_public,
            priority=1 if "priority" not in row.keys() else row["priority"]
        )


class Licence(models.Model):
    name = models.CharField(verbose_name=_("Name"), max_length=300, null=True)
    link = models.CharField(verbose_name=_("Link"), max_length=300, blank=True, null=True)
    short_name = models.CharField(verbose_name=_("Short Name"), max_length=20, null=True)
    added_by = models.ForeignKey(User, verbose_name=_("Added by"), on_delete=models.SET_NULL, default=1, editable=False,
                                 null=True)

    def __unicode__(self):
        return self.name

    def __str__(self):
        return "%s " % self.name


class GalleryImage(models.Model):
    scientific_name = models.ForeignKey(Species, verbose_name=_("Species"), on_delete=models.CASCADE)
    image = models.ImageField(verbose_name=_("Image"), upload_to="gallery", storage=PublicMediaStorage())
    thumbnail = models.ImageField(verbose_name=_("Thumbnail"), upload_to="gallery", storage=PublicMediaStorage(), null=True)
    aspect_ratio = models.FloatField(verbose_name=_("Aspect Ratio"), null=True, blank=True)
    specimen = models.ForeignKey(BiodataCode, verbose_name=_("Specimen"), on_delete=models.SET_NULL, blank=True, null=True)
    taken_by = models.CharField(verbose_name=_("Taken by"), max_length=300, blank=True, null=True)
    licence = models.ForeignKey(
        Licence,
        verbose_name=_("Licence"),
        on_delete=models.SET_NULL,
        null=True,
        default=Licence.objects.filter(id=1).first().pk
    )
    upload_by = models.ForeignKey(User, verbose_name=_("Upload by"), on_delete=models.PROTECT, default=1, editable=False)
    upload_at = models.DateTimeField(verbose_name=_("Upload at"), auto_now_add=True, blank=True, null=True, editable=False)

    def generate_thumbnail(self) -> None:
        celery.current_app.send_task('generate_thumbnail', (self.pk,))
        return


class BannerImage(models.Model):
    species = models.OneToOneField(Species, verbose_name=_("Species"), on_delete=models.CASCADE)
    banner = models.ImageField(verbose_name=_("Banner"), upload_to="banners", storage=PublicMediaStorage())
    image = models.ForeignKey(VoucherImported, verbose_name=_("Image"), on_delete=models.CASCADE)
    updated_at = models.DateTimeField(verbose_name=_("Updated at"), auto_now=True)


class Area(models.Model):
    name = models.CharField(verbose_name=_("Name"), max_length=300, null=True)
    geometry = GeometryField(verbose_name=_("Geometry"), dim=2)
    created_at = models.DateTimeField(verbose_name=_("Created at"), auto_now=True, blank=True, null=True,
                                      editable=False)
    created_by = models.ForeignKey(User, verbose_name=_("Created by"), on_delete=models.PROTECT, blank=True, null=True)
    updated_at = models.DateTimeField(verbose_name=_("Updated at"), auto_now=True)

    class Meta:
        verbose_name = _("Area")
        verbose_name_plural = _("Areas")


class ProtectedArea(Area):
    mma_code = models.CharField(verbose_name=_("MMA Code"), max_length=100, null=True)
    designation_type = models.IntegerField(verbose_name=_("Designation Type"), choices=DESIGNATION_TYPES, default=0)
    category = models.CharField(verbose_name=_("Category"), max_length=100, null=True)
    iucn_management_category = models.CharField(verbose_name=_("IUCN Management Category"), max_length=5,
                                                choices=IUCN_CATEGORIES, null=True)

    class Meta:
        verbose_name = _("Protected Area")
        verbose_name_plural = _("Protected Areas")


class TemporalArea(Area):
    access = models.IntegerField(verbose_name=_("Access"), default=0)

    class Meta:
        verbose_name = _("Temporal Area")
        verbose_name_plural = _("Temporal Areas")


class PostprocessingLog(models.Model):
    date = models.DateTimeField(verbose_name=_("Date"))
    file = models.FileField(
        verbose_name=_("File"),
        upload_to='logs/',
        storage=PrivateMediaStorage(),
        blank=False, null=False
    )
    found_images = models.IntegerField(verbose_name=_("Found Images"), default=0, blank=False, null=False)
    processed_images = models.IntegerField(verbose_name=_("Processed Images"), default=0, blank=False, null=False)
    failed_images = models.IntegerField(verbose_name=_("Failed Images"), default=0, blank=False, null=False)
    created_by = models.ForeignKey(
        User, verbose_name=_("Created by"), on_delete=models.PROTECT, blank=False, null=False
    )
    scheduled = models.BooleanField(verbose_name=_("Scheduled"), blank=False, null=False)

    class Meta:
        verbose_name = _("Postprocessing Log")
        verbose_name_plural = _("Postprocessing Logs")


@receiver(post_delete, sender=PriorityVouchersFile)
def auto_delete_file_on_delete_PriorityVouchersFile(sender, instance, **kwargs):
    if instance.file:
        instance.file.delete(save=False)


@receiver(post_delete, sender=ColorProfileFile)
def auto_delete_file_on_delete_ColorProfileFile(sender, instance, **kwargs):
    if instance.file:
        instance.file.delete(save=False)


@receiver(pre_save, sender=VoucherImported)
def pre_save_image(sender, instance, *args, **kwargs):
    """ instance old image file will delete from os """
    try:
        old_image = instance.__class__.objects.get().image.path
        old_image_resized_10 = instance.__class__.objects.get().image_resized_10.path
        old_image_resized_60 = instance.__class__.objects.get().image_resized_60.path
        old_image_public = instance.__class__.objects.get().image_public.path
        old_image_public_resized_10 = instance.__class__.objects.get().image_public_resized_10.path
        old_image_public_resized_60 = instance.__class__.objects.get().image_public_resized_60.path
        old_image_raw = instance.__class__.objects.get().image_raw.path
        try:
            new_image = instance.image.path
            new_image_resized_10 = instance.image_resized_10.path
            new_image_resized_60 = instance.image_resized_60.path
            new_image_public = instance.image_public.path
            new_image_public_resized_10 = instance.image_public_resized_10.path
            new_image_public_resized_60 = instance.image_public_resized_60.path
            new_image_raw = instance.image_raw.path
        except:
            new_image = None
        if new_image != old_image:
            import os
            if os.path.exists(old_image):
                os.remove(old_image)
        if new_image_resized_10 != old_image_resized_10:
            import os
            if os.path.exists(old_image_resized_10):
                os.remove(old_image_resized_10)
        if new_image_resized_60 != old_image_resized_60:
            import os
            if os.path.exists(old_image_resized_60):
                os.remove(old_image_resized_60)
        if new_image_public != old_image_public:
            import os
            if os.path.exists(old_image_public):
                os.remove(old_image_public)
        if new_image_public_resized_10 != old_image_public_resized_10:
            import os
            if os.path.exists(old_image_public_resized_10):
                os.remove(old_image_public_resized_10)
        if new_image_public_resized_60 != old_image_public_resized_60:
            import os
            if os.path.exists(old_image_public_resized_60):
                os.remove(old_image_public_resized_60)
        if new_image_raw != old_image_raw:
            import os
            if os.path.exists(old_image_raw):
                os.remove(old_image_raw)
    except:
        pass


class VouchersView(models.Model):
    """
    CREATE MATERIALIZED VIEW vouchers_view AS
    SELECT voucher.id,
           voucherfile.file,
           biodatacode.code,
           biodatacode.voucher_state,
           herbarium.collection_code,
           voucher.other_catalog_numbers,
           voucher.catalog_number,
           voucher.recorded_by,
           voucher.record_number,
           voucher.organism_remarks,
           species.scientific_name,
           voucher.locality,
           voucher.verbatim_elevation,
           voucher.georeferenced_date,
           voucher.decimal_latitude,
           voucher.decimal_longitude,
           voucher.identified_by,
           voucher.identified_date,
           voucher.decimal_latitude_public,
           voucher.decimal_longitude_public,
           voucher.priority
    FROM digitalization_voucherimported voucher
         JOIN digitalization_herbarium herbarium ON voucher.herbarium_id = herbarium.id
         JOIN digitalization_priorityvouchersfile voucherfile ON voucher.vouchers_file_id = voucherfile.id
         JOIN digitalization_biodatacode biodatacode ON voucher.biodata_code_id = biodatacode.id
         JOIN catalog_species species ON voucher.scientific_name_id = species.id;

    CREATE UNIQUE INDEX vouchers_view_id_idx
        ON vouchers_view (id);
    """
    id = models.IntegerField(primary_key=True, blank=False, null=False, help_text="")
    file = models.CharField(max_length=300, blank=True, null=True)
    code = models.CharField(max_length=300, blank=True, null=True)
    voucher_state = models.CharField(max_length=300, blank=True, null=True)
    collection_code = models.CharField(max_length=300, blank=True, null=True)
    other_catalog_numbers = models.CharField(max_length=13, blank=True, null=True)
    catalog_number = models.IntegerField(blank=True, null=True)
    recorded_by = models.CharField(max_length=300, blank=True, null=True)
    record_number = models.CharField(max_length=13, blank=True, null=True)
    organism_remarks = models.CharField(max_length=300, blank=True, null=True)
    scientific_name = models.CharField(max_length=300, blank=True, null=True)
    locality = models.CharField(max_length=300, blank=True, null=True)
    verbatim_elevation = models.IntegerField(blank=True, null=True)
    georeferenced_date = models.DateTimeField(blank=True, null=True)
    decimal_latitude = models.FloatField(blank=True, null=True)
    decimal_longitude = models.FloatField(blank=True, null=True)
    identified_by = models.CharField(max_length=100, blank=True, null=True)
    identified_date = models.CharField(max_length=100, blank=True, null=True)
    decimal_latitude_public = models.FloatField(blank=True, null=True)
    decimal_longitude_public = models.FloatField(blank=True, null=True)
    priority = models.IntegerField(blank=True, null=True, default=3)

    @classmethod
    def refresh_view(cl):
        with connection.cursor() as cursor:
            cursor.execute("REFRESH MATERIALIZED VIEW CONCURRENTLY vouchers_view")

    class Meta:
        managed = False
        db_table = 'vouchers_view'
