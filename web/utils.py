import logging
from typing import Type

from django.core.paginator import Paginator
from django.db.models import Model, Q
from django.http import HttpRequest, JsonResponse
from rest_framework.serializers import SerializerMetaclass


def paginated_table(
        request: HttpRequest,
        model: Type[Model],
        serializer: SerializerMetaclass,
        sort_by_func: dict[int, str],
        model_name: str,
        search_query: Q
) -> JsonResponse:
    entries = model.objects.all()
    search_value = request.GET.get("search[value]", None)
    if search_value:
        logging.debug(f"Searching with {search_value}")
        entries = entries.filter(search_query)

    sort_by = int(request.GET.get("order[0][column]", 4))
    sort_type = request.GET.get("order[0][dir]", "desc")

    if sort_by in sort_by_func:
        sort_by_str = "ascending" if sort_type == "asc" else "descending"
        logging.debug(f"Order by {sort_by} ({sort_by_func[sort_by]}) in {sort_by_str} order")
        entries = entries.order_by(
            ("" if sort_type == "asc" else "-") + sort_by_func[sort_by]
        )

    length = int(request.GET.get("length", 10))
    start = int(request.GET.get("start", 0))
    paginator = Paginator(entries, length)
    page_number = start // length + 1
    page_obj = paginator.get_page(page_number)
    data = list()

    logging.debug(f"Returning {entries.count()} {model_name}, starting at {start + 1} with {length} items")

    for item in page_obj:
        data.append(serializer(
            instance=item,
            many=False,
            context=request
        ).data)

    return JsonResponse({
        "draw": int(request.GET.get("draw", 0)),
        "recordsTotal": entries.count(),
        "recordsFiltered": paginator.count,
        "data": data
    })
