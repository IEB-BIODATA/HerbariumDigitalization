FROM python:3.10-slim

EXPOSE 8000

RUN apt-get update -y
RUN apt-get install -y \
    binutils \
    libproj-dev \
    libgdal-dev \
    libgeos-dev \
    libpq-dev \
    gettext

RUN mkdir /app
WORKDIR /app

COPY ./requirements.txt /app
RUN pip install --upgrade pip
RUN pip install --no-cache-dir -r requirements.txt

ENTRYPOINT ["python", "/app/manage.py"]
CMD ["runserver", "0.0.0.0:8000"]
