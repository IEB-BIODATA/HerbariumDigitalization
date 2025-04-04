from __future__ import annotations

import html
import logging
import os
import smtplib
import tempfile
import time
import datetime as dt
import traceback
from abc import ABC, abstractmethod
from email.header import Header
from email.mime.application import MIMEApplication
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.utils import formataddr, formatdate, make_msgid
from typing import Dict, List, Tuple, Any, Sequence
from celery.app.task import Task
from django.conf import settings
from django.contrib.gis.gdal import DataSource
from django.contrib.gis.geos import GEOSGeometry, Point, LineString, LinearRing, Polygon, MultiPoint, MultiLineString, \
    MultiPolygon, GeometryCollection
from django.core.files.base import ContentFile
from django.core.files.storage import Storage
from django.core.files.uploadedfile import UploadedFile
from django.core.paginator import Paginator
from django.db import models
from django.db.models import Q, QuerySet
from django.http import HttpRequest, JsonResponse
from rest_framework.serializers import SerializerMetaclass

GEOM_TYPE = {
    0: Point,
    1: LineString,
    2: LinearRing,
    3: Polygon,
    4: MultiPoint,
    5: MultiLineString,
    6: MultiPolygon,
    7: GeometryCollection,
}


class CatalogQuerySet(models.QuerySet, ABC):

    @abstractmethod
    def filter_query(self, **parameters: Dict[str, List[str]]) -> CatalogQuerySet:
        pass

    @abstractmethod
    def filter_taxonomy(self, **parameters: Dict[str: List[str]]) -> CatalogQuerySet:
        pass

    @abstractmethod
    def filter_geometry(self, geometries: List[str]) -> CatalogQuerySet:
        pass

    @abstractmethod
    def search(self, text: str) -> CatalogQuerySet:
        pass


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

    @property
    def file_path(self) -> str:
        return self.__path__

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


def paginated_table(
        request: HttpRequest,
        entries: QuerySet,
        serializer: SerializerMetaclass,
        sort_by_func: dict[int, str],
        model_name: str,
        search_query: Q
) -> JsonResponse:
    search_value = request.GET.get("search[value]", None)
    if search_value:
        logging.debug(f"Searching with {search_value}")
        entries = entries.filter(search_query)

    sort_by = int(request.GET.get("order[0][column]", 4))
    sort_type = request.GET.get("order[0][dir]", "desc")

    if sort_by in sort_by_func:
        sort_by_str = "ascending" if sort_type == "asc" else "descending"
        second_sort_by = request.GET.get("order[1][column]", None)
        second_sort_type = request.GET.get("order[1][dir]", "asc")
        if second_sort_by:
            second_sort_by_str = "ascending" if second_sort_type == "asc" else "descending"
            logging.debug(f"Order by {sort_by} ({sort_by_func[sort_by]}) in {sort_by_str} order"
                          f" and {second_sort_by} ({sort_by_func[int(second_sort_by)]}) in {second_sort_by_str} order")
            entries = entries.order_by(
                ("" if sort_type == "asc" else "-") + sort_by_func[sort_by],
                ("" if second_sort_type == "asc" else "-") + sort_by_func[int(second_sort_by)]
            )
        else:
            logging.debug(f"Order by {sort_by} ({sort_by_func[sort_by]}) in {sort_by_str} order")
            entries = entries.order_by(("" if sort_type == "asc" else "-") + sort_by_func[sort_by])

    length = int(request.GET.get("length", 10))
    start = int(request.GET.get("start", 0))
    paginator = Paginator(entries, length)
    page_number = start // length + 1
    page_obj = paginator.get_page(page_number)
    data = list()

    logging.debug(f"Returning {entries.count()} {model_name}, starting at {start + 1} with {length} items")

    for item in page_obj:
        data.append(serializer(
            instance=item,
            many=False,
            context={"request": request}
        ).data)

    return JsonResponse({
        "draw": int(request.GET.get("draw", 0)),
        "recordsTotal": entries.count(),
        "recordsFiltered": paginator.count,
        "data": data
    })


