# -*- coding: utf-8 -*-

from django.urls import re_path
from . import views

urlpatterns = [
    re_path(r'^load_priority_vouchers_file$', views.load_priority_vouchers_file, name='load_priority_vouchers_file'),
    re_path(r'^priority_vouchers_table$', views.priority_vouchers_table, name='priority_vouchers_table'),
    re_path(r'^pdf_error_data$', views.pdf_error_data, name='pdf_error_data'),
    re_path(r'^xls_error_data$', views.xls_error_data, name='xls_error_data'),
    re_path(r'^qr_generator$', views.qr_generator, name='qr_generator'),
    re_path(r'^session_table/qr$', views.session_table_qr, name='session_table_qr'),
    re_path(r'^session_table$', views.session_table, name='session_table'),
    re_path(
        r'^priority_vouchers_page_download/(?P<page_id>\d+)/$',
        views.priority_vouchers_page_download,
        name='priority_vouchers_page_download'
    ),
    re_path(r'^qr_page_download/(?P<page_id>\d+)/$', views.qr_page_download, name='qr_page_download'),
    re_path(r'^upload_color_profile_file$', views.upload_color_profile_file, name='upload_color_profile_file'),
    re_path(r'^mark_vouchers$', views.mark_vouchers, name='mark_vouchers'),
    re_path(r'^set_state$', views.set_state, name='set_state'),
    re_path(r'^control_vouchers$', views.control_vouchers, name='control_vouchers'),
    re_path(r'^vouchers_table/(?P<voucher_state>-?\d+)$', views.vouchers_table, name='vouchers_table'),
    re_path(r'^terminate_session$', views.terminate_session, name='terminate_session'),
    re_path(r'^validate_vouchers$', views.validate_vouchers, name='validate_vouchers'),
    re_path(r'^gallery_images$', views.gallery_images, name='gallery_images'),
    re_path(r'^gallery_table$', views.gallery_table, name='gallery_table'),
    re_path(r'^species_gallery/(?P<species_id>\d+)$', views.species_gallery, name='species_gallery'),
    re_path(r'^new_gallery_image/(?P<species_id>\d+)$', views.new_gallery_image, name='new_gallery_image'),
    re_path(r'^modify_gallery_image/(?P<gallery_id>\d+)$', views.modify_gallery_image, name='modify_gallery_image'),
    re_path(r'^delete_gallery_image/(?P<gallery_id>\d+)$', views.delete_gallery_image, name='delete_gallery_image'),
    re_path(r'^new_licence$', views.new_licence, name='new_licence'),
    re_path(
        r'^get_vouchers_to_validate/(?P<page_id>\d+)/(?P<voucher_state>-?\d+)$',
        views.get_vouchers_to_validate,
        name='get_vouchers_to_validate'
    ),
    re_path(r'^upload_banner$', views.upload_banner, name='upload_banner'),
    re_path(r'^upload_raw_image$', views.upload_raw_image, name='upload_raw_image'),
    re_path(r'^upload_temporal_image$', views.upload_temporal_image, name='upload_temporal_image'),
    re_path(r'^extract_taken_by/(?P<image_file>[\w \.]+)/$', views.extract_taken_by, name='extract_taken_by'),
    re_path(r'^get_pending_images$', views.get_pending_images, name='get_pending_images'),
    re_path(r'^get_pending_vouchers$', views.get_pending_vouchers, name='get_pending_vouchers'),
    re_path(r'^process_pending_images$', views.process_pending_images, name='process_pending_images'),
    re_path(r'^get_progress/(?P<task_id>[\w-]+)/$', views.get_progress, name='get_progress'),
    re_path(r'^get_task_log/(?P<task_id>[\w-]+)/$', views.get_task_log, name='get_task_log'),
    re_path(r'^vouchers_download$', views.vouchers_download, name='vouchers_download'),
    re_path(r'^download_catalog$', views.download_catalog, name='download_catalog'),
    re_path(r'^update_voucher/(?P<voucher_id>\d+)/$', views.update_voucher, name='update_voucher'),
]
