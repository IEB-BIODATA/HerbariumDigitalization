import cv2
import datetime as dt
import glob
import json
import logging
import math
import numpy as np
import os
import pytesseract
import shutil
import textwrap
from django.contrib.auth.models import User
from django.core.files.base import ContentFile
from io import BytesIO
from typing import List, Tuple, Type, Dict

import boto3
import pandas as pd
import pytz
from PIL import Image, ImageDraw, ImageFont
from apps.catalog.models import Species, Synonymy
from celery import shared_task
from celery.app.task import Task
from celery.exceptions import Ignore
from django.conf import settings
from django.contrib.postgres.search import TrigramSimilarity
from django.db import transaction
from django.db.models import Model

from apps.digitalization.models import DCW_SQL, PostprocessingLog
from apps.digitalization.models import GalleryImage, BannerImage
from apps.digitalization.models import VoucherImported, BiodataCode, ColorProfileFile, PriorityVouchersFile
from apps.digitalization.storage_backends import PrivateMediaStorage, PublicMediaStorage
from apps.digitalization.utils import SessionFolder, TaskProcessLogger, HtmlLogger, GroupLogger
from apps.digitalization.utils import cr3_to_dng, dng_to_jpeg, dng_to_jpeg_color_profile
from apps.digitalization.utils import read_qr, change_image_resolution, empty_folder

N_BATCH = 1
WIDTH_CROP = 550
HEIGHT_CROP = 550
MARGIN = 100

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
        "CORNER": {
            "LEFT": (100, 200),
            "RIGHT": (3450, 200),
        },
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
        "CORNER": {
            "LEFT": (100, 100),
            "RIGHT": (3450, 100),
        },
    }
}


@shared_task(name='etiquette_picture')
def etiquette_picture(voucher_id, logger: logging.Logger = None):
    if logger is None:
        logger = logging.getLogger(__name__)
    try:
        voucher = VoucherImported.objects.get(pk=voucher_id)
        logger.info("Working with {}".format(voucher.id))
        parameters = PARAMETERS[voucher.herbarium.collection_code]
        logger.debug(parameters)
        image_file = PrivateMediaStorage().open(voucher.image.name, "rb")
        voucher_image = Image.open(image_file)
        voucher_image_editable = ImageDraw.Draw(voucher_image)
        voucher_image_editable.rectangle(parameters["RECTANGLE"], fill='#d7d6e0', outline="black", width=4)
        title_font = ImageFont.truetype('assets/font/arial.ttf', 70)
        voucher_image_editable.text(
            parameters["TITLE_POS"], voucher.herbarium.name.upper(),
            (0, 0, 0), anchor="ms", font=title_font, stroke_width=2, stroke_fill="black"
        )
        number_font = ImageFont.truetype('assets/font/arial.ttf', 55)
        voucher_image_editable.text(
            parameters["NUMBER_POS"], voucher.herbarium.collection_code + ' ' + str(voucher.catalog_number),
            (0, 0, 0), font=number_font, stroke_width=2, stroke_fill="black"
        )
        scientific_name_font = ImageFont.truetype('assets/font/arial_italic.ttf', 48)
        voucher_image_editable.text(
            parameters["NAME_POS"], voucher.scientific_name.scientific_name_full + ' ',
            (0, 0, 0), anchor="ms", font=scientific_name_font
        )
        normal_font = ImageFont.truetype('assets/font/arial_italic.ttf', 48)
        voucher_image_editable.text(
            parameters["FAMILY_POS"], voucher.scientific_name.genus.family.name,
            (0, 0, 0), anchor="ms", font=normal_font
        )
        if voucher.locality is not None and voucher.locality != "":
            voucher_image_editable.text(
                parameters["LOCALITY_POS"], voucher.locality,
                (0, 0, 0), font=normal_font
            )
        if voucher.georeferenced_date:
            georeferenced_date = voucher.georeferenced_date.strftime('%d-%m-%Y')
        else:
            georeferenced_date = ""
        voucher_image_editable.text(
            parameters["GEO_DATE_POS"], 'Fecha Col. ' + georeferenced_date,
            (0, 0, 0), font=normal_font
        )
        voucher_image_editable.text(
            parameters["RECORD_POS"], 'Leg. ' + voucher.recorded_by + ' ' + voucher.record_number,
            (0, 0, 0), font=normal_font
        )
        if voucher.identified_date is not None and voucher.identified_date != "":
            voucher_image_editable.text(
                parameters["RECORD_DATE_POS"], 'Fecha Det. ' + str(voucher.identified_date),
                (0, 0, 0), font=normal_font
            )
        if voucher.identified_by is not None and voucher.identified_by != "":
            voucher_image_editable.text(
                parameters["IDENTIFY_POS"], 'Det. ' + str(voucher.identified_by),
                (0, 0, 0), font=normal_font
            )
        if voucher.organism_remarks is not None and voucher.organism_remarks not in ["", "nan"]:
            observation = textwrap.fill(str(voucher.organism_remarks), width=60, break_long_words=False)
            voucher_image_editable.text(
                parameters["OBS_POS"], 'Obs.: ' + observation,
                (0, 0, 0), font=normal_font
            )
        edited_image_content = BytesIO()
        voucher_image.save(edited_image_content, format='JPEG')
        edited_image_content.seek(0)
        voucher.upload_image(edited_image_content, public=True)
        # Resize the image to a different size and save
        for scale_percent in [10, 60]:
            resized_image = change_image_resolution(voucher_image, scale_percent)
            voucher.upload_scaled_image(resized_image, scale_percent, public=True)
        voucher.biodata_code.voucher_state = 7
        voucher.biodata_code.save()
        voucher.save()
        logger.info("Image saved!")
        return True
    except Exception as e:
        logger.error("Error on saving")
        logger.error(e, exc_info=True)
        return False


