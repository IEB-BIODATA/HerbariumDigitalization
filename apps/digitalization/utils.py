import datetime as dt
import glob
import html
import logging
import os
import re
import shutil
import subprocess
import traceback
import uuid
from io import BytesIO
from typing import Set, Union, Dict, Tuple, List, Any, Sequence

import boto3
import cv2
import numpy as np
from PIL.Image import Image
from django.contrib.auth.models import User
from django.contrib.gis.geos import GEOSGeometry
from django.core.files.base import ContentFile
from django.core.files.storage import Storage
from django.template.loader import get_template
from xhtml2pdf import pisa

from apps.digitalization.models import Areas


class TaskProcessLogger(logging.Logger):
    def __init__(self, name: str, path_file: str):
        super().__init__(name)
        self.__path__ = os.path.join(
            path_file, dt.datetime.today().strftime("%Y-%m-%d") + ".log"
        )
        self.__log_file__ = open(self.__path__, "a+", encoding="utf-8")

    def __message__(self, level: str, message: Any, **kwargs) -> None:
        self.__log_file__.write("{} [{}]:{}\n".format(
            dt.datetime.now().strftime("%Y-%m-%d %I:%M:%S"),
            level,
            str(message)
        ))
        if kwargs.get("exc_info", False):
            self.__log_file__.write(traceback.format_exc() + "\n")

    def debug(self, message: Any, **kwargs) -> None:
        self.__message__("DEBUG", message, **kwargs)

    def info(self, message: Any, **kwargs) -> None:
        self.__message__("INFO", message, **kwargs)

    def warning(self, message: Any, **kwargs) -> None:
        self.__message__("WARN", message, **kwargs)

    def error(self, message: Any, **kwargs) -> None:
        self.__message__("ERROR", message, **kwargs)

    def save_file(self, storage: Storage, file_name: str) -> None:
        with open(self.__path__, "rb") as file:
            storage.save(file_name, ContentFile(file.read()))
        return

    def close(self) -> None:
        self.__log_file__.close()
        return


class HtmlLogger(logging.Logger):
    def __init__(self, name: str):
        super().__init__(name)
        self.__logs__ = ""

    def __message__(self, level: str, message: Any, **kwargs) -> None:
        escaped_msg = html.escape("{} [{}]:{}".format(
            dt.datetime.now().strftime("%Y-%m-%d %I:%M:%S"),
            level,
            str(message)
        ))
        self.__logs__ += f'<code class="{level.lower()}">{escaped_msg}</code><br>'
        if kwargs.get("exc_info", False):
            for line in traceback.format_exc().split("\n"):
                escaped_line = html.escape(line)
                self.__logs__ += f'<code class="{level.lower()}">{escaped_line}</code><br>'

    def debug(self, message: Any, **kwargs) -> None:
        self.__message__("DEBUG", message, **kwargs)

    def info(self, message: Any, **kwargs) -> None:
        self.__message__("INFO", message, **kwargs)

    def warning(self, message: Any, **kwargs) -> None:
        self.__message__("WARN", message, **kwargs)

    def error(self, message: Any, **kwargs) -> None:
        self.__message__("ERROR", message, **kwargs)

    def get_logs(self) -> str:
        return self.__logs__


class GroupLogger(logging.Logger, Sequence):
    def __init__(self, name: str, *args):
        super().__init__(name)
        self.__loggers__ = list()
        for arg in args:
            assert isinstance(arg, logging.Logger), f"{arg} is not a Logger object"
            self.__loggers__.append(arg)

    def __getitem__(self, index: int) -> logging.Logger:
        return self.__loggers__[index]

    def __len__(self) -> int:
        return len(self.__loggers__)

    def debug(self, message: Any, **kwargs) -> None:
        for logger in self.__loggers__:
            logger.debug(message, **kwargs)

    def info(self, message: Any, **kwargs) -> None:
        for logger in self.__loggers__:
            logger.info(message, **kwargs)

    def warning(self, message: Any, **kwargs) -> None:
        for logger in self.__loggers__:
            logger.warning(message, **kwargs)

    def error(self, message: Any, **kwargs) -> None:
        for logger in self.__loggers__:
            logger.error(message, **kwargs)


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


