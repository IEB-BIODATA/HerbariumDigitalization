import textwrap
import urllib
from io import BytesIO

from PIL import Image,ImageDraw, ImageFont
from django.core.files.uploadedfile import InMemoryUploadedFile

from apps.digitalization.models import VoucherImported


def generate_etiquete(voucher_id):
    voucher = VoucherImported.objects.get(id=voucher_id)
    file = urllib.request.urlretrieve(voucher.image.url, voucher.occurrenceID.code.replace(':', '_') + '.jpg')
    voucher_image = Image.open(voucher.occurrenceID.code.replace(':', '_') + '.jpg')
    voucher_image_editable = ImageDraw.Draw(voucher_image)
    herbarium_code = voucher.herbarium.collection_code
    herbarium_name = voucher.herbarium.name
    scientificNameFull = voucher.scientificName.scientificNameFull
    family = voucher.scientificName.genus.family.name.title()
    catalogNumber = voucher.catalogNumber
    recordNumber = voucher.recordNumber
    recordedBy = voucher.recordedBy
    locality = voucher.locality
    identifiedBy = voucher.identifiedBy
    dateIdentified = voucher.dateIdentified
    georeferencedDate = voucher.georeferencedDate.strftime('%d-%m-%Y')
    organismRemarks = voucher.organismRemarks
    if herbarium_code == 'CONC':
        delta_x = 0
        delta_y = 230
        shape = [(2046 + delta_x, 4384 + delta_y), (3915 + delta_x, 5528 + delta_y)]
        voucher_image_editable.rectangle(shape, fill='#d7d6e0', outline="black", width=4)
        title_font = ImageFont.truetype('static/font/arial.ttf', 70)
        voucher_image_editable.text((((4000 - 2150) / 2) + 2150 + delta_x, 4530 + delta_y), herbarium_name, (0, 0, 0),
                                    anchor="ms", font=title_font, stroke_width=2, stroke_fill="black")
        number_font = ImageFont.truetype('static/font/arial.ttf', 55)
        voucher_image_editable.text((2250 + delta_x, 4660 + delta_y), herbarium_code + ' ' + str(catalogNumber),
                                    (0, 0, 0), font=number_font, stroke_width=2, stroke_fill="black")
        scientificName_font = ImageFont.truetype('static/font/arial_italic.ttf', 48)
        voucher_image_editable.text((((4000 - 2150) / 2) + 2150 + delta_x, 4810 + delta_y), scientificNameFull + ' ',
                                    (0, 0, 0), anchor="ms", font=scientificName_font)
        normal_font = ImageFont.truetype('static/font/arial.ttf', 48)
        voucher_image_editable.text((((4000 - 2150) / 2) + 2150 + delta_x, 4870 + delta_y), family, (0, 0, 0),
                                    anchor="ms", font=normal_font)

        if locality:
            voucher_image_editable.text((2250 + delta_x, 4980 + delta_y), locality, (0, 0, 0), font=normal_font)

        voucher_image_editable.text((2250 + delta_x, 5130 + delta_y), 'Fecha Col. ' + georeferencedDate, (0, 0, 0),
                                    font=normal_font)
        voucher_image_editable.text((2900 + delta_x, 5130 + delta_y), 'Leg. ' + recordedBy + ' ' + recordNumber,
                                    (0, 0, 0), font=normal_font)

        if dateIdentified:
            voucher_image_editable.text((2250 + delta_x, 5200 + delta_y), 'Fecha Det. ' + str(dateIdentified),
                                        (0, 0, 0), font=normal_font)

        if identifiedBy:
            voucher_image_editable.text((2900 + delta_x, 5200 + delta_y), 'Det. ' + str(identifiedBy), (0, 0, 0),
                                        font=normal_font)

        if organismRemarks and organismRemarks != 'nan':
            observation = textwrap.fill(str(organismRemarks), width=60, break_long_words=False)
            voucher_image_editable.text((2250 + delta_x, 5350 + delta_y), 'Obs.: ' + observation, (0, 0, 0),
                                        font=normal_font)
    else:
        shape = [(2150, 4650), (4000, 5690)]
        voucher_image_editable.rectangle(shape, fill='#d7d6e0', outline="black", width=4)
        title_font = ImageFont.truetype('static/font/arial.ttf', 70)
        voucher_image_editable.text((((4000 - 2150) / 2) + 2150, 4800), herbarium_name, (0, 0, 0), anchor="ms",
                                    font=title_font, stroke_width=2, stroke_fill="black")
        number_font = ImageFont.truetype('static/font/arial.ttf', 55)
        voucher_image_editable.text((2250, 4900), herbarium_code + ' ' + str(catalogNumber), (0, 0, 0),
                                    font=number_font, stroke_width=2, stroke_fill="black")
        scientificName_font = ImageFont.truetype('static/font/arial_italic.ttf', 48)
        voucher_image_editable.text((((4000 - 2150) / 2) + 2150, 5000), scientificNameFull, (0, 0, 0), anchor="ms",
                                    font=scientificName_font)
        normal_font = ImageFont.truetype('static/font/arial.ttf', 48)
        voucher_image_editable.text((((4000 - 2150) / 2) + 2150, 5070), family, (0, 0, 0), anchor="ms",
                                    font=normal_font)

        if locality:
            voucher_image_editable.text((2250, 5170), locality, (0, 0, 0), font=normal_font)

        voucher_image_editable.text((2250, 5270), 'Fecha Col. ' + georeferencedDate, (0, 0, 0), font=normal_font)
        voucher_image_editable.text((2900, 5270), 'Leg. ' + recordedBy + ' ' + recordNumber, (0, 0, 0),
                                    font=normal_font)

        if dateIdentified:
            voucher_image_editable.text((2250, 5340), 'Fecha Det. ' + str(dateIdentified), (0, 0, 0), font=normal_font)

        if identifiedBy:
            voucher_image_editable.text((2900, 5340), 'Det. ' + str(identifiedBy), (0, 0, 0), font=normal_font)

        if organismRemarks and organismRemarks != 'nan':
            observation = textwrap.fill(str(organismRemarks), width=60, break_long_words=False)
            voucher_image_editable.text((2250, 5440), 'Obs.: ' + observation, (0, 0, 0), font=normal_font)

    voucher_image.save(voucher_image.filename.replace(".jpg", "_public.jpg"))
    buffer = BytesIO()
    voucher_image.save(buffer, "JPEG")
    image_file = InMemoryUploadedFile(buffer, None, voucher_image.filename, 'image/jpeg', buffer.tell, None)
    voucher.image_public.save(voucher_image.filename, image_file)
    voucher.save()
    return voucher_image.filename.replace(".jpg", "_public.jpg")