@shared_task(name='scheduled_postprocessing')
def scheduled_postprocess(input_folder: str, temp_folder: str, log_folder: str):
    bucket_name = settings.AWS_STORAGE_BUCKET_NAME

    def batch_files_function(files: List, x: int) -> List[List]:
        return [files[i:i + x] for i in range(0, len(files), x)]

    s3 = boto3.client('s3')
    os.makedirs(temp_folder, exist_ok=True)
    os.makedirs(log_folder, exist_ok=True)
    log_object = PostprocessingLog(
        date=dt.datetime.now(),
        created_by=User.objects.get(pk=1),
        scheduled=True,
    )
    process_logger = TaskProcessLogger("Scheduled PostProcessing", log_folder)
    sessions = get_pending_sessions(s3, input_folder, process_logger)
    process_logger.debug(sessions)
    logging.info("Enter in sessions")
    os.makedirs(input_folder, exist_ok=True)
    for session_folder in sessions:
        try:
            process_logger.debug(session_folder)
            batch_files = batch_files_function(list(session_folder.__files__), N_BATCH)
            logging.info("Processing batches...")
            for batch in batch_files:
                log_cache = set()
                session_folder.create_folder()
                for file in batch:
                    file.download(s3, bucket_name, process_logger)
                logging.info("Converting file")
                cr3_to_dng(input_folder, temp_folder, process_logger)
                dng_to_jpeg(temp_folder, temp_folder, session_folder.get_institution(), process_logger, log_cache)
                for filename in glob.glob(temp_folder + '/*.jpg', recursive=False):
                    log_object.found_images += 1
                    logging.info("Reading QR...")
                    qr = read_qr(filename,
                                 WIDTH_CROP, HEIGHT_CROP,
                                 MARGIN, PARAMETERS[session_folder.get_institution()]["CORNER"],
                                 process_logger)
                    if qr is not None:
                        json_qr = json.loads(qr)
                        code_voucher = json_qr['code']
                        logging.info("Retrieving info...")
                        biodata_codes = BiodataCode.objects.filter(code=code_voucher)
                        if biodata_codes.count() == 0:
                            process_logger.error("Error retrieving data on qr for file {} and code {}".format(
                                filename, code_voucher
                            ))
                        else:
                            biodata_code: BiodataCode = biodata_codes[0]
                            dng_to_jpeg_color_profile(
                                temp_folder, temp_folder,
                                session_folder.get_institution(),
                                biodata_code.page.color_profile.file.url,
                                process_logger, log_cache
                            )
                            vouchers = VoucherImported.objects.filter(biodata_code__id=biodata_code.id)
                            if vouchers.count() == 1:
                                voucher: VoucherImported = vouchers[0]
                                raw_image_path = filename.replace(temp_folder, input_folder).replace(".jpg", ".CR3")
                                with open(raw_image_path, "rb") as file:
                                    voucher.upload_raw_image(file)
                                    voucher.save()
                                with open(filename, "rb") as file:
                                    voucher.upload_image(file)
                                    image = Image.open(file)
                                    for scale_percent in [10, 60]:
                                        resized_image = change_image_resolution(image, scale_percent)
                                        voucher.upload_scaled_image(resized_image, scale_percent)
                                voucher.save()
                                etiquette_picture(voucher.id, logger=process_logger)
                            else:
                                process_logger.error(
                                    "No voucher, or more than one, associated with ocurrence {}".format(
                                        biodata_code.id
                                    )
                                )
                        log_object.processed_images += 1
                    else:
                        process_logger.error("QR not found for file {}".format(filename))
                empty_folder(input_folder)
                empty_folder(temp_folder)
            session_folder.close_session(s3, bucket_name, process_logger)
        except Exception as e:
            process_logger.error(e, exc_info=True)
    s3.close()
    try:
        shutil.rmtree(input_folder)
        shutil.rmtree(temp_folder)
        process_logger.close()
        log_object.failed_images = log_object.found_images - log_object.processed_images
        with open(process_logger.file_path, "rb") as log_file:
            log_object.file.save(
                f"scheduled/{log_object.date.strftime('%Y-%m-%d')}.log",
                ContentFile(log_file.read()),
                save=True
            )
        log_object.save()
        shutil.rmtree(log_folder)
        return "Processed"
    except Exception as e:
        logging.error(e, exc_info=True)
        return str(e)