def read_qr(filename: str,
            width_crop: int, height_crop: int,
            margin: int, corner: Dict[str, Tuple[int]],
            logger: logging.Logger) -> Union[None, str]:
    """
    Reads a QR code on an image on filename

    Parameters
    ----------
    filename : str
        File path to image to process
    width_crop : int
        Width of crop of QR
    height_crop : int
        Height of crop of QR
    margin : int
        Margin of crop
    corner : {str: (int, int)}
        Corner sizes ('LEFT' and 'RIGHT')
    logger : Logger
        Object Logger

    Returns
    -------
    str
        Code on QR at the image
    """
    logging.info("Reading QR of {}...".format(filename))
    qr_code_detector = cv2.QRCodeDetector()
    image = cv2.imread(filename)
    p = re.compile('(?<!\\\\)\'')
    try:
        if image is not None:
            for read_function in [
                read_qr_at_right,
                read_qr_at_left,
                read_qr_at_right_margin_left,
                read_qr_at_right_margin_right,
                read_qr_at_left_margin_left,
                read_qr_at_left_margin_right,
                read_qr_at_right_margin_up,
                read_qr_at_right_margin_down,
                read_qr_at_left_margin_up,
                read_qr_at_left_margin_down,
            ]:
                qr_code = read_function(
                    qr_code_detector, p, image,
                    width_crop, height_crop, margin,
                    corner, logger
                )
                if qr_code is not None:
                    return qr_code
            logging.error("QR code on {} not detected".format(filename))
            os.remove('cropped.jpg')
            return None
    except Exception as e:
        logging.error("QR code reading error:\n{}".format(e))
        return None


def __read_qr_at__(
        qr_code_detector: cv2.QRCodeDetector, p: re.Pattern,
        cropped_image: np.ndarray, found_message: str,
        logger: logging.Logger
) -> Union[str, None]:
    logger.debug("Looking for QR in {}".format(found_message))
    cv2.imwrite('cropped.jpg', cropped_image)
    image_temp = cv2.imread('cropped.jpg')
    decoded_text, points, _ = qr_code_detector.detectAndDecode(image_temp)
    if decoded_text is not None and decoded_text != "":
        logger.debug("Decoded Text '{}'".format(decoded_text))
        os.remove('cropped.jpg')
        logger.info("QR found in {}".format(found_message))
        return p.sub('\"', decoded_text)
    else:
        return None


def read_qr_at_right(
        qr_code_detector: cv2.QRCodeDetector,
        p: re.Pattern, image: np.ndarray,
        width_crop: int, height_crop: int, margin: int,
        corner: Dict[str, Tuple[int]],
        logger: logging.Logger
) -> Union[str, None]:
    """
    Read QR at the right corner of the image

    Parameters
    ----------
    qr_code_detector : QRCodeDetector
        Open CV reader of QR code on images
    p : Patter
        Regular expression pattern
    image : ND-Array
        Array of N=2 dimension coding an image
    width_crop : int
        Width of crop of QR
    height_crop : int
        Height of crop of QR
    margin : int
        Margin of crop
    corner : {str: (int, int)}
        Corner sizes ('LEFT' and 'RIGHT')
    logger : Logger
        Object Logger

    Returns
    -------
    str
        In case of found, the code on the QR
    """
    cropped_image = image[
        corner["RIGHT"][1]:corner["RIGHT"][1] + height_crop,
        corner["RIGHT"][0]:corner["RIGHT"][0] + width_crop
    ]
    return __read_qr_at__(qr_code_detector, p, cropped_image, "right corner", logger)


def read_qr_at_left(
        qr_code_detector: cv2.QRCodeDetector,
        p: re.Pattern, image: np.ndarray,
        width_crop: int, height_crop: int, margin: int,
        corner: Dict[str, Tuple[int]],
        logger: logging.Logger
) -> Union[str, None]:
    """
    Read QR at the left corner of the image

    Parameters
    ----------
    qr_code_detector : QRCodeDetector
        Open CV reader of QR code on images
    p : Patter
        Regular expression pattern
    image : ND-Array
        Array of N=2 dimension coding an image
    width_crop : int
        Width of crop of QR
    height_crop : int
        Height of crop of QR
    margin : int
        Margin of crop
    corner : {str: (int, int)}
        Corner sizes ('LEFT' and 'RIGHT')
    logger : Logger
        Object Logger

    Returns
    -------
    str
        In case of found, the code on the QR
    """
    cropped_image = image[
        corner["LEFT"][1]:corner["LEFT"][1] + height_crop,
        corner["LEFT"][0]:corner["LEFT"][0] + width_crop
    ]
    return __read_qr_at__(qr_code_detector, p, cropped_image, "left corner", logger)


