FROM 660141862495.dkr.ecr.sa-east-1.amazonaws.com/herbarium-digitalization:latest

RUN apt-get install -y \
    wget \
    rawtherapee \
    ffmpeg \
    libsm6 \
    libxext6

RUN wget https://github.com/dnglab/dnglab/releases/download/v0.6.3/dnglab_0.6.3-1_amd64.deb && \
    apt-get install ./dnglab_0.6.3-1_amd64.deb

ENTRYPOINT ["celery", "-A", "intranet", "worker", "-B", "-l", "INFO"]