def get_pending_sessions(s3: boto3.client, input_folder: str, logger: logging.Logger) -> List[SessionFolder]:
    bucket_name = settings.AWS_STORAGE_BUCKET_NAME
    input_path = f"digitalization/{input_folder}/"
    response = s3.list_objects_v2(
        Bucket=bucket_name,
        Delimiter='/',
        Prefix=input_path,
    )
    out = list()
    institutions_folder = [prefix.get("Prefix") for prefix in response.get('CommonPrefixes', [])]
    for institution_path in institutions_folder:
        institution = institution_path.replace(input_path, "").strip("/")
        logger.info("Institution {} at {}".format(institution, institution_path))
        response = s3.list_objects_v2(
            Bucket=bucket_name,
            Delimiter='/',
            Prefix=institution_path,
        )
        sessions_candidates = [prefix.get("Prefix") for prefix in response.get('CommonPrefixes', [])]
        for session_folder in sessions_candidates:
            session_name = session_folder.replace(institution_path, "").strip("/")
            response = s3.list_objects_v2(
                Bucket=bucket_name,
                Prefix=session_folder,
            )
            content = [obj['Key'] for obj in response.get('Contents', [])]
            if f"{session_folder}processed" in content:
                logger.debug("Session folder `{}` already processed".format(session_name))
            else:
                logger.debug("Session folder `{}` to be processed".format(session_name))
                out.append(SessionFolder(institution, session_name, input_folder, input_path))
                out[-1].add_files(content)
    return out


