import pandas as pd
from django.core.management.base import BaseCommand
from tqdm import tqdm

from apps.digitalization.models import Voucher, VoucherRepatriated


class Command(BaseCommand):
    def handle(self, *args, **kwargs):
        data = pd.read_excel("herbarium_specimens_CL1_cruzado_catalogo.xlsx")
        repatriated = Voucher.objects.filter(herbarium=8).all()
        qs_df = pd.DataFrame(list(repatriated.values("id", "catalog_number")))
        merged = qs_df.merge(
            data,
            left_on="catalog_number",
            right_on="CatalogNumberNumeric",
            how="left",
            indicator=True
        )
        merged_indexes = merged.set_index("id")
        unmapped = merged[merged["_merge"] == "left_only"].copy()
        assert len(unmapped) == 0
        for voucher in tqdm(repatriated):
            row = merged_indexes.loc[voucher.id]
            repatriated_voucher = VoucherRepatriated(
                **{f.name: getattr(voucher, f.name) for f in Voucher._meta.fields}
            )
            repatriated_voucher.voucher_ptr_id = voucher.id
            repatriated_voucher.verbatim_scientific_name = row["scientificName"]
            repatriated_voucher.save_base(raw=True)
            voucher.catalog_number = int(row["catalogNumber"][1:])
            voucher.other_catalog_numbers = row["CatalogNumberNumeric"]
            voucher.save()
