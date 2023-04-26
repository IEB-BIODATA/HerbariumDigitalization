FROM python:3.10-slim

EXPOSE 8000

RUN apt-get update -y
RUN apt-get install -y \
    binutils \
    libproj-dev \
    libgdal-dev \
    libgeos-dev \
    libpq-dev

RUN mkdir /app
WORKDIR /app
COPY ./requirements.txt /app

RUN pip install --upgrade pip
RUN pip install --no-cache-dir -r requirements.txt

COPY ./apps /app/apps
COPY ./templates /app/templates
COPY ./web /app/web
COPY ./manage.py /app

RUN mkdir -p /app/media/upload
RUN mkdir -p /app/media/qr

RUN mkdir -p /var/log/gunicorn

STOPSIGNAL SIGTERM

ENV PYTHONPATH=/app:$PYTHONPATH

ENTRYPOINT [ \
    "gunicorn", "web.wsgi:application", \
    "--bind", "0.0.0.0:8000", \
    "--log-level", "debug", \
    "--access-logformat", "'%(h)s %(l)s %(u)s %(t)s \"%(r)s\" %(s)s %(b)s \"%(f)s\" \"%(a)s\" %(L)s \"%({header_name}i)s\"'", \
    "--access-logfile", "/var/log/gunicorn/access.log", \
    "--workers=2" \
]
