import glob
import glob
import logging
import os
import re
import shutil
import subprocess
import uuid
from io import BytesIO
from typing import Set, Union, List

import boto3
import cv2
import numpy as np
from PIL.Image import Image
from django.contrib.auth.models import User
from django.contrib.gis.geos import GEOSGeometry
from django.template.loader import get_template
from pyzbar.pyzbar import decode, ZBarSymbol  # Para la decodificación de códigos QR
from xhtml2pdf import pisa

from apps.digitalization.models import TemporalArea


def log_stdout_stderr(out: bytes, err: bytes, logger: logging.Logger, log_cache: Set[str] = None) -> None:
    """
    Logs the stdout and stderr of subprocess

    Parameters
    ----------
    out : bytes
        Standard output of subprocess
    err : bytes
        Standard output of subprocess
    logger : Logger
        Specialize logger
    log_cache : Set[str]
        Current log

    Returns
    -------
    None
    """
    for log in out.decode("utf-8").split("\n"):
        if log == "":
            continue
        if log_cache is None or log not in log_cache:
            logger.debug(log)
        if log_cache is not None:
            log_cache.add(log)
    for log in err.decode("utf-8").split("\n"):
        if log == "":
            continue
        if log_cache is None or log not in log_cache:
            logger.warning(log)
        if log_cache is not None:
            log_cache.add(log)
    return


class S3File:
    def __init__(self, file_path: str, remote_path: str, input_folder: str) -> None:
        self.__input_folder__ = input_folder
        self.__remote_path__ = remote_path
        self.__filename__ = file_path.split(remote_path + "/")[1]
        return

    def download(self, s3: boto3.client, bucket_name: str, logger: logging.Logger = None) -> None:
        """
        Downloads image on path

        Parameters
        ----------
        s3 : boto3.client
            S3 client to execute download
        bucket_name : str
            Bucket name
        logger : Logger
            Object to manage logs

        Returns
        -------
        None
        """
        if logger is None:
            logger = logging.getLogger(__name__)
        remote_path = f"{self.__remote_path__}/{self.__filename__}"
        logger.debug("Downloading {}".format(remote_path))
        s3.download_file(
            bucket_name, remote_path,
            os.path.join(self.__input_folder__, self.__filename__)
        )
        return

    def __unicode__(self) -> str:
        """
        String representation

        Returns
        -------
        str
            Representation of Session Folder
        """
        return "S3 file <location=s3://{}><filename={}>".format(
            self.__remote_path__, self.__filename__
        )

    def __str__(self) -> str:
        """
        String representation

        Returns
        -------
        str
            Representation of Session Folder
        """
        return self.__unicode__()

    def __repr__(self) -> str:
        """
        String representation

        Returns
        -------
        str
            Representation of Session Folder
        """
        return self.__unicode__()


class SessionFolder:
    def __init__(self, institution: str, session: str, input_folder: str, remote_folder: str) -> None:
        self.__institution__ = institution
        self.__session__ = session
        self.__files__: Set[S3File] = set()
        self.__input_folder__ = input_folder
        self.__remote_prefix__ = f"{remote_folder}{institution}/{session}"
        return

    def get_institution(self) -> str:
        return self.__institution__

    def add_files(self, files: List[str]) -> None:
        """
        Adds files to Session Folder to be
        processed

        Parameters
        ----------
        files : List[str]
            List of candidate files

        Returns
        -------
        None
        """
        for file in files:
            file_name, file_extension = os.path.splitext(file)
            if file_extension == ".CR3":
                self.__files__.add(S3File(
                    file, self.__remote_prefix__,
                    self.__input_folder__
                ))
        return

    def create_folder(self) -> None:
        """
        Creates folder to manipulate files

        Returns
        -------
        None
        """
        os.makedirs(self.__input_folder__, exist_ok=True)

    def download(self, s3: boto3.client, bucket_name: str, logger: logging.Logger = None) -> None:
        """
        Downloads all images on path

        Parameters
        ----------
        s3 : boto3.client
            S3 client to execute download
        bucket_name : str
            Bucket name
        logger : Logger
            Object to manage logs

        Returns
        -------
        None
        """
        for file in self.__files__:
            file.download(s3, bucket_name, logger=logger)
        return

    def close_session(self, s3: boto3.client, bucket_name: str, logger: logging.Logger = None) -> None:
        """
        Uploads a `processed` file to folder

        s3 : boto3.client
            S3 client to execute download
        bucket_name : str
            Bucket name
        logger : Logger
            Object to manage logs

        Returns
        -------
        None
        """
        if logger is None:
            logger = logging.getLogger(__name__)
        try:
            s3.upload_file(
                "assets/processed",
                bucket_name,
                f"{self.__remote_prefix__}/processed"
            )
        except Exception as e:
            logger.error("Error uploading processed, upload it by hand")
            logger.error(e, exc_info=True)
        finally:
            return

    def __len__(self) -> int:
        """
        Get number of files

        Returns
        -------
        int
            Files on session folder
        """
        return len(self.__files__)

    def __unicode__(self) -> str:
        """
        String representation

        Returns
        -------
        str
            Representation of Session Folder
        """
        return "Session Folder <location=s3://{}/><images={}>".format(
            self.__remote_prefix__, self.__len__()
        )

    def __str__(self) -> str:
        """
        String representation

        Returns
        -------
        str
            Representation of Session Folder
        """
        return self.__unicode__()

    def __repr__(self) -> str:
        """
        String representation

        Returns
        -------
        str
            Representation of Session Folder
        """
        return self.__unicode__()


