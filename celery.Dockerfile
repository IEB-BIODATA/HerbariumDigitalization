FROM herbarium-api

CMD ["celery", "worker", "--app=web", "--loglevel=info"]