@shared_task(name='clean_storage')
def clean_storage(log_folder: str):
    os.makedirs(log_folder, exist_ok=True)
    process_logger = TaskProcessLogger("Clean Storage", log_folder)
    try:
        s3 = boto3.client('s3')
        bucket = settings.AWS_STORAGE_BUCKET_NAME
        process_logger.info("Cleaning Public Storage...")
        public_location = PublicMediaStorage().location
        paginator = s3.get_paginator("list_objects_v2")
        page_response = paginator.paginate(Bucket=bucket, Prefix=public_location)
        to_delete = list()
        public_files_to_delete = 0
        for i, response in enumerate(page_response):
            process_logger.debug(f"Page: {i + 1}")
            if 'Contents' in response:
                for obj in response['Contents']:
                    file_name = obj['Key'].replace(public_location + "/", "")
                    found = False
                    for model, field, contains, extension in [
                        (GalleryImage, "image", "", ".jpg"),
                        (GalleryImage, "thumbnail", "_thumbnail", ".jpg"),
                        (BannerImage, "banner", "", ".png"),
                        (VoucherImported, "image_public_resized_10", "_public_resized_10", ".jpg"),
                        (VoucherImported, "image_public_resized_60", "_public_resized_60", ".jpg"),
                        (VoucherImported, "image_public", "_public", ".jpg"),
                    ]:
                        found = found or check_on_model(file_name, model, field, contains, extension, process_logger)
                        if found:
                            break
                    if not found:
                        process_logger.error(f"{file_name} not found on database")
                        to_delete.append((obj['Key'], obj['Size']))
                        public_files_to_delete += 1
        process_logger.info(f"Public files to delete {public_files_to_delete}")
        process_logger.info("Cleaning Private Storage...")
        private_location = PrivateMediaStorage().location
        page_response = paginator.paginate(Bucket=bucket, Prefix=private_location)
        private_files_to_delete = 0
        for i, response in enumerate(page_response):
            process_logger.debug(f"Page: {i + 1}")
            if 'Contents' in response:
                for obj in response['Contents']:
                    file_name = obj['Key'].replace(private_location + "/", "")
                    found = False
                    for model, field, contains, extension in [
                        (ColorProfileFile, "file", "", ".dcp"),
                        (PriorityVouchersFile, "file", "", ".xls"),
                        (PriorityVouchersFile, "file", "", ".xlsx"),
                        (PostprocessingLog, "file", "", ".log"),
                        (VoucherImported, "image_raw", "", ".CR3"),
                        (VoucherImported, "image_resized_10", "_resized_10", ".jpg"),
                        (VoucherImported, "image_resized_60", "_resized_60", ".jpg"),
                        (VoucherImported, "image", "", ".jpg"),
                    ]:
                        found = found or check_on_model(file_name, model, field, contains, extension, process_logger)
                        if found:
                            break
                    if not found:
                        process_logger.error(f"{file_name} not found on database")
                        to_delete.append((obj['Key'], obj['Size']))
                        private_files_to_delete += 1
        process_logger.info(f"Private files to delete {private_files_to_delete}")
        assert len(to_delete) == public_files_to_delete + private_files_to_delete, "Error on number of files to delete"
        process_logger.info(f"Files to delete {len(to_delete)}")
        total_size_save = 0
        for file_name, file_size in to_delete:
            try:
                process_logger.info(f"Deleting `{file_name}` ({show_storage(file_size)})")
                s3.delete_object(Bucket=bucket, Key=file_name)
                total_size_save += file_size
                process_logger.debug(f"Total size saved: {show_storage(total_size_save)}")
            except Exception as e:
                process_logger.error(e, exc_info=True)
        process_logger.info(f"Total size saved: {show_storage(total_size_save)}")
        s3.close()
    except Exception as e:
        process_logger.error(e, exc_info=True)
    process_logger.close()
    return "Cleaned"


def check_on_model(
        file_name: str, model: Type[Model],
        field: str, contains: str, extension: str,
        logger: logging.Logger
) -> bool:
    prefix = model._meta.get_field(field).upload_to
    if prefix != "":
        prefix = prefix if prefix.endswith("/") else prefix + "/"
    if file_name.startswith(prefix) and contains in file_name and file_name.endswith(extension):
        if model.objects.filter(**{field: file_name}).exists():
            return True
        else:
            logger.warning(f"{model.__name__}.{field} does not include `{file_name}` file")
            return False
    else:
        return False


def show_storage(storage: int):
    order = int(math.log(storage) / math.log(1024))
    suffixes = ['B', 'KB', 'MB', 'GB', 'TB', 'PB']
    if order >= len(suffixes):
        order = len(suffixes) - 1
    human_readable = storage / (1024 ** order)
    return f"{human_readable:.2f} {suffixes[order]}"


