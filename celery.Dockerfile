FROM 660141862495.dkr.ecr.sa-east-1.amazonaws.com/herbarium-api:latest

ENTRYPOINT ["celery", "-A", "web", "worker", "-l", "INFO"]