def read_qr_at_right_margin_left(
        qr_code_detector: cv2.QRCodeDetector,
        p: re.Pattern, image: np.ndarray,
        width_crop: int, height_crop: int, margin: int,
        corner: Dict[str, Tuple[int]],
        logger: logging.Logger
) -> Union[str, None]:
    """
    Read QR at the right margin left corner of the image

    Parameters
    ----------
    qr_code_detector : QRCodeDetector
        Open CV reader of QR code on images
    p : Patter
        Regular expression pattern
    image : ND-Array
        Array of N=2 dimension coding an image
    width_crop : int
        Width of crop of QR
    height_crop : int
        Height of crop of QR
    margin : int
        Margin of crop
    corner : {str: (int, int)}
        Corner sizes ('LEFT' and 'RIGHT')
    logger : Logger
        Object Logger

    Returns
    -------
    str
        In case of found, the code on the QR
    """
    cropped_image = image[
        corner["RIGHT"][1]:corner["RIGHT"][1] + height_crop,
        corner["RIGHT"][0] - margin:corner["RIGHT"][0] + width_crop - margin
    ]
    return __read_qr_at__(qr_code_detector, p, cropped_image, "right margin left", logger)


def read_qr_at_right_margin_right(
        qr_code_detector: cv2.QRCodeDetector,
        p: re.Pattern, image: np.ndarray,
        width_crop: int, height_crop: int, margin: int,
        corner: Dict[str, Tuple[int]],
        logger: logging.Logger
) -> Union[str, None]:
    """
    Read QR at the right margin right corner of the image

    Parameters
    ----------
    qr_code_detector : QRCodeDetector
        Open CV reader of QR code on images
    p : Patter
        Regular expression pattern
    image : ND-Array
        Array of N=2 dimension coding an image
    width_crop : int
        Width of crop of QR
    height_crop : int
        Height of crop of QR
    margin : int
        Margin of crop
    corner : {str: (int, int)}
        Corner sizes ('LEFT' and 'RIGHT')
    logger : Logger
        Object Logger

    Returns
    -------
    str
        In case of found, the code on the QR
    """
    cropped_image = image[
        corner["RIGHT"][1]:corner["RIGHT"][1] + height_crop,
        corner["RIGHT"][0] + margin:corner["RIGHT"][0] + width_crop + margin
    ]
    return __read_qr_at__(qr_code_detector, p, cropped_image, "right margin right", logger)


def read_qr_at_left_margin_left(
        qr_code_detector: cv2.QRCodeDetector,
        p: re.Pattern, image: np.ndarray,
        width_crop: int, height_crop: int, margin: int,
        corner: Dict[str, Tuple[int]],
        logger: logging.Logger
) -> Union[str, None]:
    """
    Read QR at the left margin left corner of the image

    Parameters
    ----------
    qr_code_detector : QRCodeDetector
        Open CV reader of QR code on images
    p : Patter
        Regular expression pattern
    image : ND-Array
        Array of N=2 dimension coding an image
    width_crop : int
        Width of crop of QR
    height_crop : int
        Height of crop of QR
    margin : int
        Margin of crop
    corner : {str: (int, int)}
        Corner sizes ('LEFT' and 'RIGHT')
    logger : Logger
        Object Logger

    Returns
    -------
    str
        In case of found, the code on the QR
    """
    cropped_image = image[
        corner["LEFT"][1]:corner["LEFT"][1] + height_crop,
        corner["LEFT"][0] - margin:corner["LEFT"][0] + width_crop - margin
    ]
    return __read_qr_at__(qr_code_detector, p, cropped_image, "left margin left", logger)


def read_qr_at_left_margin_right(
        qr_code_detector: cv2.QRCodeDetector,
        p: re.Pattern, image: np.ndarray,
        width_crop: int, height_crop: int, margin: int,
        corner: Dict[str, Tuple[int]],
        logger: logging.Logger
) -> Union[str, None]:
    """
    Read QR at the left margin right corner of the image

    Parameters
    ----------
    qr_code_detector : QRCodeDetector
        Open CV reader of QR code on images
    p : Patter
        Regular expression pattern
    image : ND-Array
        Array of N=2 dimension coding an image
    width_crop : int
        Width of crop of QR
    height_crop : int
        Height of crop of QR
    margin : int
        Margin of crop
    corner : {str: (int, int)}
        Corner sizes ('LEFT' and 'RIGHT')
    logger : Logger
        Object Logger

    Returns
    -------
    str
        In case of found, the code on the QR
    """
    cropped_image = image[
        corner["LEFT"][1]:corner["LEFT"][1] + height_crop,
        corner["LEFT"][0] + margin:corner["LEFT"][0] + width_crop + margin
    ]
    return __read_qr_at__(qr_code_detector, p, cropped_image, "left margin right", logger)