def __subprocess__(command: List[str], logger: logging.Logger, log_cache: Set[str]) -> None:
    p = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    out, err = p.communicate()
    log_stdout_stderr(out, err, logger, log_cache)
    return


def cr3_to_dng(
        file_path_in: str, file_path_out: str,
        logger: logging.Logger, log_cache: Set[str] = None
) -> None:
    """
    Convert CR3 to DNG format

    Parameters
    ----------
    file_path_in : str
        File path where to convert files
    file_path_out : str
        File path where to put converted files
    logger : Logger
        Object Logger
    log_cache : Set[str]
        Current log

    Returns
    -------
    None
    """
    logger.info("Transforming to DNG...")
    os.makedirs(file_path_out, exist_ok=True)
    command = ["dnglab", "convert", "-r", file_path_in, file_path_out]
    logger.info("Executing: {}".format(" ".join(command)))
    __subprocess__(command, logger, log_cache)
    return


def dng_to_jpeg(
        file_path_in: str, file_path_out: str,
        herbarium: str, logger: logging.Logger,
        log_cache: Set[str] = None
) -> None:
    """
    Convert CR3 to JPEG format

    Parameters
    ----------
    file_path_in : str
        File path where to convert files
    file_path_out : str
        File path where to put files converted
    herbarium : str
        Herbarium code for retrieve format files
    logger : Logger
        Object Logger
    log_cache : Set[str]
        Current log

    Returns
    -------
    None
    """
    logger.info("Transforming to JPEG...")
    os.makedirs(file_path_out, exist_ok=True)
    for filename in glob.glob(file_path_in + '/*.dng', recursive=True):
        if os.path.exists(filename.replace(".dng", ".jpg")):
            logger.warning("{} already converted, skipping".format(filename))
            continue
        processing_profile_file = "assets/processing_profiles/herbarium_{}.pp3".format(herbarium)
        command = [
            'rawtherapee-cli', '-o', file_path_out,
            '-d', '-j100', '-js3', '-Y',
            '-p', processing_profile_file,
            '-c', filename
        ]
        logger.info("Executing: {}".format(" ".join(command)))
        __subprocess__(command, logger, log_cache)
    return


