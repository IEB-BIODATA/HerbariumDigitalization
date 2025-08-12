from django.utils.translation import gettext_lazy as _, get_language, activate
from storages.backends.s3boto3 import S3Boto3Storage
from django.db.models import Count
from django.core.files.base import ContentFile
from django.utils import timezone
from celery import shared_task
from apps.catalog.models import Species
from apps.datavis.models import DataVisualization
import pandas as pd
import matplotlib.pyplot as plt
import io

class PublicDatavisStorage(S3Boto3Storage):
    location = 'static/presentation/images/datavis'
    default_acl = None
    querystring_auth = False
    file_overwrite = True
    object_parameters = {"CacheControl": "max-age=86400"}

def group_frequency(frequency):
    if frequency > 5:
        return ">5"
    elif frequency > 0:
        return "1–5"
    else:
        return "0"

def delete_by_prefix(prefix: str) -> int:
    storage = PublicDatavisStorage()
    bucket = storage.bucket
    full_prefix = (
        f"{storage.location.rstrip('/')}/{prefix.lstrip('/')}"
        if getattr(storage, "location", "")
        else prefix
    )
    deleted = 0
    batch = []
    for obj in bucket.objects.filter(Prefix=full_prefix):
        batch.append({"Key": obj.key})
        if len(batch) == 1000:
            bucket.delete_objects(Delete={"Objects": batch})
            deleted += len(batch)
            batch = []
    if batch:
        bucket.delete_objects(Delete={"Objects": batch})
        deleted += len(batch)
    return deleted

@shared_task(name='digitalization_progress')
def digitalization_progress():
    collection_frequency_qs = (Species.objects.filter(determined=True, conservation_status__in=[1,3]).annotate(occ_count=Count("voucherimported")).values("id","scientific_name","occ_count").order_by("-occ_count"))
    collection_frequency = pd.DataFrame.from_records(collection_frequency_qs)
    collection_frequency.columns= ["id", "ScientificName", "Frequency"]
    collection_frequency_plot = collection_frequency.copy().reset_index(drop=True)
    collection_frequency_plot["index"] = collection_frequency.index + 1
    collection_frequency_plot["group"] = collection_frequency_plot["Frequency"].apply(group_frequency)
    collection_frequency_plot["group"] = pd.Categorical(collection_frequency_plot["group"],categories=[">5", "1–5", "0"],ordered=True)
    limit_5 = collection_frequency_plot.loc[collection_frequency_plot["Frequency"] > 5, "index"].max() + 0.5
    limit_1 = collection_frequency_plot.loc[collection_frequency_plot["Frequency"] > 0, "index"].max() + 0.5
    group_info = collection_frequency_plot["group"].value_counts().sort_index()
    group_pct = (group_info / group_info.sum() * 100).round(1).astype(str) + "%"
    group_pos = collection_frequency_plot.groupby("group",observed=False)["index"].mean()
    group_color = {
        ">5": "#1b9e77",
        "1–5": "#d95f02",
        "0": "#7570b3"
    }
    fig, (ax1, ax2) = plt.subplots(
        2, 1,
        figsize=(12, 8),
        gridspec_kw={'height_ratios': [4, 0.5]},
        sharex=True
    )
    ax1.bar(collection_frequency_plot["index"], collection_frequency_plot["Frequency"], color='lightgray')
    ax1.axvline(limit_5, color='red', linestyle='--', linewidth=1)
    ax1.axvline(limit_1, color='blue', linestyle='--', linewidth=1)
    ax1.set_ylabel(_("Specimens"), fontsize=16)
    ax1.set_xticks([])
    ax1.spines[['top', 'right', 'bottom']].set_visible(False)
    for group in group_color:
        sub_df = collection_frequency_plot[collection_frequency_plot["group"] == group]
        ax2.bar(sub_df["index"],height=1,width=1.0,bottom=0,color=group_color[group],label=group)
    for group in group_color:
        if group in group_pos:
            ax2.text(group_pos[group],0.5,group_pct[group],ha='center',va='center',fontsize=20,weight='bold',color='black')
    ax2.set_yticks([])
    ax2.set_xlabel(_("Catalog species ordered by number of specimens"), fontsize=16)
    ax2.spines[['top', 'right', 'left']].set_visible(False)

    handles = [plt.Rectangle((0,0),1,1, color=group_color[g]) for g in group_color]
    labels = list(group_color.keys())
    ax2.legend(
        handles, labels,
        title=_("N° of Specimens"),
        loc='lower center',
        bbox_to_anchor=(0.5, -1.5),
        ncol=3,
        fontsize=14,
        title_fontsize=14
    )
    plt.tight_layout()
    buf = io.BytesIO()
    plt.savefig(buf, format="png", dpi=300, bbox_inches="tight")
    plt.close(fig)
    buf.seek(0)
    ts = timezone.now().strftime("%Y%m%d%H%M%S")
    name = f"herbarium_progress_fig_1_{ts}.png"
    delete_by_prefix("herbarium_progress_fig_1_")
    storage = PublicDatavisStorage()
    storage.save(name, ContentFile(buf.getvalue()))
    url = f'https://static.herbariodigital.cl/images/datavis/{name}'
    group_per=(group_info / group_info.sum() * 100).round(1)
    percentage_completeness=float(group_per['>5']+group_per['1–5'])
    data = {"fig_1": url, "percentage_completeness": percentage_completeness}
    data_visualization, created = DataVisualization.objects.get_or_create(name='herbarium_progress')
    data_visualization.data=data
    data_visualization.save()