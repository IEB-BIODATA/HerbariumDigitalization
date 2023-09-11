# -*- coding: utf-8 -*-

from django.urls import re_path
from . import views

urlpatterns = [
    re_path(r'^qr_generator$', views.qr_generator, name='qr_generator'),
    re_path(r'^code_generator$', views.code_generator, name='code_generator'),
    re_path(r'^historical_page_download$', views.historical_page_download, name='historical_page_download'),
    re_path(r'^historical_priority_voucher_page_download$', views.historical_priority_voucher_page_download, name='historical_priority_voucher_page_download'),
    re_path(r'^load_priority_vouchers_file$', views.load_priority_vouchers_file, name='load_priority_vouchers_file'),
    re_path(r'^priority_vouchers_table$', views.priority_vouchers_table, name='priority_vouchers_table'),
    re_path(r'^upload_color_profile_file$', views.upload_color_profile_file, name='upload_color_profile_file'),
    re_path(r'^session_table$', views.session_table, name='session_table'),
    re_path(r'^mark_vouchers$', views.mark_vouchers, name='mark_vouchers'),
    re_path(r'^set_state$', views.set_state, name='set_state'),
    re_path(r'^csv_error_data$', views.csv_error_data, name='csv_error_data'),
    re_path(r'^xls_error_data$', views.xls_error_data, name='xls_error_data'),
    re_path(r'^pdf_error_data$', views.pdf_error_data, name='pdf_error_data'),
    re_path(r'^control_vouchers$', views.control_vouchers, name='control_vouchers'),
    re_path(r'^terminate_session$', views.terminate_session, name='terminate_session'),
    re_path(r'^validate_vouchers$', views.validate_vouchers, name='validate_vouchers'),
    re_path(r'^modify_gallery_image$', views.modify_gallery_image, name='modify_gallery_image'),
    re_path(r'^gallery_table$', views.gallery_table, name='gallery_table'),
    re_path(
        r'^get_vouchers_to_validate/(?P<page_id>\d+)/(?P<voucher_state>-?\d+)$',
        views.get_vouchers_to_validate,
        name='get_vouchers_to_validate'
    ),
    re_path(r'^upload_gallery$', views.upload_gallery, name='upload_gallery'),
    re_path(r'^modify_gallery/(?P<species_id>\d+)$', views.modify_gallery, name='modify_gallery'),
    re_path(r'^gallery_image/(?P<gallery_id>\d+)$', views.gallery_image, name='gallery_image'),
    re_path(r'^new_gallery_image/(?P<catalog_id>\d+)$', views.new_gallery_image, name='new_gallery_image'),
    re_path(r'^delete_gallery_image/(?P<gallery_id>\d+)$', views.delete_gallery_image, name='delete_gallery_image'),
    re_path(r'^new_licence$', views.new_licence, name='new_licence'),
    re_path(r'^upload_banner$', views.upload_banner, name='upload_banner'),
    re_path(r'^upload_raw_image$', views.upload_raw_image, name='upload_raw_image'),
    re_path(r'^get_pending_images$', views.get_pending_images, name='get_pending_images'),
    re_path(r'^get_pending_vouchers$', views.get_pending_vouchers, name='get_pending_vouchers'),
    re_path(r'^process_pending_images$', views.process_pending_images, name='process_pending_images'),
    re_path(r'^get_progress/(?P<task_id>[\w-]+)/$', views.get_progress, name='get_progress'),
    re_path(r'^get_task_log/(?P<task_id>[\w-]+)/$', views.get_task_log, name='get_task_log'),
    re_path(r'^vouchers_download$', views.vouchers_download, name='vouchers_download'),
    re_path(r'^download_catalog$', views.download_catalog, name='download_catalog'),
    re_path(r'^update_voucher/(?P<id>\d+)/$', views.update_voucher, name='update_voucher'),
]
