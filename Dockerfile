FROM python:3.10-slim

EXPOSE 8000

RUN apt-get update -y
RUN apt-get install -y \
    binutils \
    libproj-dev \
    libgdal-dev \
    libgeos-dev \
    libpq-dev \
    gettext \
    zbar-tools

RUN mkdir /app
WORKDIR /app
COPY ./requirements.txt /app

RUN pip install --upgrade pip setuptools setuptools_scm wheel
RUN pip install --no-cache-dir -r requirements.txt

COPY ./apps /app/apps
COPY ./assets /app/assets
COPY ./templates /app/templates
COPY ./static /app/static
COPY ./intranet /app/intranet
COPY ./manage.py /app

RUN mkdir -p /app/media/upload
RUN mkdir -p /app/media/qr

RUN mkdir -p /var/log/gunicorn

STOPSIGNAL SIGTERM

ENV PYTHONPATH=/app:$PYTHONPATH

ENTRYPOINT [ \
    "gunicorn", "intranet.wsgi:application", \
    "--bind", "0.0.0.0:8000", \
    "--log-level", "debug", \
    "--access-logformat", "'%(h)s %(l)s %(u)s %(t)s \"%(r)s\" %(s)s %(b)s \"%(f)s\" \"%(a)s\" %(L)s \"%({header_name}i)s\"'", \
    "--access-logfile", "/var/log/gunicorn/access.log", \
    "--workers=2", \
    "--timeout=120", \
    "--preload" \
]
