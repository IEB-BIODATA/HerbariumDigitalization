# -*- coding: utf-8 -*-
# from django.db import models
import logging
import os
from typing import BinaryIO, Union, Any, Tuple

import celery
from django.contrib.auth.models import User
from django.contrib.gis.db import models
from django.core.files.base import ContentFile, File
from django.db import connection
from django.db.models.signals import post_delete, pre_save
from django.dispatch import receiver
from django.forms import CharField

from apps.catalog.models import Species
from .storage_backends import PublicMediaStorage, PrivateMediaStorage
from .validators import validate_file_size

VOUCHER_STATE = (
    (0, 'Sin Estado'),
    (1, 'Encontrado'),
    (2, 'No Encontrado'),
    (3, 'En Préstamo'),
    (4, 'Extraviado'),
    (5, 'En Préstado Encontrado'),
    (6, 'Extraviado Encontrado'),
    (7, 'Digitalizado'),
    (8, 'Pendiente'),
)


class Herbarium(models.Model):
    name = models.CharField(max_length=300, blank=False, null=False)
    collection_code = models.CharField(max_length=6, blank=False, null=False)
    institution_code = models.CharField(max_length=10, blank=True, null=True)

    class Meta:
        verbose_name_plural = "Herbariums"

    def __unicode__(self):
        return self.name

    def __str__(self):
        return "%s " % self.name

    def natural_key(self) -> Tuple[Any, CharField]:
        return self.id, self.name


class ColorProfileFile(models.Model):
    file = models.FileField(upload_to='uploads/color_profile/', validators=[validate_file_size], blank=False,
                            null=False)
    created_at = models.DateTimeField(blank=True, null=True, editable=False)
    created_by = models.ForeignKey(User, on_delete=models.PROTECT, blank=True, null=True)

    def __unicode__(self):
        return self.file.name

    def __str__(self):
        return "%s " % self.file.name


class GeneratedPage(models.Model):
    name = models.CharField(max_length=300)
    herbarium = models.ForeignKey(Herbarium, on_delete=models.CASCADE)
    terminated = models.BooleanField(default=False)
    color_profile = models.ForeignKey(ColorProfileFile, on_delete=models.SET_NULL, blank=True, null=True)
    created_at = models.DateTimeField(blank=True, null=True, editable=False)
    created_by = models.ForeignKey(User, on_delete=models.PROTECT)

    class Meta:
        verbose_name_plural = "Generated Pages"

    def Total(self):
        return BiodataCode.objects.filter(page__id=self.id).count()

    def StatelessCount(self):
        return BiodataCode.objects.filter(page__id=self.id, voucher_state=0).count()

    def FoundCount(self):
        return BiodataCode.objects.filter(page__id=self.id, voucher_state=1).count()

    def NotFoundCount(self):
        return BiodataCode.objects.filter(page__id=self.id, voucher_state=2).count()

    def Digitalized(self):
        return BiodataCode.objects.filter(page__id=self.id, voucher_state=7).count()

    def __unicode__(self):
        return self.name

    def __str__(self):
        return "%s " % self.name

    def natural_key(self) -> Tuple[Any, CharField]:
        return self.id, self.name


class BiodataCode(models.Model):
    herbarium = models.ForeignKey(Herbarium, on_delete=models.CASCADE)
    code = models.CharField(max_length=30, blank=False, null=False, unique=True)
    catalog_number = models.IntegerField(blank=True, null=True)
    created_at = models.DateTimeField(blank=True, null=True, editable=False)
    created_by = models.ForeignKey(User, on_delete=models.PROTECT)
    qr_generated = models.BooleanField(default=False)
    page = models.ForeignKey(GeneratedPage, on_delete=models.CASCADE, blank=True, null=True)
    voucher_state = models.IntegerField(choices=VOUCHER_STATE, default=0)

    class Meta:
        verbose_name_plural = "BIODATA Codes"

    def __unicode__(self):
        return self.code

    def __str__(self):
        return "%s " % self.code

    def natural_key(self) -> Tuple[Any, CharField]:
        return self.id, self.code


class HerbariumMember(models.Model):
    user = models.OneToOneField(User, unique=True, on_delete=models.CASCADE)
    herbarium = models.ManyToManyField(Herbarium, blank=False)


class PriorityVouchersFile(models.Model):
    herbarium = models.ForeignKey(Herbarium, on_delete=models.CASCADE, blank=True, null=True)
    file = models.FileField(upload_to='uploads/priority_vouchers/', validators=[validate_file_size], blank=False,
                            null=False)
    created_at = models.DateTimeField(blank=True, null=True, editable=False)
    created_by = models.ForeignKey(User, on_delete=models.PROTECT, blank=True, null=True)

    class Meta:
        verbose_name_plural = "Priority Vouchers Files"

    def __unicode__(self):
        return self.file.name

    def __str__(self):
        return "%s " % self.file.name

    def filename(self):
        return os.path.basename(self.file.name)