def dng_to_jpeg_color_profile(
        file_path_in: str, file_path_out: str,
        herbarium: str, color_profile: str,
        logger: logging.Logger,
        log_cache: Set[str] = None
) -> None:
    origin_profile = "assets/processing_profiles/herbarium_cdp_{}.pp3".format(herbarium)
    rawtherapee_profile = os.path.join(file_path_in, "herbarium_cdp_{}.pp3".format(herbarium))
    with open(origin_profile, "r") as file:
        prev_content = file.read()
    with open(rawtherapee_profile, "w") as file:
        file.write(prev_content.format(color_profile))
    os.makedirs(file_path_out, exist_ok=True)
    for filename in glob.glob(file_path_in + '/*.dng', recursive=True):
        previous_file = False
        expected_output = filename.replace(".dng", ".jpg")
        if os.path.exists(expected_output):
            previous_file = True
            os.rename(expected_output, expected_output + "_(old)")
        command = [
            'rawtherapee-cli', '-o', file_path_out,
            '-d', '-j100', '-js3', '-Y',
            '-p', rawtherapee_profile, '-c', filename
        ]
        logger.info("Executing: {}".format(" ".join(command)))
        __subprocess__(command, logger, log_cache)
        if previous_file:
            if os.path.exists(expected_output):
                os.remove(expected_output + "_(old)")
            else:
                logging.warning("Error converting {} with color profile".format(expected_output))
                os.rename(expected_output + "_(old)", expected_output)
    with open(rawtherapee_profile, "w") as file:
        file.write(prev_content)
    return


def read_qr(filename: str, logger: logging.Logger) -> Union[None, str]:
    """
    Given the name of the file that contains an image, the image is read and 
    then divided into 4 zones. A QR is searched in each of them sequentially 
    using different image preprocessing methods.

    Parameters
    ----------
    filename : str
        File path to image to process
    logger : Logger
        Object Logger

    Returns
    -------
    str
        In case of found, the code on QR at the image. Otherwise None.
    """

    logging.info("Reading QR of {}...".format(filename))
    p = re.compile('(?<!\\\\)\'')

    image = cv2.imread(filename, cv2.IMREAD_GRAYSCALE)
    read_functions = [read_qr_at_top_right, read_qr_at_top_left, read_qr_at_bottom_left, read_qr_at_bottom_right]

    try:
        if image is not None:
            for read_function in read_functions:
                qr_code = read_function(p, image, logger, 'resize')
                if qr_code:
                    return qr_code
            
            for read_function in read_functions:
                qr_code = read_function(p, image, logger, 'no_filter')
                if qr_code:
                    return qr_code
                
            for read_function in read_functions:
                qr_code = read_function(p, image, logger, 'median')
                if qr_code:
                    return qr_code
            
            logging.error("QR code on {} not detected".format(filename))
            return None
        
    except Exception as e:
        logging.error("QR code reading error:\n{}".format(e))
        return None


def __read_qr_at__(
        p: re.Pattern, cropped_image: np.ndarray, 
        found_message: str, logger: logging.Logger, 
        filter: str
) -> Union[str, None]:
    
    """
    Reads the QR in an image using some method specified in the 'filter' argument.

    Parameters
    ----------
    p : Pattern
        Regular expression pattern
    cropped_image : ND-Array
        Array of N=2 dimension coding an image
    found_message : Str
        Custom message delivered when finding a QR
    logger : Logger
        Object Logger
    filter : Str
        String specifying the image preproceessing method

    Returns
    -------
    str
        In case of found, the code on the QR. otherwise None.
    """
    
    image_to_process = None 
    
    if filter == 'no_filter':
        logger.debug("Looking for QR in {}".format(found_message))
        image_to_process = cropped_image

    elif filter == 'resize':
        logger.debug("Looking for QR in {} with {}".format(found_message, filter))
        image_to_process = cv2.resize(cropped_image, None, fx=0.5, fy=0.5, interpolation=cv2.INTER_LINEAR)

    elif filter == 'median':
        logger.debug("Looking for QR in {} with {} filter".format(found_message, filter))
        image_to_process = cv2.medianBlur(cropped_image, 7)
    
    else:
        logger.error("No filter specified")
        raise ValueError("Se debe especificar el filtro que se está aplicando (o no) en el agrumento de la funcion")
    
    code = decode(image_to_process, [ZBarSymbol.QRCODE])

    if code:
        decoded_text = code[0].data.decode('utf8')
        logger.debug("Decoded Text '{}'".format(decoded_text))
        logger.info("QR found in {}".format(found_message))
        return p.sub('\"', decoded_text)
    else:
        return None