@shared_task(name='process_pending_vouchers', bind=True)
def process_pending_vouchers(self, pending_vouchers: List[str], user: int) -> str:
    html_logger = HtmlLogger("Pending Logger")
    temp_folder = self.request.id
    logging.info("Pending vouchers: {}".format(", ".join(pending_vouchers)))
    total = len(pending_vouchers)
    os.makedirs(temp_folder, exist_ok=True)
    log_object = PostprocessingLog(
        date=dt.datetime.now(),
        found_images=total,
        created_by=User.objects.get(pk=user),
        scheduled=False
    )
    process_logger = TaskProcessLogger("Pending Logger", temp_folder)
    logger = GroupLogger("Pending Logger", html_logger, process_logger)
    for i, voucher in enumerate(pending_vouchers):
        try:
            voucher_imported: VoucherImported = VoucherImported.objects.get(pk=int(voucher))
            raw_file = voucher_imported.image_raw.name
            logger.info(f"Saving file as {raw_file}...")
            with PrivateMediaStorage().open(raw_file) as raw_image_file:
                with open(os.path.join(temp_folder, raw_file), "wb") as local_file:
                    local_file.write(raw_image_file.read())
            cr3_to_dng(temp_folder, temp_folder, logger)
            self.update_state(state='PROGRESS', meta={
                "step": i, "total": total, "logs": logger[0].get_logs()
            })
            if not os.path.exists(os.path.join(temp_folder, raw_file.replace(".CR3", ".dng"))):
                raise FileNotFoundError(f"File {raw_file} cannot be converted to .dng")
            dng_to_jpeg_color_profile(
                temp_folder, temp_folder, voucher_imported.herbarium.collection_code,
                voucher_imported.biodata_code.page.color_profile.file.url, logger
            )
            if not os.path.exists(os.path.join(temp_folder, raw_file.replace(".CR3", ".jpg"))):
                raise FileNotFoundError(f"File {raw_file} cannot be converted to .jpg")
            self.update_state(state='PROGRESS', meta={
                "step": i, "total": total, "logs": logger[0].get_logs()
            })
            with open(os.path.join(temp_folder, raw_file.replace(".CR3", ".jpg")), "rb") as image_file:
                voucher_imported.upload_image(image_file)
                image = Image.open(image_file)
                for scale_percent in [10, 60]:
                    resized_image = change_image_resolution(image, scale_percent)
                    voucher_imported.upload_scaled_image(resized_image, scale_percent)
                voucher_imported.save()
                self.update_state(state='PROGRESS', meta={
                    "step": i, "total": total, "logs": logger[0].get_logs()
                })
                etiquette_picture(int(voucher), logger=logger)
            log_object.processed_images += 1
        except Exception as e:
            logger.error(e, exc_info=True)
            log_object.failed_images += 1
        finally:
            self.update_state(
                state='PROGRESS',
                meta={
                    "step": i + 1,
                    "total": total,
                    "logs": logger[0].get_logs()
                }
            )
            logger.debug("Cleaning folder")
            for tmp_file in os.listdir(temp_folder):
                if os.path.splitext(tmp_file)[1] in [".jpg", ".CR3", ".dng"]:
                    os.remove(os.path.join(temp_folder, tmp_file))
    try:
        logger[1].close()
        with open(logger[1].file_path, "rb") as log_file:
            log_object.file.save(
                f"manually/{self.request.id}.log",
                ContentFile(log_file.read()),
                save=True
            )
        log_object.save()
        close_process(logger[0], self, {"step": total, "total": total, })
        shutil.rmtree(temp_folder)
        return "Processed"
    except Exception as e:
        logging.error(e, exc_info=True)
        return str(e)