class VoucherImported(models.Model):
    vouchers_file = models.ForeignKey(PriorityVouchersFile, on_delete=models.CASCADE, blank=True, null=True)
    biodata_code = models.ForeignKey(BiodataCode, on_delete=models.CASCADE, blank=True, null=True)
    herbarium = models.ForeignKey(Herbarium, on_delete=models.CASCADE, blank=True, null=True)
    other_catalog_numbers = models.CharField(max_length=13, blank=True, null=True)
    catalog_number = models.IntegerField(blank=True, null=True)
    recorded_by = models.CharField(max_length=300, blank=True, null=True)
    record_number = models.CharField(max_length=13, blank=True, null=True)
    organism_remarks = models.CharField(max_length=300, blank=True, null=True)
    scientific_name = models.ForeignKey(Species, on_delete=models.CASCADE, blank=True, null=True)
    locality = models.CharField(max_length=300, blank=True, null=True)
    verbatim_elevation = models.IntegerField(blank=True, null=True)
    georeference_date = models.DateTimeField(blank=True, null=True)
    decimal_latitude = models.FloatField(blank=True, null=True)
    decimal_longitude = models.FloatField(blank=True, null=True)
    identified_by = models.CharField(max_length=100, blank=True, null=True)
    identified_date = models.CharField(max_length=100, blank=True, null=True)
    image = models.ImageField(storage=PrivateMediaStorage(), blank=True, null=True)
    image_resized_10 = models.ImageField(storage=PrivateMediaStorage(), blank=True, null=True)
    image_resized_60 = models.ImageField(storage=PrivateMediaStorage(), blank=True, null=True)
    image_public = models.ImageField(storage=PublicMediaStorage(), blank=True, null=True)
    image_public_resized_10 = models.ImageField(storage=PublicMediaStorage(), blank=True, null=True)
    image_public_resized_60 = models.ImageField(storage=PublicMediaStorage(), blank=True, null=True)
    image_raw = models.ImageField(storage=PrivateMediaStorage(), blank=True, null=True)
    point = models.PointField(null=True, blank=True, )
    decimal_latitude_public = models.FloatField(blank=True, null=True)
    decimal_longitude_public = models.FloatField(blank=True, null=True)
    point_public = models.PointField(null=True, blank=True, )
    priority = models.IntegerField(blank=True, null=True, default=3)

    class Meta:
        verbose_name_plural = "Vouchers"

    def generate_etiquette(self):
        if self.biodata_code.voucher_state == 7:
            logging.debug("Regenerating public image ({})".format(self.id))
            self.biodata_code.voucher_state = 8
            self.biodata_code.save()
            self.save()
            celery.current_app.send_task('etiquette_picture', (self.id, ))
            return
        else:
            logging.debug("Voucher not digitalized, skipping ({})".format(self.id))
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
            self.id, image_variable, image_name
        ))
        getattr(self, image_variable).save(image_name, image_content, save=True)
        return


class Licence(models.Model):
    name = models.CharField(max_length=300, null=True)
    link = models.CharField(max_length=300, blank=True, null=True)
    short_name = models.CharField(max_length=20, null=True)
    added_by = models.ForeignKey(User, on_delete=models.SET_NULL, default=1, editable=False, null=True)

    def __unicode__(self):
        return self.name

    def __str__(self):
        return "%s " % self.name


class GalleryImage(models.Model):
    scientific_name = models.ForeignKey(Species, on_delete=models.CASCADE)
    image = models.ImageField(upload_to="gallery", storage=PublicMediaStorage())
    specimen = models.ForeignKey(BiodataCode, on_delete=models.SET_NULL, blank=True, null=True)
    taken_by = models.CharField(max_length=300, blank=True, null=True)
    licence = models.ForeignKey(
        Licence,
        on_delete=models.SET_NULL,
        null=True,
        default=Licence.objects.filter(id=1).first().pk
    )
    upload_by = models.ForeignKey(User, on_delete=models.PROTECT, default=1, editable=False)
    upload_at = models.DateTimeField(auto_now_add=True, blank=True, null=True, editable=False)


class BannerImage(models.Model):
    specie = models.OneToOneField(Species, on_delete=models.CASCADE)
    banner = models.ImageField(upload_to="banners", storage=PublicMediaStorage())
    image = models.ForeignKey(VoucherImported, on_delete=models.CASCADE)
    updated = models.DateTimeField(auto_now=True)


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
           voucher.georeference_date,
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
         JOIN digitalization_biodatacode biodatacode ON voucher.biodata_code = biodatacode.id
         JOIN catalog_species species ON voucher.scientific_name = species.id;

    ALTER MATERIALIZED VIEW vouchers_view OWNER TO <POSTGRES_USER>;

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
    georeference_date = models.DateTimeField(blank=True, null=True)
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
