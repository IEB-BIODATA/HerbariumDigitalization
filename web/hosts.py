from django.conf import settings
from django_hosts import patterns, host

host_patterns = patterns(
    '',
    host(r'digitalizacion', 'web.main_urls', name='digitalization'),
    host(r'api', 'web.api_urls', name='api'),
)

if settings.DEBUG:
    host_patterns += patterns(
        '',
        host(r'localhost', 'web.main_urls', name='localhost'),
    )