@shared_task(name="upload_priority_vouchers", bind=True)
def upload_priority_vouchers(self, priority_voucher: int):
    html_logger = HtmlLogger("Priority Logger")
    temp_folder = self.request.id
    os.makedirs(temp_folder, exist_ok=True)
    process_logger = TaskProcessLogger("Priority Logger", temp_folder)
    logger = GroupLogger("Priority Logger", html_logger, process_logger)
    priorities = PriorityVouchersFile.objects.get(pk=priority_voucher)
    logger.info("Reading priorities...")
    logger.debug(f"Reading excel file {priorities.file.name}")
    self.update_state(
        state='PROGRESS',
        meta={
            "step": 0,
            "total": 1,
            "logs": logger[0].get_logs()
        }
    )
    total = 1
    error = dict()
    on_database = False
    missing_species = False
    code_error = False
    try:
        data = pd.read_excel(priorities.file, header=0)
        data.rename(columns=DCW_SQL, inplace=True)
        sql_dcw = {v: k for k, v in DCW_SQL.items()}
        database_errors = list()
        species_errors = list()
        errors = list()
        logger.info("Checking duplications in file")
        duplicated = data[data.duplicated(["catalog_number"], keep=False)]
        logger.debug(f"Found {len(duplicated)} row duplicated")
        if len(duplicated) != 0:
            error["type"] = "duplicates in file"
            error["data"] = duplicated.rename(columns=sql_dcw).to_json()
            raise AssertionError("Duplicated rows on file")
        with transaction.atomic():
            logger.info("Checking rows")
            total = len(data)
            for i, (index, row) in enumerate(data.iterrows()):
                try:
                    code = "{}:{}:{:07d}".format(
                        priorities.herbarium.institution_code,
                        priorities.herbarium.collection_code,
                        row["catalog_number"]
                    )
                    biodata_codes = BiodataCode.objects.filter(code=code).all()
                    if len(biodata_codes) != 0:
                        logger.warning(f"Code {code} already on database")
                        biodata_code = biodata_codes[0]
                        if biodata_code.voucher_state in [0, 1, 7, 8]:
                            logger.error(
                                f"{code} is assigned to a '{biodata_code.get_voucher_state_display()}' voucher"
                            )
                            database_errors.append(row)
                            on_database = True
                            continue
                        else:
                            logger.debug(f"Overwriting code '{code}'")
                            biodata_code.delete()
                    biodata_code = BiodataCode(
                        herbarium=priorities.herbarium,
                        code=code,
                        catalog_number=row["catalog_number"],
                        created_by=priorities.created_by,
                        created_at=dt.datetime.now(tz=pytz.timezone('America/Santiago')),
                        qr_generated=False
                    )
                    biodata_code.save()
                    logger.debug(f"New occurrence ({biodata_code.id}) added with code {code}")
                    species, info = get_species(row, logger)
                    if species is None:
                        species_errors.append(info)
                        missing_species = True
                        continue
                    voucher_imported = VoucherImported.from_pandas_row(
                        row, priorities, species=species, biodata_code=biodata_code, logger=logger
                    )
                    voucher_imported.save()
                except Exception as e:
                    logger.error(e, exc_info=True)
                    errors.append(row)
                    code_error = True
                finally:
                    self.update_state(
                        state='PROGRESS',
                        meta={
                            "step": i,
                            "total": total,
                            "logs": logger[0].get_logs(),
                        }
                    )
            if on_database:
                error["type"] = "duplicates in database"
                error["data"] = pd.DataFrame(database_errors).rename(columns=sql_dcw).to_json()
                raise AssertionError("Codes presented on database")
            if missing_species:
                error["type"] = "no match with catalog"
                error["data"] = pd.DataFrame(species_errors).rename(columns=sql_dcw).to_json()
                raise ValueError("Some species are not in database of catalog")
            if code_error:
                error["type"] = "code"
                error["data"] = pd.DataFrame(errors).rename(columns=sql_dcw).to_json()
                raise RuntimeError("Error during import data on server, check logs for details")
        logger[1].close()
        logger[1].save_file(PrivateMediaStorage(), temp_folder + ".log")
        close_process(logger[0], self, {"step": total, "total": total, })
        shutil.rmtree(temp_folder)
        return "Processed"
    except Exception as e:
        logger.error(e, exc_info=True)
        logger.warning("Deleting failed priority file")
        try:
            priorities.file.delete(save=False)
            priorities.delete()
            logger.info("Priority file deleted.")
        except Exception as e:
            logger.error(e, exc_info=True)
            logger.info("Error deleting file!")
        logger[1].close()
        logger[1].save_file(PrivateMediaStorage(), temp_folder + ".log")
        close_process(logger[0], self, {"step": total, "total": total, }, error=error)
        shutil.rmtree(temp_folder)
        raise Ignore()


