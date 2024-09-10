import time

import boto3
from django.core.management.base import BaseCommand

from apps.digitalization.models import VoucherImported
from intranet.utils import send_mail


class Command(BaseCommand):
    def add_arguments(self, parser):
        parser.add_argument('mail', type=str, help='Mail address to notified')

    def handle(self, *args, **kwargs):
        mail_to_notify = kwargs['mail']
        s3 = boto3.client('s3')
        objects = VoucherImported.objects.filter(biodata_code__voucher_state=8)
        total = objects.count()
        obj_to_restore = [(obj, 0) for obj in objects]
        restored = sum([state == 2 for _, state in obj_to_restore])
        while restored < total:
            for i, (obj, state) in enumerate(obj_to_restore):
                bucket_name = obj.image_raw.storage.bucket_name
                image_key = obj.image_raw.storage.location + "/" + obj.image_raw.name
                if state == 2:
                    continue
                response = s3.head_object(Bucket=bucket_name, Key=image_key)
                if response["StorageClass"] == 'DEEP_ARCHIVE':
                    if 'Restore' in response:
                        if 'ongoing-request="true"' in response['Restore']:
                            obj_to_restore[i] = (obj, 1)
                        else:
                            obj_to_restore[i] = (obj, 2)
                    else:
                        s3.restore_object(
                            Bucket=bucket_name,
                            Key=image_key,
                            RestoreRequest={
                                'Days': 7,
                                'GlacierJobParameters': {
                                    'Tier': 'Standard',
                                }
                            }
                        )
            restored = sum([state == 2 for _, state in obj_to_restore])
            print("Object restored: {}/{}".format(restored, total), end="\t")
            print("Object in progress: {}/{}".format(sum([state == 1 for _, state in obj_to_restore]), total))
            time.sleep(10 * 60)
        send_mail("Everything restored", mail_to_notify,"Pending images")
