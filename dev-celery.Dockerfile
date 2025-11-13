FROM herbarium-digitalization

RUN apt-get install -y \
    tesseract-ocr \
    wget \
    rawtherapee \
    ffmpeg \
    libsm6 \
    libxext6

RUN wget https://github.com/dnglab/dnglab/releases/download/v0.7.1/dnglab_0.7.1-1_amd64.deb && \
    apt-get install ./dnglab_0.7.1-1_amd64.deb

ENTRYPOINT ["celery", "-A", "intranet", "worker", "-l", "INFO"]
