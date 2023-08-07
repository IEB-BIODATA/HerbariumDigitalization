import logging
from typing import List

from celery import shared_task

from apps.catalog.utils import generate_etiquette
from apps.digitalization.models import VoucherImported


@shared_task
def update_voucher_name(vouchers: List[int]):
    logging.info(vouchers)
    for voucher_id in vouchers:
        logging.debug("Getting voucher")
        voucher = VoucherImported.objects.get(id=voucher_id)
        logging.debug(voucher)
        logging.info("Updating voucher: {}, new specie: `{}`".format(
            voucher.id,
            voucher.scientificName
        ))
        generate_etiquette(voucher.id)
