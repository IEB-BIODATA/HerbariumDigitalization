from django_hosts import patterns, host


host_patterns = patterns(
    '',
    host(r'digitalizacion', 'intranet.main_urls', name='digitalization'),
    host(r'api', 'intranet.api_urls', name='api'),
)