def get_geometry_post(request: HttpRequest) -> GEOSGeometry:
    kml_file = request.data.get("file")
    return get_geometry(kml_file)


def get_geometry(file: UploadedFile) -> GEOSGeometry:
    file_extension = os.path.splitext(file.name)[1]
    with tempfile.NamedTemporaryFile(delete=True, suffix=file_extension) as temp_file:
        kml_data = file.read()
        temp_file.write(kml_data)
        temp_file.seek(0)
        data_source = DataSource(temp_file.name)
        layer = data_source[0]
        kml_geometry = layer.get_geoms(True)
        if len(kml_geometry) > 1:
            logging.warning(f"File has {len(kml_geometry)} layers, using first one only")
        geometry = kml_geometry[0]
    if geometry.hasz:
        logging.debug(f"Stripping z dimension of {geometry.geom_type}")
        geometry = strip_z_dimension(geometry)
    return geometry


def strip_z_dimension(geometry: GEOSGeometry) -> GEOSGeometry:
    if geometry.num_geom > 1:
        geoms = list()
        for geom in geometry:
            geoms.append(__strip_z_dimension_coord__(geom))
        return GEOM_TYPE[geometry.geom_typeid](*geoms)
    else:
        return __strip_z_dimension_coord__(geometry)


def __strip_z_dimension_coord__(geometry: GEOSGeometry) -> GEOSGeometry:
    if geometry.geom_typeid == 3:
        rings = list()
        for linear_ring in geometry:
            rings.append(__strip_z_dimension_coord__(linear_ring))
        return Polygon(*rings)
    elif geometry.geom_typeid == 6:
        polygons = list()
        for polygon in geometry:
            polygons.append(__strip_z_dimension_coord__(polygon))
        return MultiPolygon(polygons)
    else:
        return GEOM_TYPE[geometry.geom_typeid](
            list(map(__strip_z__, geometry.coords)),
            srid=geometry.srid
        )


def __strip_z__(coordinate: Tuple[float, float, float]) -> Tuple[float, float]:
    if abs(coordinate[2] - 1e-6) < 0:
        logging.warning(f"{coordinate[2]} is not a zero Z coordinate")
    return coordinate[0], coordinate[1]


def send_mail(mail_body: str, to_addr: str, subject: str, attachment_path: str = None) -> None:
    """
    Sends mail based on template

    Parameters
    ----------
    mail_body : str
        Body of mail based on template
    to_addr : str
        Address to send email
    subject : str
        Subject of mail
    attachment_path : str, optional
        Path to attachment file

    Returns
    -------
    None
    """
    logging.info("Sending email for subject {}...".format(subject))
    try:
        username = settings.EMAIL_HOST_USER
        password = settings.EMAIL_HOST_PASSWORD
        from_addr = "noreply@{}".format(os.environ.get("EMAIL_DOMAIN"))

        msg = MIMEMultipart('relative')

        msg['Subject'] = str(subject)
        msg['From'] = formataddr((str(Header(from_addr, 'utf-8')), from_addr))
        msg['To'] = to_addr
        msg['Date'] = formatdate(time.time(), localtime=True)
        msg.add_header('Message-id', make_msgid())
        msg.attach(MIMEText(mail_body, 'html', _charset="utf-8"))

        if attachment_path:
            with open(attachment_path, 'rb') as attach_file:
                basename = os.path.basename(attachment_path)
                part = MIMEApplication(attach_file.read(), Name=basename)
                part['Content-Disposition'] = 'attachment; filename="%s"' % basename
                msg.attach(part)

        server = smtplib.SMTP(settings.EMAIL_HOST, settings.EMAIL_PORT)
        server.ehlo()
        server.starttls()
        server.login(username, password)
        server.sendmail(from_addr, [to_addr], msg.as_string())
        server.close()
    except Exception as e:
        logging.error("Error sending mail")
        logging.error(e, exc_info=True)
        raise e
    return