def read_qr_at_top_right(
        p: re.Pattern, image: np.ndarray,
        logger: logging.Logger, filter: str
) -> Union[str, None]:
    """
    Crops the top right of image and read QR in that zone using the auxiliary function 
    __read__qr__at__.

    Parameters
    ----------
    p : Patter
        Regular expression pattern
    image : ND-Array
        Array of N=2 dimension coding an image
    logger : Logger
        Object Logger

    Returns
    -------
    str
        In case of found, the code on the QR. otherwise None.
    """

    height, widht = image.shape
    cropped_image = image[:height // 2, widht // 2:]

    return __read_qr_at__(p, cropped_image, "top right corner", logger, filter)


def read_qr_at_top_left(
        p: re.Pattern, image: np.ndarray,
        logger: logging.Logger, filter: str
) -> Union[str, None]:
    """
    Crops the top left of image and read QR in that zone using the auxiliary function 
    __read__qr__at__.

    Parameters
    ----------
    p : Patter
        Regular expression pattern
    image : ND-Array
        Array of N=2 dimension coding an image
    logger : Logger
        Object Logger

    Returns
    -------
    str
        In case of found, the code on the QR. otherwise None.
    """

    height, widht = image.shape
    cropped_image = image[:height // 2, :widht // 2]

    return __read_qr_at__(p, cropped_image, "top left corner", logger, filter)


def read_qr_at_bottom_left(
        p: re.Pattern, image: np.ndarray,
        logger: logging.Logger, filter:str
) -> Union[str, None]:
    """
    Crops the bottom left of image and read QR in that zone using the auxiliary function 
    __read__qr__at__.

    Parameters
    ----------
    p : Patter
        Regular expression pattern
    image : ND-Array
        Array of N=2 dimension coding an image
    logger : Logger
        Object Logger

    Returns
    -------
    str
        In case of found, the code on the QR. otherwise None.
    """

    height, widht = image.shape
    cropped_image = image[height // 2:, :widht // 2]

    return __read_qr_at__(p, cropped_image, "bottom left corner", logger, filter)


def read_qr_at_bottom_right(
        p: re.Pattern, image: np.ndarray,
        logger: logging.Logger, filter: str
) -> Union[str, None]:
    """
    Crops the bottom right of image and read QR in that zone using the auxiliary function 
    __read__qr__at__.

    Parameters
    ----------
    p : Patter
        Regular expression pattern
    image : ND-Array
        Array of N=2 dimension coding an image
    logger : Logger
        Object Logger

    Returns
    -------
    str
        In case of found, the code on the QR. otherwise None.
    """

    height, widht = image.shape
    cropped_image = image[height // 2:, widht // 2:]
    
    return __read_qr_at__(p, cropped_image, "bottom right corner", logger, filter)



def change_image_resolution(image: Image, scale_percent) -> BytesIO:
    width = int(image.size[0] * scale_percent / 100)
    height = int(image.size[1] * scale_percent / 100)
    resized_image = image.resize((width, height))
    resized_image_content = BytesIO()
    resized_image.save(resized_image_content, format='JPEG')
    resized_image_content.seek(0)
    return resized_image_content


def empty_folder(folder_path: str) -> None:
    for content in os.listdir(folder_path):
        content_path = os.path.join(folder_path, content)
        try:
            if os.path.isfile(content_path):
                os.remove(content_path)
            elif os.path.isdir(content_path):
                shutil.rmtree(content_path)
        except Exception as e:
            logging.error(f"Failed to delete {content_path}. Exception: {e}", exc_info=True)


def render_to_pdf(template_src, context_dict):
    template = get_template(template_src)
    html_template = template.render(context_dict)
    result = BytesIO()
    pdf = pisa.pisaDocument(
        src=BytesIO(html_template.encode('UTF-8')),
        dest=result,
        encoding='UTF-8'
    )
    if pdf.err:
        return 'We had some errors <pre>' + html_template + '</pre>'
    return result.getvalue()


def register_temporal_geometry(geometry: GEOSGeometry) -> int:
    areas = TemporalArea(
        name=f"temp_{uuid.uuid4().hex}",
        geometry=geometry,
        created_by=User.objects.get(pk=1)
    )
    try:
        areas.save()
        logging.debug(f"Registered new area with id `{areas.pk}`")
        return areas.pk
    except Exception as e:
        logging.error(f"Cannot save area: {e}", exc_info=True)
        return -1
