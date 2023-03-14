# -*- coding: utf-8 -*-
from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from apps.digitalization.models import BiodataCode, Herbarium
from django.db.models.functions import ExtractDay, ExtractMonth, ExtractYear
from django.db.models import Count
from django.db.models import Q


@login_required
def index(request):
    count_total_codes = BiodataCode.objects.filter(qr_generated=True).order_by('page__created_at__date').annotate(
        day=ExtractDay('page__created_at'),
        month=ExtractMonth('page__created_at'),
        year=ExtractYear('page__created_at'),
    ).values('day', 'month','year').annotate(count=Count('*')).values('day', 'month', 'year', 'count')
    count_scanned_codes = BiodataCode.objects.filter(
        Q(qr_generated=True, voucher_state=1) | Q(qr_generated=True, voucher_state=7)
    ).order_by('page__created_at__date').annotate(
        day=ExtractDay('page__created_at'),
        month=ExtractMonth('page__created_at'),
        year=ExtractYear('page__created_at'),
    ).values('day', 'month', 'year').annotate(count=Count('*')).values('day', 'month', 'year', 'count')
    stand_by_conc = BiodataCode.objects.filter(herbarium__collection_code='CONC',voucher_state=0).count()
    digitalized_conc = BiodataCode.objects.filter(
        Q(voucher_state=1) | Q(voucher_state=7),
        herbarium__collection_code='CONC'
    ).count()
    stand_by_uls = BiodataCode.objects.filter(
        herbarium__collection_code='ULS',
        voucher_state=0
    ).count()
    digitalized_uls = BiodataCode.objects.filter(
        Q(voucher_state=1) | Q(voucher_state=7),
        herbarium__collection_code='ULS'
    ).count()
    return render(
        request,
        'index.html',
        {
            'count_total_codes': count_total_codes,
            'count_scanned_codes': count_scanned_codes,
            'stand_by_conc': stand_by_conc,
            'digitalized_conc': digitalized_conc,
            'stand_by_uls': stand_by_uls,
            'digitalized_uls': digitalized_uls
        }
    )
