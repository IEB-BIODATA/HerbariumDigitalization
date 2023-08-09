FROM herbarium-api

ENTRYPOINT ["celery", "-A", "web", "worker", "-l", "INFO"]
