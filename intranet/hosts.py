from django_hosts import patterns, host


host_patterns = patterns(
    '',
    host(r'digitalizacion(-dev)?', 'intranet.main_urls', name='digitalization'),
    host(r'api(-dev)?', 'intranet.api_urls', name='api'),
)