def get_species(data_candid: pd.Series, logger: logging.Logger) -> Tuple[Species, pd.Series]:
    info = data_candid.copy(deep=True)
    species = Species.objects.filter(scientific_name_db=data_candid["scientific_name"].strip()).first()
    if species is None:
        logger.warning("Searching using trigram similarity")
        similarity_values = Species.objects.annotate(
            similarity=TrigramSimilarity(
                'scientific_name_db',
                data_candid['scientific_name'].strip().upper()
            ),
        ).filter(
            similarity__gte=0.55
        ).order_by('-similarity')
        if len(similarity_values) > 0:
            logger.debug("Similarity found on accepted species")
            if similarity_values[0].similarity < 1:
                info['similarity'] = similarity_values[0].similarity
                info['scientific_name_similarity'] = similarity_values[0].scientific_name
                info['synonymy_similarity'] = ''
            else:
                logger.warning("Error on similarity found")
        else:
            similarity_values = Synonymy.objects.annotate(
                similarity=TrigramSimilarity(
                    'scientific_name_db',
                    data_candid['scientific_name'].strip().upper()
                ),
            ).filter(
                similarity__gte=0.55
            ).order_by('-similarity')
            if len(similarity_values) > 0:
                logger.debug("Similarity found on synonym")
                info['similarity'] = similarity_values[0].similarity
                species_synonymy = Species.objects.filter(synonyms=similarity_values[0].id)
                info['scientific_name_similarity'] = species_synonymy[0].scientific_name
                info['synonymy_similarity'] = similarity_values[0].scientific_name
            else:
                logger.warning("No similarity found")
                info['similarity'] = 0
                info['scientific_name_similarity'] = ''
                info['synonymy_similarity'] = ''
    else:
        logger.debug(f"Species {data_candid['scientific_name'].strip()} found")
    return species, info


def close_process(logger: HtmlLogger, task: Task, meta: Dict, error: Dict = None) -> None:
    meta["logs"] = logger.get_logs()
    if error is None:
        task.update_state(
            state='SUCCESS',
            meta=meta,
        )
        return
    else:
        meta["error"] = error
        task.update_state(
            state='ERROR',
            meta=meta
        )
        return


@shared_task(name="extract_taken_by", bind=True)
def get_taken_by(self, image_path: str, logger: logging.Logger = None) -> Tuple[str, str]:
    if logger is None:
        logger = logging.getLogger(__name__)
    logger.info(f"Image to process: {image_path}")
    try:
        image = PrivateMediaStorage().open(image_path)
        self.update_state(state="PROGRESS", meta={"on": "Image loaded"})
        arr = np.asarray(bytearray(image.read()), dtype=np.uint8)
        img = cv2.imdecode(arr, -1)
        self.update_state(state="PROGRESS", meta={"on": "Image converted"})
        text = pytesseract.image_to_string(img)
        self.update_state(state="PROGRESS", meta={"on": "Text found"})
        taken_by = GalleryImage.objects.filter(
            taken_by__isnull=False
        ).values("taken_by").distinct().annotate(
            similarity=TrigramSimilarity('taken_by', text),
        ).order_by('-similarity')
        self.update_state(state="PROGRESS", meta={"on": "Looking for similar"})
        candidate = taken_by.first()["taken_by"]
    except Exception as e:
        logger.error(e, exc_info=True)
        self.update_state(state='ERROR', meta={"error": str(e)})
        text = ""
        candidate = ""
    return text, candidate


@shared_task(name="generate_thumbnail")
def generate_thumbnail(gallery_id: int) -> None:
    try:
        gallery: GalleryImage = GalleryImage.objects.get(pk=gallery_id)
        image = Image.open(gallery.image)
        gallery.aspect_ratio = image.size[0] / image.size[1]
        scale_percent = 200 * 100 / image.size[1]
        resized_image = change_image_resolution(image, scale_percent)
        image_content = ContentFile(resized_image.read())
        filepath = os.path.basename(gallery.image.name)
        filename, ext = os.path.splitext(filepath)
        image_name = f"{filename}_thumbnail{ext}"
        gallery.thumbnail.save(image_name, image_content, save=True)
        gallery.save()
        logging.info(f"{image_name} saved")
    except Exception as e:
        logging.error(f"Error on thumbnail: {e}", exc_info=True)
        return
