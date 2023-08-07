import logging
import textwrap
from io import BytesIO

from PIL import Image, ImageDraw, ImageFont
from celery import shared_task
from django.contrib.staticfiles import finders

from apps.digitalization.models import VoucherImported
from apps.digitalization.storage_backends import PrivateMediaStorage

PARAMETERS = {
    "CONC": {
        "RECTANGLE": ((2046, 4614), (3915, 5758)),
        "TITLE_POS": (3075, 4760),
        "NUMBER_POS": (2250, 4890),
        "NAME_POS": (3075, 5040),
        "FAMILY_POS": (3075, 5100),
        "LOCALITY_POS": (2250, 5210),
        "GEO_DATE_POS": (2250, 5360),
        "RECORD_POS": (2900, 5360),
        "RECORD_DATE_POS": (2250, 5430),
        "IDENTIFY_POS": (2900, 5430),
        "OBS_POS": (2250, 5580),
    },
    "ULS": {
        "RECTANGLE": ((2150, 4650), (4000, 5690)),
        "TITLE_POS": (3075, 4800),
        "NUMBER_POS": (2250, 4900),
        "NAME_POS": (3075, 5000),
        "FAMILY_POS": (3075, 5070),
        "LOCALITY_POS": (2250, 5170),
        "GEO_DATE_POS": (2250, 5270),
        "RECORD_POS": (2900, 5270),
        "RECORD_DATE_POS": (2250, 5340),
        "IDENTIFY_POS": (2900, 5340),
        "OBS_POS": (2250, 5440),
    }
}


@shared_task(name='etiquette_picture')
def etiquette_picture(voucher_id):
    try:
        voucher = VoucherImported.objects.get(pk=voucher_id)
        logging.info("Working with {}".format(voucher.id))
        parameters = PARAMETERS[voucher.herbarium.collection_code]
        logging.debug(parameters)
        image_file = PrivateMediaStorage().open(voucher.image.name, "rb")
        voucher_image = Image.open(image_file)
        voucher_image_editable = ImageDraw.Draw(voucher_image)
        voucher_image_editable.rectangle(parameters["RECTANGLE"], fill='#d7d6e0', outline="black", width=4)
        title_font = ImageFont.truetype(finders.find('font/arial.ttf'), 70)
        voucher_image_editable.text(
            parameters["TITLE_POS"], voucher.herbarium.name.upper(),
            (0, 0, 0), anchor="ms", font=title_font, stroke_width=2, stroke_fill="black"
        )
        number_font = ImageFont.truetype(finders.find('font/arial.ttf'), 55)
        voucher_image_editable.text(
            parameters["NUMBER_POS"], voucher.herbarium.collection_code + ' ' + str(voucher.catalogNumber),
            (0, 0, 0), font=number_font, stroke_width=2, stroke_fill="black"
        )
        scientific_name_font = ImageFont.truetype(finders.find('font/arial_italic.ttf'), 48)
        voucher_image_editable.text(
            parameters["NAME_POS"], voucher.scientificName.scientificNameFull + ' ',
            (0, 0, 0), anchor="ms", font=scientific_name_font
        )
        normal_font = ImageFont.truetype(finders.find('font/arial_italic.ttf'), 48)
        voucher_image_editable.text(
            parameters["FAMILY_POS"], voucher.scientificName.genus.family.name,
            (0, 0, 0), anchor="ms", font=normal_font
        )
        if voucher.locality is not None and voucher.locality != "":
            voucher_image_editable.text(
                parameters["LOCALITY_POS"], voucher.locality,
                (0, 0, 0), font=normal_font
            )
        if voucher.georeferencedDate:
            georeferenced_date = voucher.georeferencedDate.strftime('%d-%m-%Y')
        else:
            georeferenced_date = ""
        voucher_image_editable.text(
            parameters["GEO_DATE_POS"], 'Fecha Col. ' + georeferenced_date,
            (0, 0, 0), font=normal_font
        )
        voucher_image_editable.text(
            parameters["RECORD_POS"], 'Leg. ' + voucher.recordedBy + ' ' + voucher.recordNumber,
            (0, 0, 0), font=normal_font
        )
        if voucher.dateIdentified is not None and voucher.dateIdentified != "":
            voucher_image_editable.text(
                parameters["RECORD_DATE_POS"], 'Fecha Det. ' + str(voucher.dateIdentified),
                (0, 0, 0), font=normal_font
            )
        if voucher.identifiedBy is not None and voucher.identifiedBy != "":
            voucher_image_editable.text(
                parameters["IDENTIFY_POS"], 'Det. ' + str(voucher.identifiedBy),
                (0, 0, 0), font=normal_font
            )
        if voucher.organismRemarks is not None and voucher.organismRemarks not in ["", "nan"]:
            observation = textwrap.fill(str(voucher.organismRemarks), width=60, break_long_words=False)
            voucher_image_editable.text(
                parameters["OBS_POS"], 'Obs.: ' + observation,
                (0, 0, 0), font=normal_font
            )
        edited_image_content = BytesIO()
        voucher_image.save(edited_image_content, format='JPEG')
        edited_image_content.seek(0)
        public_filename = "{}_{}_{:07}_public.jpg".format(
            voucher.herbarium.institution_code,
            voucher.herbarium.collection_code,
            voucher.catalogNumber
        )
        logging.info("Saving image with etiquette: {}".format(public_filename))
        voucher.image_public.save(public_filename, edited_image_content, save=True)
        # Resize the image to a different size and save
        for scale_percent in [10, 60]:
            width = int(voucher_image.size[0] * scale_percent / 100)
            height = int(voucher_image.size[1] * scale_percent / 100)
            resized_image = voucher_image.resize((width, height))
            resized_image_content = BytesIO()
            resized_image.save(resized_image_content, format='JPEG')
            resized_image_content.seek(0)
            getattr(voucher, "image_public_resized_{}".format(scale_percent)).save(
                public_filename.replace(".jpg", "_resized_{}.jpg".format(scale_percent)),
                resized_image_content, save=True
            )
        voucher.occurrenceID.voucher_state = 7
        voucher.occurrenceID.save()
        voucher.save()
        logging.info("Image saved!")
        return True
    except Exception as e:
        logging.error("Error on saving")
        logging.error(e, exc_info=True)
        return False
