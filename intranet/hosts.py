from django_hosts import patterns, host


host_patterns = patterns(
    '',
    host(r'digitalization-dev', 'intranet.main_urls', name='digitalization'),
    host(r'apidev', 'intranet.api_urls', name='api'),
)
