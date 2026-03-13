import os

import boto3
import pandas as pd
from django.core.management.base import BaseCommand

from apps.digitalization.models import VoucherImported


def get_list():
    # Replace this with the needed vouchers
    vouchers = VoucherImported.objects.first()
    return [vouchers]

class Command(BaseCommand):
    def handle(self, *args, **kwargs):
        os.makedirs("vouchers", exist_ok=True)
        s3 = boto3.client('s3')
        objects = get_list()
        for obj in objects:
            bucket_name = obj.image_raw.storage.bucket_name
            image_key = obj.image_raw.storage.location + "/" + obj.image.name
            s3.download_file(bucket_name, image_key, os.path.join("vouchers", obj.image.name))