def read_qr_at_right_margin_up(
        qr_code_detector: cv2.QRCodeDetector,
        p: re.Pattern, image: np.ndarray,
        width_crop: int, height_crop: int, margin: int,
        corner: Dict[str, Tuple[int]],
        logger: logging.Logger
) -> Union[str, None]:
    """
    Read QR at the right margin up corner of the image

    Parameters
    ----------
    qr_code_detector : QRCodeDetector
        Open CV reader of QR code on images
    p : Patter
        Regular expression pattern
    image : ND-Array
        Array of N=2 dimension coding an image
    width_crop : int
        Width of crop of QR
    height_crop : int
        Height of crop of QR
    margin : int
        Margin of crop
    corner : {str: (int, int)}
        Corner sizes ('LEFT' and 'RIGHT')
    logger : Logger
        Object Logger

    Returns
    -------
    str
        In case of found, the code on the QR
    """
    cropped_image = image[
        corner["RIGHT"][1] - margin:corner["RIGHT"][1] + height_crop - margin,
        corner["RIGHT"][0] - margin:corner["RIGHT"][0] + width_crop
    ]
    return __read_qr_at__(qr_code_detector, p, cropped_image, "right margin up", logger)


def read_qr_at_right_margin_down(
        qr_code_detector: cv2.QRCodeDetector,
        p: re.Pattern, image: np.ndarray,
        width_crop: int, height_crop: int, margin: int,
        corner: Dict[str, Tuple[int]],
        logger: logging.Logger
) -> Union[str, None]:
    """
    Read QR at the right margin down corner of the image

    Parameters
    ----------
    qr_code_detector : QRCodeDetector
        Open CV reader of QR code on images
    p : Patter
        Regular expression pattern
    image : ND-Array
        Array of N=2 dimension coding an image
    width_crop : int
        Width of crop of QR
    height_crop : int
        Height of crop of QR
    margin : int
        Margin of crop
    corner : {str: (int, int)}
        Corner sizes ('LEFT' and 'RIGHT')
    logger : Logger
        Object Logger

    Returns
    -------
    str
        In case of found, the code on the QR
    """
    cropped_image = image[
        corner["RIGHT"][1] + margin:corner["RIGHT"][1] + height_crop + margin,
        corner["RIGHT"][0] - margin:corner["RIGHT"][0] + width_crop
    ]
    return __read_qr_at__(qr_code_detector, p, cropped_image, "right margin down", logger)


def read_qr_at_left_margin_up(
        qr_code_detector: cv2.QRCodeDetector,
        p: re.Pattern, image: np.ndarray,
        width_crop: int, height_crop: int, margin: int,
        corner: Dict[str, Tuple[int]],
        logger: logging.Logger
) -> Union[str, None]:
    """
    Read QR at the left margin up corner of the image

    Parameters
    ----------
    qr_code_detector : QRCodeDetector
        Open CV reader of QR code on images
    p : Patter
        Regular expression pattern
    image : ND-Array
        Array of N=2 dimension coding an image
    width_crop : int
        Width of crop of QR
    height_crop : int
        Height of crop of QR
    margin : int
        Margin of crop
    corner : {str: (int, int)}
        Corner sizes ('LEFT' and 'RIGHT')
    logger : Logger
        Object Logger

    Returns
    -------
    str
        In case of found, the code on the QR
    """
    cropped_image = image[
        corner["LEFT"][1] - margin:corner["LEFT"][1] + height_crop - margin,
        corner["LEFT"][0] - margin:corner["LEFT"][0] + width_crop
    ]
    return __read_qr_at__(qr_code_detector, p, cropped_image, "left margin up", logger)


def read_qr_at_left_margin_down(
        qr_code_detector: cv2.QRCodeDetector,
        p: re.Pattern, image: np.ndarray,
        width_crop: int, height_crop: int, margin: int,
        corner: Dict[str, Tuple[int]],
        logger: logging.Logger
) -> Union[str, None]:
    """
    Read QR at the left margin down corner of the image

    Parameters
    ----------
    qr_code_detector : QRCodeDetector
        Open CV reader of QR code on images
    p : Patter
        Regular expression pattern
    image : ND-Array
        Array of N=2 dimension coding an image
    width_crop : int
        Width of crop of QR
    height_crop : int
        Height of crop of QR
    margin : int
        Margin of crop
    corner : {str: (int, int)}
        Corner sizes ('LEFT' and 'RIGHT')
    logger : Logger
        Object Logger

    Returns
    -------
    str
        In case of found, the code on the QR
    """
    cropped_image = image[
        corner["LEFT"][1] + margin:corner["LEFT"][1] + height_crop + margin,
        corner["LEFT"][0] - margin:corner["LEFT"][0] + width_crop
    ]
    return __read_qr_at__(qr_code_detector, p, cropped_image, "left margin down", logger)


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
    areas = Areas(
        name=f"temp_{uuid.uuid4().hex}",
        temporal=True,
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
